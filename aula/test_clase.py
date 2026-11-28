from datetime import date, datetime, time, timedelta

from django.contrib.auth.models import Group
from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from django.utils import timezone

from .models import (
    Asistencia, Carrera, Catedra, Clase, Contenido, Materia, Progreso, Unidad, Usuario,
)
from .views.clase import en_vivo

TEXTO = {'secciones': [{'titulo': 'Intro', 'texto': 'Hola'}]}
PRACTICA = {'consigna': 'Hacer', 'entregables': ['informe'], 'formatos_aceptados': 'pdf'}
LINK = 'https://meet.example.com/clase'


class ClaseTests(TestCase):
    def setUp(self):
        self.hoy = timezone.localdate()
        self.alumno = Usuario.objects.create_user('1001', password='clave-segura-123')
        self.alumno.groups.add(Group.objects.get(name='alumno'))
        materia = Materia.objects.create(nombre='Legislación', carrera=Carrera.objects.create(nombre='TUP'))
        self.catedra = Catedra.objects.create(materia=materia, anio=2026, cuatrimestre=2)
        self.catedra.alumnos.add(self.alumno)
        self.u1 = Unidad.objects.create(catedra=self.catedra, orden=1, titulo='Constitucional')
        self.u2 = Unidad.objects.create(catedra=self.catedra, orden=2, titulo='Civil')
        self.lectura = Contenido.objects.create(
            unidad=self.u1, formato='texto', titulo='Lectura', cuerpo=TEXTO, publicado=True,
        )
        self.tp = Contenido.objects.create(
            unidad=self.u1, formato='practica', titulo='TP 1', cuerpo=PRACTICA, publicado=True,
        )
        self.borrador = Contenido.objects.create(
            unidad=self.u1, formato='texto', titulo='Borrador', cuerpo=TEXTO,
        )
        self.client.force_login(self.alumno)

    def clase(self, numero, dias, unidad=None, link=LINK, desde='00:00', hasta='23:59:59'):
        return Clase.objects.create(
            catedra=self.catedra, numero=numero, fecha=self.hoy + timedelta(days=dias),
            hora_inicio=time.fromisoformat(desde), hora_fin=time.fromisoformat(hasta),
            titulo=f'Tema {numero}', resumen='Temario de la clase', unidad=unidad,
            link_videollamada=link,
        )

    def unirse(self, clase):
        return self.client.post(reverse('unirse', args=[clase.id]))

    # CU-05: clase del día

    def test_clase_de_hoy_con_material_y_tareas(self):
        clase = self.clase(1, 0, unidad=self.u1)
        clase.contenidos.set([self.lectura, self.tp, self.borrador])
        Progreso.objects.create(alumno=self.alumno, contenido=self.lectura, completado_en=timezone.now())
        respuesta = self.client.get(reverse('clase_hoy'))
        item = respuesta.context['clases'][0]
        self.assertEqual(item['material'], [self.lectura])
        self.assertEqual(item['tareas'], [self.tp])
        self.assertIn(self.lectura.id, item['hechos'])
        self.assertContains(respuesta, 'Temario de la clase')
        self.assertContains(respuesta, 'Unirse a la clase en vivo')
        self.assertNotContains(respuesta, 'Borrador')

    def test_sin_clase_hoy_muestra_la_proxima(self):
        proxima = self.clase(1, 2)
        respuesta = self.client.get(reverse('clase_hoy'))
        self.assertContains(respuesta, 'Hoy no tenés clases.')
        self.assertEqual(respuesta.context['proxima'], proxima)

    def test_clase_futura_de_unidad_abierta_se_puede_adelantar(self):
        self.clase(1, 1)
        adelantable = self.clase(2, 5, unidad=self.u1)
        bloqueada = self.clase(3, 6, unidad=self.u2)
        respuesta = self.client.get(reverse('clase_hoy'))
        self.assertEqual(respuesta.context['habilitadas'], [adelantable])
        self.assertTrue(self.client.get(reverse('clase', args=[adelantable.id])).context['habilitada'])
        detalle = self.client.get(reverse('clase', args=[bloqueada.id]))
        self.assertFalse(detalle.context['habilitada'])
        self.assertContains(detalle, 'todavía no está habilitada')

    def test_clase_ajena_da_404(self):
        otra = Catedra.objects.create(materia=self.catedra.materia, anio=2025, cuatrimestre=1)
        clase = Clase.objects.create(catedra=otra, numero=1, fecha=self.hoy, hora_inicio=time(0),
                                     hora_fin=time(23, 59), titulo='Ajena')
        self.assertEqual(self.client.get(reverse('clase', args=[clase.id])).status_code, 404)
        self.assertEqual(self.unirse(clase).status_code, 404)

    def test_aparece_en_la_navegacion_del_alumno(self):
        respuesta = self.client.get(reverse('clase_hoy'))
        self.assertContains(respuesta, 'aria-current="page">Clase de hoy')

    # CU-06: unirse a la clase en vivo

    def test_unirse_registra_asistencia_y_redirige_al_link(self):
        clase = self.clase(1, 0)
        respuesta = self.unirse(clase)
        self.assertRedirects(respuesta, LINK, fetch_redirect_response=False)
        self.assertTrue(Asistencia.objects.filter(alumno=self.alumno, clase=clase).exists())
        self.unirse(clase)
        self.assertEqual(Asistencia.objects.filter(alumno=self.alumno, clase=clase).count(), 1)
        self.assertContains(self.client.get(reverse('clase_hoy')), 'Presente registrado')

    def test_no_se_puede_unir_a_una_clase_que_no_esta_en_vivo(self):
        # Pasado mañana y no mañana: una clase de mañana a las 00:00 abre a las 23:45 de hoy.
        for clase in (self.clase(1, 2), self.clase(2, -1)):
            respuesta = self.unirse(clase)
            self.assertRedirects(respuesta, reverse('clase', args=[clase.id]))
        self.assertFalse(Asistencia.objects.exists())
        respuesta = self.client.post(reverse('unirse', args=[clase.id]), follow=True)
        self.assertContains(respuesta, 'no está disponible en este momento')

    def test_sin_link_no_registra_asistencia(self):
        clase = self.clase(1, 0, link='')
        self.assertRedirects(self.unirse(clase), reverse('clase', args=[clase.id]))
        self.assertFalse(Asistencia.objects.exists())

    def test_unirse_solo_por_post(self):
        clase = self.clase(1, 0)
        self.assertEqual(self.client.get(reverse('unirse', args=[clase.id])).status_code, 405)
        self.assertFalse(Asistencia.objects.exists())

    def test_rechaza_otros_roles(self):
        profe = Usuario.objects.create_user('2001', password='clave-segura-123')
        profe.groups.add(Group.objects.get(name='profesor'))
        self.client.force_login(profe)
        self.assertEqual(self.client.get(reverse('clase_hoy')).status_code, 403)


class VentanaEnVivoTests(SimpleTestCase):
    def setUp(self):
        self.clase = Clase(fecha=date(2026, 10, 5), hora_inicio=time(18, 30), hora_fin=time(20))

    def en(self, hora, minuto):
        return en_vivo(self.clase, datetime(2026, 10, 5, hora, minuto))

    def test_se_abre_15_minutos_antes(self):
        self.assertFalse(self.en(18, 14))
        self.assertTrue(self.en(18, 15))

    def test_se_cierra_al_terminar(self):
        self.assertTrue(self.en(20, 0))
        self.assertFalse(self.en(20, 1))
