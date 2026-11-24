# Módulo de datos: entidades del aula virtual (ver docs/schemas/schema.mmd)
from django.contrib.auth.models import AbstractUser, UserManager
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class Usuario(AbstractUser):
    dni = models.CharField(max_length=10, blank=True)
    fecha_nacimiento = models.DateField(null=True, blank=True)

    def __str__(self):
        return self.get_full_name() or self.username


class RolManager(UserManager):
    """Filtra usuarios por el Group que representa su rol."""

    def __init__(self, rol):
        super().__init__()
        self.rol = rol

    def get_queryset(self):
        return super().get_queryset().filter(groups__name=self.rol)


class Alumno(Usuario):
    objects = RolManager('alumno')

    class Meta:
        proxy = True

    def unidad_actual(self, catedra):
        """Primera unidad que el alumno todavía no completó."""
        for unidad in catedra.unidades.filter(es_fe_de_erratas=False):
            if not unidad.completada_por(self):
                return unidad
        return None


class Profesor(Usuario):
    objects = RolManager('profesor')

    class Meta:
        proxy = True
        verbose_name_plural = 'profesores'


class Carrera(models.Model):
    nombre = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.nombre


class Materia(models.Model):
    carrera = models.ForeignKey(Carrera, on_delete=models.CASCADE, related_name='materias')
    nombre = models.CharField(max_length=100)

    def __str__(self):
        return self.nombre


class Catedra(models.Model):
    materia = models.ForeignKey(Materia, on_delete=models.CASCADE, related_name='catedras')
    anio = models.PositiveSmallIntegerField()
    cuatrimestre = models.PositiveSmallIntegerField(choices=[(1, '1º'), (2, '2º')])
    programa = models.JSONField(default=dict, blank=True)
    programa_archivo = models.FileField(upload_to='programas/', blank=True)
    profesores = models.ManyToManyField(
        Usuario, related_name='catedras', blank=True,
        limit_choices_to={'groups__name': 'profesor'},
    )
    alumnos = models.ManyToManyField(
        Usuario, related_name='cursadas', blank=True,
        limit_choices_to={'groups__name': 'alumno'},
    )

    class Meta:
        verbose_name = 'cátedra'
        ordering = ['-anio', '-cuatrimestre']

    def __str__(self):
        return f'{self.materia} {self.anio}-{self.cuatrimestre}C'


class Unidad(models.Model):
    catedra = models.ForeignKey(Catedra, on_delete=models.CASCADE, related_name='unidades')
    orden = models.PositiveSmallIntegerField()
    titulo = models.CharField(max_length=200)
    conceptos = models.JSONField(default=list, blank=True)
    fecha_apertura = models.DateField(null=True, blank=True)
    fecha_limite = models.DateField(null=True, blank=True)
    # Fe de erratas: contenido corregido de unidades ya cursadas. Queda fuera
    # de la secuencia, así que nunca bloquea el recorrido del alumno.
    es_fe_de_erratas = models.BooleanField(default=False)
    corrige = models.ManyToManyField(
        'self', symmetrical=False, blank=True, related_name='erratas',
        limit_choices_to={'es_fe_de_erratas': False},
    )

    class Meta:
        verbose_name_plural = 'unidades'
        ordering = ['orden']
        constraints = [
            models.UniqueConstraint(fields=['catedra', 'orden'], name='unidad_orden_unico'),
        ]

    def __str__(self):
        return f'Unidad {self.orden}: {self.titulo}'

    def clean(self):
        if self.fecha_apertura and self.fecha_limite and self.fecha_apertura > self.fecha_limite:
            raise ValidationError('La fecha de apertura no puede ser posterior a la fecha límite.')

    def completada_por(self, alumno):
        completados = Progreso.objects.filter(
            alumno=alumno, completado_en__isnull=False,
        ).values('contenido')
        publicados = self.contenidos.filter(publicado=True)
        # Una unidad sin contenido publicado no está completa: el alumno espera ahí.
        return publicados.exists() and not publicados.exclude(pk__in=completados).exists()

    def esta_desbloqueada(self, alumno):
        """Se abre al llegar su fecha de apertura y cuando el alumno completó la anterior.

        Una fe de erratas se abre cuando el alumno ya pasó por las unidades que corrige.
        """
        if self.fecha_apertura and timezone.localdate() < self.fecha_apertura:
            return False
        if self.es_fe_de_erratas:
            return all(unidad.completada_por(alumno) for unidad in self.corrige.all())
        anterior = self.catedra.unidades.filter(
            orden__lt=self.orden, es_fe_de_erratas=False,
        ).last()
        return anterior is None or anterior.completada_por(alumno)


class Contenido(models.Model):
    class Formato(models.TextChoices):
        TEXTO = 'texto', 'Texto'
        CUESTIONARIO = 'cuestionario', 'Cuestionario'
        PRACTICA = 'practica', 'Práctica'

    unidad = models.ForeignKey(Unidad, on_delete=models.CASCADE, related_name='contenidos')
    autor = models.ForeignKey(
        Usuario, on_delete=models.SET_NULL, null=True, related_name='contenidos',
    )
    formato = models.CharField(max_length=20, choices=Formato.choices)
    titulo = models.CharField(max_length=200)
    cuerpo = models.JSONField(default=dict, blank=True)
    archivo = models.FileField(upload_to='material/', blank=True)
    publicado = models.BooleanField(default=False)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return self.titulo

    @property
    def es_teoria(self):
        """Texto es teoría; cuestionario y práctica son práctica."""
        return self.formato == self.Formato.TEXTO


