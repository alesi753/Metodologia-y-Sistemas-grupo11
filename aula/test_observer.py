from django.contrib.auth.models import Group
from django.test import TestCase
from django.utils import timezone

from .formatos import registrar_progreso
from .models import Aviso, Carrera, Catedra, Contenido, Materia, Progreso, Unidad, Usuario
from .signals import aviso_publicado, unidad_completada


class ObserverSignalsTests(TestCase):
    def setUp(self):
        self.alumno = Usuario.objects.create_user('2001', password='clave-segura-123')
        self.alumno.groups.add(Group.objects.get(name='alumno'))
        self.profesor = Usuario.objects.create_user('3001', password='clave-segura-123')
        self.profesor.groups.add(Group.objects.get(name='profesor'))

        carrera = Carrera.objects.create(nombre='TUP')
        materia = Materia.objects.create(nombre='Metodología II', carrera=carrera)
        self.catedra = Catedra.objects.create(materia=materia, anio=2026, cuatrimestre=2)
        self.catedra.alumnos.add(self.alumno)

        self.u1 = Unidad.objects.create(catedra=self.catedra, orden=1, titulo='Unidad 1')
        self.u2 = Unidad.objects.create(catedra=self.catedra, orden=2, titulo='Unidad 2')
        self.c1 = Contenido.objects.create(
            unidad=self.u1, formato='texto', titulo='Teoría 1', publicado=True,
            cuerpo={'secciones': [{'titulo': 'Intro', 'texto': 'Contenido'}]},
        )

    def test_progreso_incompleto_no_dispara_unidad_completada(self):
        eventos = []
        receptor = lambda **kw: eventos.append(kw)
        unidad_completada.connect(receptor)
        try:
            with self.captureOnCommitCallbacks(execute=True):
                Progreso.objects.create(alumno=self.alumno, contenido=self.c1, completado_en=None)
            self.assertEqual(eventos, [])
        finally:
            unidad_completada.disconnect(receptor)

    def test_completar_unidad_via_registrar_progreso_dispara_signal_con_siguiente(self):
        eventos = []
        receptor = lambda **kw: eventos.append(kw)
        unidad_completada.connect(receptor)
        try:
            with self.captureOnCommitCallbacks(execute=True):
                registrar_progreso(self.alumno, self.c1)
            self.assertEqual(len(eventos), 1)
            self.assertEqual(eventos[0]['alumno'], self.alumno)
            self.assertEqual(eventos[0]['unidad'], self.u1)
            self.assertEqual(eventos[0]['siguiente_unidad'], self.u2)
        finally:
            unidad_completada.disconnect(receptor)

    def test_aviso_creado_dispara_signal_pero_edicion_no(self):
        eventos = []
        receptor = lambda **kw: eventos.append(kw)
        aviso_publicado.connect(receptor)
        try:
            with self.captureOnCommitCallbacks(execute=True):
                aviso = Aviso.objects.create(
                    catedra=self.catedra, autor=self.profesor, titulo='Parcial', cuerpo='Fecha confirmada',
                )
            self.assertEqual(len(eventos), 1)
            self.assertEqual(eventos[0]['catedra'], self.catedra)
            self.assertEqual(eventos[0]['destinatarios'], [self.alumno])

            with self.captureOnCommitCallbacks(execute=True):
                aviso.titulo = 'Parcial actualizado'
                aviso.save()
            self.assertEqual(len(eventos), 1)
        finally:
            aviso_publicado.disconnect(receptor)
