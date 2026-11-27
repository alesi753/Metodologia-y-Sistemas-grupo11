from datetime import time, timedelta

from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Aviso, Carrera, Catedra, Clase, Horario, Materia, Unidad, Usuario


class CursoTests(TestCase):
    def setUp(self):
        self.hoy = timezone.localdate()
        self.alumno = Usuario.objects.create_user('1001', password='clave-segura-123')
        self.alumno.groups.add(Group.objects.get(name='alumno'))
        self.profe = Usuario.objects.create_user(
            '2001', password='clave-segura-123', first_name='Marta', last_name='Ríos',
        )
        self.profe.groups.add(Group.objects.get(name='profesor'))
        materia = Materia.objects.create(nombre='Legislación', carrera=Carrera.objects.create(nombre='TUP'))
        self.catedra = Catedra.objects.create(materia=materia, anio=2026, cuatrimestre=2)
        self.catedra.alumnos.add(self.alumno)
        self.catedra.profesores.add(self.profe)
        Unidad.objects.create(catedra=self.catedra, orden=1, titulo='Constitucional',
                              conceptos=['Derechos', 'Garantías'])
        self.client.force_login(self.alumno)

    def clase(self, numero, dias, desde='18:00', hasta='20:00'):
        return Clase.objects.create(
            catedra=self.catedra, numero=numero, fecha=self.hoy + timedelta(days=dias),
            hora_inicio=time.fromisoformat(desde), hora_fin=time.fromisoformat(hasta),
            titulo=f'Tema {numero}',
        )

    def ficha(self):
        return self.client.get(reverse('roadmap', args=[self.catedra.id]))

    def test_ficha_con_profesorado_horarios_y_conceptos(self):
        Horario.objects.create(catedra=self.catedra, dia=Horario.Dia.LUNES,
                               hora_inicio=time(18, 30), hora_fin=time(20))
        respuesta = self.ficha()
        self.assertContains(respuesta, 'Marta Ríos')
        self.assertContains(respuesta, 'Lunes 18:30-20:00')
        self.assertContains(respuesta, 'Derechos · Garantías')

    def test_proxima_clase_ignora_las_pasadas(self):
        self.clase(1, -2)
        proxima = self.clase(2, 3)
        self.assertEqual(self.ficha().context['proxima_clase'], proxima)

    def test_clase_de_hoy_que_ya_termino_no_es_la_proxima(self):
        self.clase(1, 0, '00:00', '00:01')
        proxima = self.clase(2, 1)
        self.assertEqual(self.ficha().context['proxima_clase'], proxima)

    def test_sin_clases_programadas(self):
        self.assertContains(self.ficha(), 'No hay clases programadas.')

    def test_ficha_muestra_el_ultimo_aviso_publicado(self):
        Aviso.objects.create(catedra=self.catedra, titulo='Viejo', cuerpo='...',
                             publicado_en=timezone.now() - timedelta(days=2))
        Aviso.objects.create(catedra=self.catedra, titulo='Nuevo', cuerpo='...')
        Aviso.objects.create(catedra=self.catedra, titulo='Programado', cuerpo='...',
                             publicado_en=timezone.now() + timedelta(days=1))
        self.assertEqual(self.ficha().context['ultimo_aviso'].titulo, 'Nuevo')


class AvisosTests(TestCase):
    def setUp(self):
        self.alumno = Usuario.objects.create_user('1001', password='clave-segura-123')
        self.alumno.groups.add(Group.objects.get(name='alumno'))
        materia = Materia.objects.create(nombre='Legislación', carrera=Carrera.objects.create(nombre='TUP'))
        self.catedra = Catedra.objects.create(materia=materia, anio=2026, cuatrimestre=2)
        self.catedra.alumnos.add(self.alumno)
        self.url = reverse('avisos', args=[self.catedra.id])

    def test_lista_los_avisos_publicados_del_mas_nuevo_al_mas_viejo(self):
        Aviso.objects.create(catedra=self.catedra, titulo='Viejo', cuerpo='...',
                             publicado_en=timezone.now() - timedelta(days=2))
        Aviso.objects.create(catedra=self.catedra, titulo='Nuevo', cuerpo='Línea 1\nLínea 2')
        Aviso.objects.create(catedra=self.catedra, titulo='Programado', cuerpo='...',
                             publicado_en=timezone.now() + timedelta(days=1))
        self.client.force_login(self.alumno)
        respuesta = self.client.get(self.url)
        self.assertEqual([a.titulo for a in respuesta.context['avisos']], ['Nuevo', 'Viejo'])
        self.assertContains(respuesta, 'Línea 1<br>Línea 2')

    def test_sin_avisos(self):
        self.client.force_login(self.alumno)
        self.assertContains(self.client.get(self.url), 'La cátedra todavía no publicó avisos.')

    def test_requiere_login(self):
        respuesta = self.client.get(self.url)
        self.assertRedirects(respuesta, f"{reverse('login')}?next={self.url}")

    def test_solo_para_inscriptos(self):
        otro = Usuario.objects.create_user('1002', password='clave-segura-123')
        otro.groups.add(Group.objects.get(name='alumno'))
        self.client.force_login(otro)
        self.assertEqual(self.client.get(self.url).status_code, 404)

    def test_rechaza_otros_roles(self):
        profe = Usuario.objects.create_user('2001', password='clave-segura-123')
        profe.groups.add(Group.objects.get(name='profesor'))
        self.client.force_login(profe)
        self.assertEqual(self.client.get(self.url).status_code, 403)
