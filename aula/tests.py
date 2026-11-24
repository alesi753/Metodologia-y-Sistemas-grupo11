# Tests automáticos del aula: verifican reglas de dominio y vistas.
# `python manage.py test` crea una base de datos temporal aparte (test_...) y la
# destruye al terminar, así que nunca tocan db.sqlite3 ni datos reales.
from datetime import time, timedelta
from io import StringIO

from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.core.management import CommandError, call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .management import datos_demo
from .models import (
    Alumno, Asistencia, Aviso, Carrera, Catedra, Clase, Contenido, Evento, Horario, Materia,
    Progreso, Unidad, Usuario,
)


class RoadmapTests(TestCase):
    def setUp(self):
        self.hoy = timezone.localdate()
        self.alumno = Usuario.objects.create_user('1001', password='clave-segura-123')
        materia = Materia.objects.create(nombre='Legislación', carrera=Carrera.objects.create(nombre='TUP'))
        self.catedra = Catedra.objects.create(materia=materia, anio=2026, cuatrimestre=2)
        self.catedra.alumnos.add(self.alumno)
        self.u1 = Unidad.objects.create(catedra=self.catedra, orden=1, titulo='Constitucional')
        self.u2 = Unidad.objects.create(catedra=self.catedra, orden=2, titulo='Civil')
        self.texto = Contenido.objects.create(unidad=self.u1, formato='texto', titulo='Teoría', publicado=True)
        Contenido.objects.create(unidad=self.u2, formato='texto', titulo='Personas', publicado=True)

    def completar(self, contenido, cuando=None):
        return Progreso.objects.create(
            alumno=self.alumno, contenido=contenido, completado_en=cuando or timezone.now(),
        )

    def test_desbloqueo_secuencial(self):
        self.assertTrue(self.u1.esta_desbloqueada(self.alumno))
        self.assertFalse(self.u2.esta_desbloqueada(self.alumno))
        self.completar(self.texto)
        self.assertTrue(self.u2.esta_desbloqueada(self.alumno))

    def test_borrador_no_bloquea(self):
        Contenido.objects.create(unidad=self.u1, formato='texto', titulo='Borrador')
        self.completar(self.texto)
        self.assertTrue(self.u1.completada_por(self.alumno))

    def test_unidad_sin_contenido_no_esta_completa(self):
        vacia = Unidad.objects.create(catedra=self.catedra, orden=3, titulo='Vacía')
        self.assertFalse(vacia.completada_por(self.alumno))

    def test_fecha_apertura_futura_bloquea(self):
        self.u2.fecha_apertura = self.hoy + timedelta(days=5)
        self.completar(self.texto)
        self.assertFalse(self.u2.esta_desbloqueada(self.alumno))

    def test_apertura_posterior_al_limite_es_invalida(self):
        self.u2.fecha_apertura = self.hoy
        self.u2.fecha_limite = self.hoy - timedelta(days=1)
        with self.assertRaises(ValidationError):
            self.u2.clean()

    def test_en_termino(self):
        self.u1.fecha_limite = self.hoy - timedelta(days=1)
        self.u1.save()
        self.assertFalse(self.completar(self.texto).en_termino())

    def crear_fe_de_erratas(self, orden=3):
        errata = Unidad.objects.create(
            catedra=self.catedra, orden=orden, titulo='Fe de erratas', es_fe_de_erratas=True,
        )
        errata.corrige.add(self.u1)
        Contenido.objects.create(unidad=errata, formato='texto', titulo='Corrección', publicado=True)
        return errata

    def test_fe_de_erratas_no_bloquea_la_secuencia(self):
        self.crear_fe_de_erratas(orden=3)
        u4 = Unidad.objects.create(catedra=self.catedra, orden=4, titulo='Penal')
        self.completar(self.texto)
        self.completar(self.u2.contenidos.get())
        self.assertTrue(u4.esta_desbloqueada(self.alumno))

    def test_fe_de_erratas_se_abre_al_completar_lo_que_corrige(self):
        errata = self.crear_fe_de_erratas()
        self.assertFalse(errata.esta_desbloqueada(self.alumno))
        self.completar(self.texto)
        self.assertTrue(errata.esta_desbloqueada(self.alumno))

    def test_unidad_actual_ignora_fe_de_erratas(self):
        self.crear_fe_de_erratas(orden=3)
        alumno = Alumno._base_manager.get(pk=self.alumno.pk)
        self.completar(self.texto)
        self.completar(self.u2.contenidos.get())
        self.assertIsNone(alumno.unidad_actual(self.catedra))

    def test_horario_inicio_posterior_al_fin_es_invalido(self):
        horario = Horario(catedra=self.catedra, dia=0, hora_inicio=time(20), hora_fin=time(18))
        with self.assertRaises(ValidationError):
            horario.clean()

    def test_roadmap_requiere_login(self):
        respuesta = self.client.get(reverse('roadmap', args=[self.catedra.id]))
        self.assertRedirects(respuesta, f"{reverse('login')}?next=/cursada/{self.catedra.id}/")

    def test_roadmap_solo_para_inscriptos(self):
        self.client.force_login(Usuario.objects.create_user('1002'))
        respuesta = self.client.get(reverse('roadmap', args=[self.catedra.id]))
        self.assertEqual(respuesta.status_code, 404)

    def test_roadmap_oculta_unidades_bloqueadas(self):
        self.client.force_login(self.alumno)
        respuesta = self.client.get(reverse('roadmap', args=[self.catedra.id]))
        self.assertContains(respuesta, 'Teoría')
        self.assertNotContains(respuesta, 'Personas')


