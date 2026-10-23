# Módulo de datos: entidades del aula virtual (ver docs/schemas/schema.mmd)
from django.contrib.auth.models import AbstractUser, UserManager
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
        for unidad in catedra.unidades.all():
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
    fecha_limite = models.DateField(null=True, blank=True)

    class Meta:
        verbose_name_plural = 'unidades'
        ordering = ['orden']
        constraints = [
            models.UniqueConstraint(fields=['catedra', 'orden'], name='unidad_orden_unico'),
        ]

    def __str__(self):
        return f'Unidad {self.orden}: {self.titulo}'

    def completada_por(self, alumno):
        completados = Progreso.objects.filter(
            alumno=alumno, completado_en__isnull=False,
        ).values('contenido')
        pendientes = self.contenidos.filter(publicado=True).exclude(pk__in=completados)
        return not pendientes.exists()

    def esta_desbloqueada(self, alumno):
        """Secuencial: la unidad se abre cuando el alumno completó la anterior."""
        anterior = self.catedra.unidades.filter(orden__lt=self.orden).last()
        return anterior is None or anterior.completada_por(alumno)


class Contenido(models.Model):
    class Formato(models.TextChoices):
        TEXTO = 'texto', 'Texto'
        FLASHCARDS = 'flashcards', 'Flashcards'
        CUESTIONARIO = 'cuestionario', 'Cuestionario'
        PRACTICA = 'practica', 'Práctica'

    unidad = models.ForeignKey(Unidad, on_delete=models.CASCADE, related_name='contenidos')
    autor = models.ForeignKey(
        Usuario, on_delete=models.SET_NULL, null=True, related_name='contenidos',
    )
    formato = models.CharField(max_length=20, choices=Formato.choices)
    titulo = models.CharField(max_length=200)
    cuerpo = models.JSONField(default=dict, blank=True)
    publicado = models.BooleanField(default=False)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return self.titulo


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
