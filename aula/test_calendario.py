from datetime import date, time

from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Carrera, Catedra, Clase, Evento, Horario, Materia, Unidad, Usuario

# Octubre de 2026 empieza un jueves. Los lunes del mes son 5, 12, 19 y 26.
OCTUBRE = '2026-10'


class CalendarioTests(TestCase):
    def setUp(self):
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
        Horario.objects.create(catedra=self.catedra, dia=Horario.Dia.LUNES,
                               hora_inicio=time(18, 30), hora_fin=time(20))
        self.client.force_login(self.alumno)

    def get(self, **params):
        params.setdefault('mes', OCTUBRE)
        return self.client.get(reverse('calendario'), params)

    def agenda(self, respuesta):
        return {dia: [i['titulo'] for i in items] for dia, items in respuesta.context['agenda']}

    def test_horario_semanal_se_repite_en_el_mes(self):
        dias = sorted(self.agenda(self.get()))
        self.assertEqual(dias, [date(2026, 10, d) for d in (5, 12, 19, 26)])

    def test_clase_cargada_reemplaza_al_horario_de_ese_dia(self):
        Clase.objects.create(catedra=self.catedra, numero=1, fecha=date(2026, 10, 12),
                             hora_inicio=time(18, 30), hora_fin=time(20), titulo='Contratos')
        self.assertEqual(self.agenda(self.get())[date(2026, 10, 12)], ['Clase 1: Contratos'])

    def test_horario_no_se_repite_fuera_del_cuatrimestre(self):
        self.assertEqual(self.agenda(self.get(mes='2026-04')), {})

    def test_fechas_importantes_y_cierre_de_unidad(self):
        Evento.objects.create(catedra=self.catedra, tipo='parcial', titulo='Primer parcial',
                              fecha=date(2026, 10, 15))
        Unidad.objects.create(catedra=self.catedra, orden=1, titulo='Civil',
                              fecha_limite=date(2026, 10, 20))
        agenda = self.agenda(self.get())
        self.assertEqual(agenda[date(2026, 10, 15)], ['Parcial: Primer parcial'])
        self.assertEqual(agenda[date(2026, 10, 20)], ['Cierra la Unidad 1: Civil'])

    def test_filtro_por_clases_o_por_fechas(self):
        Evento.objects.create(catedra=self.catedra, tipo='entrega', titulo='TP 1',
                              fecha=date(2026, 10, 15))
        clases = self.agenda(self.get(ver='clases'))
        fechas = self.agenda(self.get(ver='fechas'))
        self.assertNotIn(date(2026, 10, 15), clases)
        self.assertEqual(list(fechas), [date(2026, 10, 15)])

    def test_solo_muestra_sus_cursadas(self):
        Evento.objects.create(catedra=self.ajena, tipo='final', titulo='Final ajeno',
                              fecha=date(2026, 10, 15))
        Horario.objects.create(catedra=self.ajena, dia=Horario.Dia.MARTES,
                               hora_inicio=time(9), hora_fin=time(11))
        self.assertNotContains(self.get(), 'Química')

    def test_mes_invalido_usa_el_actual(self):
        respuesta = self.get(mes='cualquiera', ver='otro')
        self.assertEqual(respuesta.context['mes'], timezone.localdate().replace(day=1))
        self.assertEqual(respuesta.context['ver'], 'todo')

    def test_navegacion_entre_meses(self):
        respuesta = self.get(mes='2026-12')
        self.assertEqual(respuesta.context['anterior'], '2026-11')
        self.assertEqual(respuesta.context['siguiente'], '2027-01')

    def test_aparece_en_la_navegacion_del_alumno(self):
        respuesta = self.get()
        self.assertIn('Calendario', [i['etiqueta'] for i in respuesta.context['menu']])
        self.assertContains(respuesta, 'aria-current="page">Calendario')

    def test_rechaza_otros_roles(self):
        profe = Usuario.objects.create_user('2001', password='clave-segura-123')
        profe.groups.add(Group.objects.get(name='profesor'))
        self.client.force_login(profe)
        self.assertEqual(self.get().status_code, 403)