class Progreso(models.Model):
    alumno = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='progresos')
    contenido = models.ForeignKey(Contenido, on_delete=models.CASCADE, related_name='progresos')
    completado_en = models.DateTimeField(null=True, blank=True)
    intentos = models.PositiveIntegerField(default=0)
    respuesta = models.JSONField(default=dict, blank=True)
    archivo = models.FileField(upload_to='practicas/', blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['alumno', 'contenido'], name='progreso_unico'),
        ]

    def __str__(self):
        return f'{self.alumno} - {self.contenido}'

    def en_termino(self):
        limite = self.contenido.unidad.fecha_limite
        if self.completado_en is None:
            return False
        return limite is None or timezone.localdate(self.completado_en) <= limite


class Horario(models.Model):
    """Bloque semanal de cursada. Se repite cada semana del cuatrimestre."""

    class Dia(models.IntegerChoices):
        LUNES = 0, 'Lunes'
        MARTES = 1, 'Martes'
        MIERCOLES = 2, 'Miércoles'
        JUEVES = 3, 'Jueves'
        VIERNES = 4, 'Viernes'
        SABADO = 5, 'Sábado'

    catedra = models.ForeignKey(Catedra, on_delete=models.CASCADE, related_name='horarios')
    dia = models.PositiveSmallIntegerField(choices=Dia.choices)
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()

    class Meta:
        ordering = ['dia', 'hora_inicio']

    def __str__(self):
        return f'{self.get_dia_display()} {self.hora_inicio:%H:%M}-{self.hora_fin:%H:%M}'

    def clean(self):
        if self.hora_inicio >= self.hora_fin:
            raise ValidationError('La hora de inicio tiene que ser anterior a la de fin.')


class Clase(models.Model):
    """Una sesión concreta de la cursada: qué se ve, dónde y con qué material."""

    catedra = models.ForeignKey(Catedra, on_delete=models.CASCADE, related_name='clases')
    numero = models.PositiveSmallIntegerField()
    fecha = models.DateField()
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()
    titulo = models.CharField(max_length=200)
    resumen = models.TextField(blank=True)
    unidad = models.ForeignKey(
        Unidad, on_delete=models.SET_NULL, null=True, blank=True, related_name='clases',
    )
    link_videollamada = models.URLField(blank=True)
    contenidos = models.ManyToManyField(Contenido, blank=True, related_name='clases')

    class Meta:
        ordering = ['fecha', 'hora_inicio']
        constraints = [
            models.UniqueConstraint(fields=['catedra', 'numero'], name='clase_numero_unico'),
        ]

    def __str__(self):
        return f'{self.catedra.materia}: Clase {self.numero}'

    def clean(self):
        if self.hora_inicio and self.hora_fin and self.hora_inicio >= self.hora_fin:
            raise ValidationError('La hora de inicio tiene que ser anterior a la de fin.')


class Asistencia(models.Model):
    """Presente de un alumno en una clase. Si no hay registro, estuvo ausente."""

    alumno = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='asistencias')
    clase = models.ForeignKey(Clase, on_delete=models.CASCADE, related_name='asistencias')
    registrada_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = 'asistencias'
        constraints = [
            models.UniqueConstraint(fields=['alumno', 'clase'], name='asistencia_unica'),
        ]

    def __str__(self):
        return f'{self.alumno} - {self.clase}'


class Evento(models.Model):
    """Fecha importante del calendario. No lleva nota: la plataforma no califica."""

    class Tipo(models.TextChoices):
        ENTREGA = 'entrega', 'Entrega'
        PARCIAL = 'parcial', 'Parcial'
        PRESENTACION = 'presentacion', 'Presentación'
        FINAL = 'final', 'Final'

    catedra = models.ForeignKey(Catedra, on_delete=models.CASCADE, related_name='eventos')
    tipo = models.CharField(max_length=20, choices=Tipo.choices)
    titulo = models.CharField(max_length=200)
    fecha = models.DateField()
    # Si la fecha corresponde a una entrega dentro del aula, el estado sale del Progreso.
    contenido = models.ForeignKey(
        Contenido, on_delete=models.SET_NULL, null=True, blank=True, related_name='eventos',
    )

    class Meta:
        ordering = ['fecha']

    def __str__(self):
        return f'{self.get_tipo_display()}: {self.titulo}'


class Aviso(models.Model):
    """Comunicación de la cátedra. Solo el profesorado publica."""

    catedra = models.ForeignKey(Catedra, on_delete=models.CASCADE, related_name='avisos')
    autor = models.ForeignKey(
        Usuario, on_delete=models.SET_NULL, null=True, related_name='avisos',
        limit_choices_to={'groups__name': 'profesor'},
    )
    titulo = models.CharField(max_length=200)
    cuerpo = models.TextField()
    publicado_en = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-publicado_en']

    def __str__(self):
        return self.titulo
