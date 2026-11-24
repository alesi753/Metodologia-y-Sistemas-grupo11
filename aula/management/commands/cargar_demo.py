# Comando de desarrollo: carga una cursada de ejemplo para probar el frontend con datos reales.
# Los datos están en aula/management/datos_demo.py.
from datetime import datetime, time, timedelta

from django.conf import settings
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.urls import reverse
from django.utils import timezone

from aula.management import datos_demo as datos
from aula.models import (
    Asistencia, Aviso, Carrera, Catedra, Clase, Contenido, Evento, Horario, Materia, Progreso,
    Unidad, Usuario,
)

SERVIDOR = 'http://127.0.0.1:8000'


class Command(BaseCommand):
    help = 'Carga una cursada de ejemplo con fechas relativas a hoy. Solo corre con DEBUG.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset', action='store_true',
            help='Borra lo cargado por la demo y lo vuelve a cargar.',
        )

    def handle(self, *args, reset=False, **options):
        # Crea usuarios con una contraseña conocida: nunca en producción.
        if not settings.DEBUG:
            raise CommandError('cargar_demo solo corre con DEBUG=True.')

        with transaction.atomic():
            if reset:
                borrar_demo()
            if Usuario.objects.filter(username=datos.ALUMNO_DEMO).exists():
                self.stdout.write('La demo ya estaba cargada. Usá --reset para cargarla de nuevo.')
            else:
                CargaDemo(timezone.localdate()).cargar()
                self.stdout.write(self.style.SUCCESS('Demo cargada.'))

        self.imprimir_accesos()

    def imprimir_accesos(self):
        escribir = self.stdout.write
        escribir(f'\nUsuarios (contraseña para todos: {datos.CLAVE})')
        escribir(f'  admin      {datos.ADMIN}')
        for legajo, nombre, apellido in datos.ALUMNOS:
            demo = '  <- alumno de la demo' if legajo == datos.ALUMNO_DEMO else ''
            escribir(f'  alumno     {legajo}  {nombre} {apellido}{demo}')
        for legajo, nombre, apellido in datos.PROFESORES:
            escribir(f'  profesor   {legajo}  {nombre} {apellido}')

        escribir('\nPara visitar')
        escribir(f"  {SERVIDOR}{reverse('inicio')}  inicio")
        cursadas = Catedra.objects.filter(alumnos__username=datos.ALUMNO_DEMO).select_related('materia')
        for catedra in cursadas:
            escribir(f"  {SERVIDOR}{reverse('roadmap', args=[catedra.id])}  {catedra.materia}")
        escribir(f"  {SERVIDOR}{reverse('admin:index')}  admin")


def borrar_demo():
    """Borra solo lo que crea la demo: sus materias (en cascada) y sus usuarios."""
    materias = [c['materia'] for c in datos.CATEDRAS]
    Materia.objects.filter(carrera__nombre=datos.CARRERA, nombre__in=materias).delete()
    Carrera.objects.filter(nombre=datos.CARRERA, materias__isnull=True).delete()
    legajos = [u[0] for u in datos.ALUMNOS + datos.PROFESORES] + [datos.ADMIN]
    Usuario.objects.filter(username__in=legajos).delete()


