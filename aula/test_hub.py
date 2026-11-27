from datetime import timedelta

from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Aviso, Carrera, Catedra, Contenido, Evento, Materia, Progreso, Unidad, Usuario

TEXTO = {'secciones': [{'titulo': 'Intro', 'texto': 'Hola'}]}


class HubTests(TestCase):
    def setUp(self):
        self.hoy = timezone.localdate()
        self.alumno = Usuario.objects.create_user('1001', password='clave-segura-123')
        self.alumno.groups.add(Group.objects.get(name='alumno'))
        carrera = Carrera.objects.create(nombre='TUP')
        self.catedra = Catedra.objects.create(
            materia=Materia.objects.create(nombre='Legislación', carrera=carrera),
            anio=2026, cuatrimestre=2,
        )
        self.catedra.alumnos.add(self.alumno)
        self.ajena = Catedra.objects.create(
            materia=Materia.objects.create(nombre='Química', carrera=carrera),
            anio=2026, cuatrimestre=2,
        )
        self.u1 = Unidad.objects.create(catedra=self.catedra, orden=1, titulo='Constitucional')
        self.u2 = Unidad.objects.create(catedra=self.catedra, orden=2, titulo='Civil')
        self.c1 = Contenido.objects.create(
            unidad=self.u1, formato='texto', titulo='Lectura', cuerpo=TEXTO, publicado=True,
        )
        self.c2 = Contenido.objects.create(
            unidad=self.u2, formato='texto', titulo='Otra lectura', cuerpo=TEXTO, publicado=True,
        )
        self.client.force_login(self.alumno)

    def get(self):
        return self.client.get(reverse('inicio'))

    def completar(self, contenido):
        Progreso.objects.create(alumno=self.alumno, contenido=contenido, completado_en=timezone.now())

    def test_muestra_unidad_actual_y_progreso(self):
        self.completar(self.c1)
        respuesta = self.get()
        item = respuesta.context['cursadas'][0]
        self.assertEqual(item['unidad_actual'], self.u2)
        self.assertEqual((item['hechos'], item['total']), (1, 2))
        self.assertContains(respuesta, 'Vas por la Unidad 2: Civil')

    def test_recorrido_completo(self):
        self.completar(self.c1)
        self.completar(self.c2)
        self.assertContains(self.get(), 'Completaste el recorrido.')

    def test_proximas_fechas_solo_futuras_y_de_sus_cursadas(self):
        Evento.objects.create(catedra=self.catedra, tipo='parcial', titulo='Primer parcial',
                              fecha=self.hoy + timedelta(days=3))
        Evento.objects.create(catedra=self.catedra, tipo='parcial', titulo='Parcial pasado',
                              fecha=self.hoy - timedelta(days=1))
        Evento.objects.create(catedra=self.ajena, tipo='final', titulo='Final ajeno',
                              fecha=self.hoy + timedelta(days=3))
        titulos = [e.titulo for e in self.get().context['fechas']]
        self.assertEqual(titulos, ['Primer parcial'])

    def test_entrega_muestra_su_estado(self):
        Evento.objects.create(catedra=self.catedra, tipo='entrega', titulo='TP 1',
                              fecha=self.hoy + timedelta(days=2), contenido=self.c1)
        self.assertContains(self.get(), '(pendiente)')
        self.completar(self.c1)
        self.assertContains(self.get(), 'Entregada')

    def test_avisos_publicados_y_de_sus_cursadas(self):
        Aviso.objects.create(catedra=self.catedra, titulo='Cambio de aula', cuerpo='Aula 5')
        Aviso.objects.create(catedra=self.catedra, titulo='Aviso programado', cuerpo='...',
                             publicado_en=timezone.now() + timedelta(days=1))
        Aviso.objects.create(catedra=self.ajena, titulo='Aviso ajeno', cuerpo='...')
        titulos = [a.titulo for a in self.get().context['avisos']]
        self.assertEqual(titulos, ['Cambio de aula'])

    def test_profesor_ve_sus_catedras_sin_hub(self):
        profe = Usuario.objects.create_user('2001', password='clave-segura-123')
        profe.groups.add(Group.objects.get(name='profesor'))
        self.catedra.profesores.add(profe)
        self.client.force_login(profe)
        respuesta = self.get()
        self.assertNotIn('fechas', respuesta.context)
        self.assertContains(respuesta, 'Cátedras a cargo')
