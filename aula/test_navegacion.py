from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import NoReverseMatch, reverse

from .context_processors import MENUS
from .models import Carrera, Catedra, Materia, Usuario


class NavegacionTests(TestCase):
    def setUp(self):
        self.alumno = Usuario.objects.create_user('1001', password='clave-segura-123')
        self.alumno.groups.add(Group.objects.get(name='alumno'))
        self.profe = Usuario.objects.create_user('2001', password='clave-segura-123')
        self.profe.groups.add(Group.objects.get(name='profesor'))
        materia = Materia.objects.create(nombre='Legislación', carrera=Carrera.objects.create(nombre='TUP'))
        self.catedra = Catedra.objects.create(materia=materia, anio=2026, cuatrimestre=2)
        self.catedra.alumnos.add(self.alumno)

    def test_login_sin_navegacion_inferior(self):
        respuesta = self.client.get(reverse('login'))
        self.assertNotContains(respuesta, 'navegacion-inferior')
        self.assertEqual(respuesta.context['menu'], [])

    def test_alumno_ve_su_menu_con_la_pantalla_activa(self):
        self.client.force_login(self.alumno)
        respuesta = self.client.get(reverse('inicio'))
        self.assertContains(respuesta, 'navegacion-inferior')
        self.assertContains(respuesta, f'<a href="{reverse("inicio")}" aria-current="page">Inicio</a>', html=True)

    def test_el_menu_omite_pantallas_que_todavia_no_existen(self):
        self.client.force_login(self.alumno)
        respuesta = self.client.get(reverse('inicio'))
        etiquetas = [item['etiqueta'] for item in respuesta.context['menu']]
        self.assertIn('Inicio', etiquetas)
        for nombre, etiqueta in MENUS['alumno']:
            try:
                reverse(nombre)
            except NoReverseMatch:
                self.assertNotIn(etiqueta, etiquetas)

    def test_otra_pantalla_no_marca_inicio_como_activa(self):
        self.client.force_login(self.alumno)
        respuesta = self.client.get(reverse('roadmap', args=[self.catedra.id]))
        self.assertNotContains(respuesta, 'aria-current="page"')

    def test_lugar_del_tutor_solo_para_alumnos(self):
        self.client.force_login(self.alumno)
        self.assertContains(self.client.get(reverse('inicio')), 'id="tutor"')
        self.client.force_login(self.profe)
        self.assertNotContains(self.client.get(reverse('inicio')), 'id="tutor"')

    def test_profesor_ve_su_menu(self):
        self.client.force_login(self.profe)
        respuesta = self.client.get(reverse('inicio'))
        self.assertTrue(respuesta.context['es_profesor'])
        self.assertEqual([i['etiqueta'] for i in respuesta.context['menu']], ['Inicio'])