class CargaDemo:
    def __init__(self, hoy):
        self.hoy = hoy
        self.ahora = timezone.now()
        self.usuarios = {}

    def dia(self, desplazamiento):
        if desplazamiento is None:
            return None
        return self.hoy + timedelta(days=desplazamiento)

    def cargar(self):
        self.crear_usuarios()
        self.alumno = self.usuarios[datos.ALUMNO_DEMO]
        carrera, _ = Carrera.objects.get_or_create(nombre=datos.CARRERA)
        for dato in datos.CATEDRAS:
            self.crear_catedra(carrera, dato)

    def crear_usuarios(self):
        Usuario.objects.create_superuser(datos.ADMIN, f'{datos.ADMIN}@demo.local', datos.CLAVE)
        for rol, personas in [('alumno', datos.ALUMNOS), ('profesor', datos.PROFESORES)]:
            grupo = Group.objects.get(name=rol)
            for legajo, nombre, apellido in personas:
                usuario = Usuario.objects.create_user(
                    legajo, f'{legajo}@demo.local', datos.CLAVE,
                    first_name=nombre, last_name=apellido,
                )
                usuario.groups.add(grupo)
                self.usuarios[legajo] = usuario

    def crear_catedra(self, carrera, dato):
        materia = Materia.objects.create(carrera=carrera, nombre=dato['materia'])
        catedra = Catedra.objects.create(
            materia=materia, anio=self.hoy.year, cuatrimestre=1 if self.hoy.month <= 7 else 2,
        )
        profesores = [self.usuarios[legajo] for legajo in dato['profesores']]
        catedra.profesores.set(profesores)
        catedra.alumnos.set(self.usuarios[legajo] for legajo, _, _ in datos.ALUMNOS)

        horarios = self.crear_horarios(catedra, dato['horarios'])
        unidades, contenidos = self.crear_unidades(catedra, dato['unidades'], autor=profesores[0])
        self.crear_clases(catedra, dato, horarios, unidades, contenidos)
        for tipo, titulo, dias, clave in dato['eventos']:
            Evento.objects.create(
                catedra=catedra, tipo=tipo, titulo=titulo, fecha=self.dia(dias),
                contenido=contenidos.get(clave),
            )
        for autor, dias, titulo, cuerpo in dato['avisos']:
            Aviso.objects.create(
                catedra=catedra, autor=self.usuarios[autor], titulo=titulo, cuerpo=cuerpo,
                publicado_en=self.ahora + timedelta(days=dias, hours=-2),
            )

    def crear_horarios(self, catedra, horarios):
        # Los días se cuentan desde hoy, así siempre hay alguna clase hoy.
        # Horario no tiene domingo: ese día la demo arranca desde el sábado.
        hoy = min(self.hoy.weekday(), Horario.Dia.SABADO)
        return [
            Horario.objects.create(
                catedra=catedra, dia=(hoy + despues) % 6,
                hora_inicio=time.fromisoformat(desde), hora_fin=time.fromisoformat(hasta),
            )
            for despues, desde, hasta in horarios
        ]

    def crear_unidades(self, catedra, unidades, autor):
        """Devuelve las unidades por orden y los contenidos por clave."""
        por_orden, por_clave = {}, {}
        for dato in unidades:
            unidad = Unidad.objects.create(
                catedra=catedra, orden=dato['orden'], titulo=dato['titulo'],
                conceptos=dato.get('conceptos', []),
                fecha_apertura=self.dia(dato.get('apertura')),
                fecha_limite=self.dia(dato.get('limite')),
                es_fe_de_erratas='corrige' in dato,
            )
            unidad.corrige.set(por_orden[orden] for orden in dato.get('corrige', []))
            por_orden[unidad.orden] = unidad
            for contenido in dato['contenidos']:
                por_clave[contenido['clave']] = self.crear_contenido(unidad, contenido, autor)
        return por_orden, por_clave

    def crear_contenido(self, unidad, dato, autor):
        contenido = Contenido.objects.create(
            unidad=unidad, autor=autor, formato=dato['formato'], titulo=dato['titulo'],
            cuerpo=dato['cuerpo'], publicado=not dato.get('borrador', False),
        )
        if 'completado' in dato:
            respuesta = {}
            if contenido.formato == Contenido.Formato.CUESTIONARIO:
                respuesta = {'respuestas': [p['correcta'] for p in contenido.cuerpo['preguntas']]}
            Progreso.objects.create(
                alumno=self.alumno, contenido=contenido, respuesta=respuesta,
                completado_en=self.ahora + timedelta(days=dato['completado']),
                intentos=dato.get('intentos', 1),
            )
        return contenido

    def crear_clases(self, catedra, dato, horarios, unidades, contenidos):
        fechas = self.fechas_de_clase(horarios, dato['clases_pasadas'])
        pares = zip(fechas, dato['clases'])
        for numero, ((fecha, horario), clase_dato) in enumerate(pares, start=dato['primera_clase']):
            clase = Clase.objects.create(
                catedra=catedra, numero=numero, fecha=fecha,
                hora_inicio=horario.hora_inicio, hora_fin=horario.hora_fin,
                titulo=clase_dato['titulo'], resumen=clase_dato['resumen'],
                unidad=unidades.get(clase_dato.get('unidad')),
                link_videollamada=clase_dato.get('link', ''),
            )
            clase.contenidos.set(contenidos[clave] for clave in clase_dato.get('contenidos', []))
            if fecha < self.hoy and not clase_dato.get('ausente'):
                # registrada_en es auto_now_add: se corrige después para que coincida con la clase.
                asistencia = Asistencia.objects.create(alumno=self.alumno, clase=clase)
                Asistencia.objects.filter(pk=asistencia.pk).update(
                    registrada_en=timezone.make_aware(datetime.combine(fecha, horario.hora_inicio)),
                )

    def fechas_de_clase(self, horarios, pasadas):
        """Días de cursada según los horarios: los `pasadas` anteriores a hoy y los que siguen."""
        inicio = self.hoy - timedelta(weeks=6)
        dias = []
        for i in range(12 * 7):
            fecha = inicio + timedelta(days=i)
            dias += [(fecha, h) for h in horarios if h.dia == fecha.weekday()]
        anteriores = [d for d in dias if d[0] < self.hoy]
        siguientes = [d for d in dias if d[0] >= self.hoy]
        return anteriores[len(anteriores) - pasadas:] + siguientes
