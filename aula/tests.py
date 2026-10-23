# Tests automáticos del aula: verifican reglas de dominio y vistas.
# `python manage.py test` crea una base de datos temporal aparte (test_...) y la
# destruye al terminar, así que nunca tocan db.sqlite3 ni datos reales.
from datetime import timedelta

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Carrera, Catedra, Contenido, Materia, Progreso, Unidad, Usuario


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
