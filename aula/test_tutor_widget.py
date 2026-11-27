from datetime import time

from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Carrera, Catedra, Clase, Contenido, Materia, Unidad, Usuario

TEXTO = {'secciones': [{'titulo': 'Intro', 'texto': 'Hola'}]}


class TutorWidgetTests(TestCase):
    def setUp(self):
        self.alumno = Usuario.objects.create_user('1001', password='clave-segura-123')
        self.alumno.groups.add(Group.objects.get(name='alumno'))
        materia = Materia.objects.create(nombre='Legislación', carrera=Carrera.objects.create(nombre='TUP'))
        self.catedra = Catedra.objects.create(materia=materia, anio=2026, cuatrimestre=2)
        self.catedra.alumnos.add(self.alumno)
        unidad = Unidad.objects.create(catedra=self.catedra, orden=1, titulo='Constitucional')
        self.contenido = Contenido.objects.create(
            unidad=unidad, formato='texto', titulo='Lectura', cuerpo=TEXTO, publicado=True,
        )
        self.clase = Clase.objects.create(
            catedra=self.catedra, numero=1, fecha=timezone.localdate(),
            hora_inicio=time(18), hora_fin=time(20), titulo='Tema 1',
        )

    def test_el_alumno_ve_el_widget_en_todas_sus_pantallas(self):
        self.client.force_login(self.alumno)
        for url in [
            reverse('inicio'), reverse('calendario'), reverse('clase_hoy'),
            reverse('roadmap', args=[self.catedra.id]),
        ]:
            respuesta = self.client.get(url)
            self.assertContains(respuesta, 'class="tutor-boton"')
            self.assertContains(respuesta, f'data-url="{reverse("tutor_consultar")}"')
            self.assertContains(respuesta, 'aula/tutor.js')

    def test_manda_el_contexto_de_la_pantalla(self):
        self.client.force_login(self.alumno)
        casos = [
            (reverse('roadmap', args=[self.catedra.id]), 'roadmap', f'data-catedra-id="{self.catedra.id}"'),
            (reverse('avisos', args=[self.catedra.id]), 'avisos', f'data-catedra-id="{self.catedra.id}"'),
            (reverse('clase', args=[self.clase.id]), 'clase', f'data-clase-id="{self.clase.id}"'),
            (reverse('contenido', args=[self.contenido.id]), 'contenido',
             f'data-contenido-id="{self.contenido.id}"'),
        ]
        for url, pantalla, atributo in casos:
            respuesta = self.client.get(url)
            self.assertContains(respuesta, f'data-pantalla="{pantalla}"')
            self.assertContains(respuesta, atributo)

    def test_inicio_no_manda_ids(self):
        self.client.force_login(self.alumno)
        respuesta = self.client.get(reverse('inicio'))
        self.assertEqual(respuesta.context['tutor'], {'pantalla': 'inicio'})
        self.assertNotContains(respuesta, 'data-catedra-id')

    def test_profesor_y_anonimo_no_ven_el_widget(self):
        self.assertNotContains(self.client.get(reverse('login')), 'tutor-boton')
        profe = Usuario.objects.create_user('2001', password='clave-segura-123')
        profe.groups.add(Group.objects.get(name='profesor'))
        self.client.force_login(profe)
        respuesta = self.client.get(reverse('inicio'))
        self.assertNotContains(respuesta, 'tutor-boton')
        self.assertIsNone(respuesta.context['tutor'])
