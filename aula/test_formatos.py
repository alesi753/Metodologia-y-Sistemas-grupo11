from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from .formatos import registrar_progreso
from .models import Carrera, Catedra, Contenido, Materia, Unidad, Usuario

CUESTIONARIO = {
    'aprobacion': 0.5,
    'preguntas': [
        {'enunciado': 'A', 'opciones': ['x', 'y'], 'correcta': 0},
        {'enunciado': 'B', 'opciones': ['x', 'y'], 'correcta': 1},
    ],
}


class FormatosTests(TestCase):
    def setUp(self):
        materia = Materia.objects.create(nombre='Legislación', carrera=Carrera.objects.create(nombre='TUP'))
        catedra = Catedra.objects.create(materia=materia, anio=2026, cuatrimestre=2)
        self.unidad = Unidad.objects.create(catedra=catedra, orden=1, titulo='Intro')
        self.alumno = Usuario.objects.create_user('1001')
        self.alumno.groups.add(Group.objects.get(name='alumno'))

    def contenido(self, formato, cuerpo):
        return Contenido.objects.create(
            unidad=self.unidad, formato=formato, titulo='T', cuerpo=cuerpo, publicado=True,
        )

    def test_cuerpo_invalido_se_rechaza(self):
        for formato in ('texto', 'cuestionario', 'practica'):
            with self.assertRaises(ValidationError):
                self.contenido(formato, {}).clean()

    def test_cuerpos_validos_pasan(self):
        self.contenido('texto', {'secciones': [{'titulo': 'a', 'texto': 'b'}]}).clean()
        self.contenido('cuestionario', CUESTIONARIO).clean()
        self.contenido('practica', {'consigna': 'c', 'entregables': [], 'formatos_aceptados': 'pdf'}).clean()

    def test_texto_se_completa_al_leerlo(self):
        c = self.contenido('texto', {'secciones': [{'titulo': 'a', 'texto': 'b'}]})
        self.assertIsNotNone(registrar_progreso(self.alumno, c).completado_en)

    def test_cuestionario_aprueba_o_cuenta_intento(self):
        c = self.contenido('cuestionario', CUESTIONARIO)
        malo = registrar_progreso(self.alumno, c, {'respuestas': [1, 0]})
        self.assertIsNone(malo.completado_en)
        self.assertEqual(malo.intentos, 1)
        bueno = registrar_progreso(self.alumno, c, {'respuestas': [0, 1]})
        self.assertIsNotNone(bueno.completado_en)
        self.assertEqual(bueno.intentos, 2)

    def test_practica_se_completa_al_entregar(self):
        c = self.contenido('practica', {'consigna': 'c', 'entregables': [], 'formatos_aceptados': 'pdf'})
        self.assertIsNone(registrar_progreso(self.alumno, c).completado_en)
        entrega = SimpleUploadedFile('tp.pdf', b'contenido')
        self.assertIsNotNone(registrar_progreso(self.alumno, c, archivo=entrega).completado_en)

    def test_completado_no_se_reabre(self):
        c = self.contenido('texto', {'secciones': [{'titulo': 'a', 'texto': 'b'}]})
        primero = registrar_progreso(self.alumno, c).completado_en
        self.assertEqual(registrar_progreso(self.alumno, c).completado_en, primero)