# El runner de tests fuerza DEBUG=False y el comando solo corre con DEBUG.
# MD5 acelera los tests: el comando crea varios usuarios con contraseña.
@override_settings(DEBUG=True, PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class CargarDemoTests(TestCase):
    MODELOS = [
        Usuario, Carrera, Materia, Catedra, Horario, Unidad, Contenido, Progreso, Clase,
        Asistencia, Evento, Aviso,
    ]

    def cargar(self, *opciones):
        call_command('cargar_demo', *opciones, stdout=StringIO())

    def contar(self):
        return {modelo.__name__: modelo.objects.count() for modelo in self.MODELOS}

    def test_los_grupos_de_rol_existen(self):
        self.assertEqual(Group.objects.filter(name__in=['alumno', 'profesor']).count(), 2)

    def test_carga_alumnos_y_profesores_con_su_rol(self):
        self.cargar()
        self.assertTrue(Alumno.objects.filter(username=datos_demo.ALUMNO_DEMO).exists())
        self.assertEqual(Usuario.objects.filter(groups__name='profesor').count(), len(datos_demo.PROFESORES))
        self.assertEqual(Catedra.objects.filter(alumnos__username=datos_demo.ALUMNO_DEMO).count(), 4)

    def test_es_idempotente(self):
        self.cargar()
        antes = self.contar()
        self.cargar()
        self.assertEqual(self.contar(), antes)

    def test_reset_vuelve_a_cargar(self):
        self.cargar()
        antes = self.contar()
        Aviso.objects.all().delete()
        self.cargar('--reset')
        self.assertEqual(self.contar(), antes)

    def test_sin_debug_falla(self):
        with self.settings(DEBUG=False), self.assertRaises(CommandError):
            self.cargar()
        self.assertFalse(Usuario.objects.exists())

    def test_entregas_en_termino_y_fuera_de_termino(self):
        self.cargar()
        practicas = Progreso.objects.filter(
            alumno__username=datos_demo.ALUMNO_DEMO, contenido__formato='practica',
        )
        self.assertEqual({p.en_termino() for p in practicas}, {True, False})

    def test_el_alumno_demo_ve_su_roadmap(self):
        self.cargar()
        alumno = Usuario.objects.get(username=datos_demo.ALUMNO_DEMO)
        catedra = alumno.cursadas.get(materia__nombre='Gestión de Desarrollo de Software')
        self.client.force_login(alumno)
        respuesta = self.client.get(reverse('roadmap', args=[catedra.id]))
        self.assertContains(respuesta, 'Plan de proyecto')
        estados = [item['estado'] for item in respuesta.context['unidades']]
        self.assertEqual(estados, ['completa', 'en curso', 'bloqueada', 'en curso'])
