import shutil
import tempfile
from datetime import timedelta

from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .models import Carrera, Catedra, Contenido, Materia, Progreso, Unidad, Usuario

TEXTO = {'secciones': [{'titulo': 'Introducción', 'texto': 'Primer párrafo'}]}
CUESTIONARIO = {
    'aprobacion': 0.5,
    'preguntas': [
        {'enunciado': '¿Dos más dos?', 'opciones': ['3', '4'], 'correcta': 1},
        {'enunciado': '¿Capital de Francia?', 'opciones': ['París', 'Roma'], 'correcta': 0},
    ],
}
PRACTICA = {'consigna': 'Armar el informe', 'entregables': ['Informe'], 'formatos_aceptados': '.pdf, .zip'}

MEDIA = tempfile.mkdtemp()


@override_settings(MEDIA_ROOT=MEDIA)
class ContenidoTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA, ignore_errors=True)

    def setUp(self):
        self.alumno = Usuario.objects.create_user('1001', password='clave-segura-123')
        self.alumno.groups.add(Group.objects.get(name='alumno'))
        materia = Materia.objects.create(nombre='Legislación', carrera=Carrera.objects.create(nombre='TUP'))
        self.catedra = Catedra.objects.create(materia=materia, anio=2026, cuatrimestre=2)
        self.catedra.alumnos.add(self.alumno)
        self.u1 = Unidad.objects.create(catedra=self.catedra, orden=1, titulo='Constitucional')
        self.u2 = Unidad.objects.create(catedra=self.catedra, orden=2, titulo='Civil')
        self.texto = self.crear(self.u1, 'texto', 'Lectura', TEXTO)
        self.cuestionario = self.crear(self.u1, 'cuestionario', 'Autoevaluación', CUESTIONARIO)
        self.practica = self.crear(self.u1, 'practica', 'TP 1', PRACTICA)
        self.de_u2 = self.crear(self.u2, 'texto', 'Contratos', TEXTO)
        self.client.force_login(self.alumno)

    def crear(self, unidad, formato, titulo, cuerpo, publicado=True):
        return Contenido.objects.create(
            unidad=unidad, formato=formato, titulo=titulo, cuerpo=cuerpo, publicado=publicado,
        )

    def url(self, contenido):
        return reverse('contenido', args=[contenido.id])

    def progreso(self, contenido):
        return Progreso.objects.filter(alumno=self.alumno, contenido=contenido).first()

    # Cada formato se muestra con el template de su estrategia.

    def test_cada_formato_usa_su_template(self):
        for contenido, template in [
            (self.texto, 'aula/contenido/texto.html'),
            (self.cuestionario, 'aula/contenido/cuestionario.html'),
            (self.practica, 'aula/contenido/practica.html'),
        ]:
            self.assertTemplateUsed(self.client.get(self.url(contenido)), template)

    # Texto

    def test_marcar_texto_como_leido_lo_completa(self):
        respuesta = self.client.post(self.url(self.texto), follow=True)
        self.assertIsNotNone(self.progreso(self.texto).completado_en)
        self.assertContains(respuesta, 'Completaste este contenido')
        self.assertNotContains(respuesta, 'Marcar como leído')

    # Cuestionario

    def test_cuestionario_aprobado(self):
        respuesta = self.client.post(self.url(self.cuestionario), {'pregunta-0': 1, 'pregunta-1': 1}, follow=True)
        progreso = self.progreso(self.cuestionario)
        self.assertIsNotNone(progreso.completado_en)
        self.assertEqual(progreso.respuesta, {'respuestas': [1, 1]})
        self.assertContains(respuesta, 'Aprobaste con 1 de 2')

    def test_cuestionario_no_aprobado_permite_reintentar(self):
        respuesta = self.client.post(self.url(self.cuestionario), {'pregunta-0': 0}, follow=True)
        progreso = self.progreso(self.cuestionario)
        self.assertIsNone(progreso.completado_en)
        self.assertEqual(progreso.intentos, 1)
        self.assertContains(respuesta, 'No alcanzaste el mínimo')
        self.assertContains(respuesta, 'Acertaste 0 de 2')
        self.assertContains(respuesta, 'Enviar respuestas')

        self.client.post(self.url(self.cuestionario), {'pregunta-0': 1, 'pregunta-1': 0})
        progreso.refresh_from_db()
        self.assertEqual(progreso.intentos, 2)
        self.assertIsNotNone(progreso.completado_en)

    # Práctica

    def test_entregar_practica_guarda_el_archivo(self):
        archivo = SimpleUploadedFile('informe.pdf', b'%PDF-1.4', content_type='application/pdf')
        respuesta = self.client.post(self.url(self.practica), {'archivo': archivo}, follow=True)
        progreso = self.progreso(self.practica)
        self.assertIsNotNone(progreso.completado_en)
        self.assertTrue(progreso.archivo.name.startswith('practicas/informe'))
        self.assertContains(respuesta, 'Entregaste')

    def test_practica_rechaza_formatos_no_aceptados_y_sin_archivo(self):
        archivo = SimpleUploadedFile('informe.exe', b'MZ')
        respuesta = self.client.post(self.url(self.practica), {'archivo': archivo}, follow=True)
        self.assertContains(respuesta, 'El archivo tiene que ser .pdf, .zip')
        respuesta = self.client.post(self.url(self.practica), follow=True)
        self.assertContains(respuesta, 'Elegí un archivo para entregar.')
        self.assertIsNone(self.progreso(self.practica))

    # Flujo de la unidad

    def test_completar_la_unidad_desbloquea_la_siguiente(self):
        self.assertTemplateUsed(self.client.get(self.url(self.de_u2)), 'aula/contenido/bloqueado.html')
        self.client.post(self.url(self.texto))
        self.client.post(self.url(self.cuestionario), {'pregunta-0': 1, 'pregunta-1': 0})
        archivo = SimpleUploadedFile('informe.zip', b'PK')
        respuesta = self.client.post(self.url(self.practica), {'archivo': archivo}, follow=True)
        self.assertContains(respuesta, 'Se desbloqueó la Unidad 2: Civil')
        self.assertTemplateUsed(self.client.get(self.url(self.de_u2)), 'aula/contenido/texto.html')

    def test_unidad_bloqueada_indica_que_falta(self):
        respuesta = self.client.post(self.url(self.de_u2), follow=True)
        self.assertContains(respuesta, 'Primero completá la Unidad 1: Constitucional')
        self.assertIsNone(self.progreso(self.de_u2))

    def test_entrega_fuera_de_termino(self):
        self.u1.fecha_limite = timezone.localdate() - timedelta(days=1)
        self.u1.save()
        respuesta = self.client.post(self.url(self.texto), follow=True)
        self.assertContains(respuesta, 'fuera de término')

    def test_contenido_completado_no_se_reabre(self):
        self.client.post(self.url(self.texto))
        respuesta = self.client.post(self.url(self.texto), follow=True)
        self.assertContains(respuesta, 'ya estaba completado')

    # Acceso

    def test_borrador_o_ajeno_da_404(self):
        borrador = self.crear(self.u1, 'texto', 'Borrador', TEXTO, publicado=False)
        self.assertEqual(self.client.get(self.url(borrador)).status_code, 404)
        otro = Usuario.objects.create_user('1002', password='clave-segura-123')
        otro.groups.add(Group.objects.get(name='alumno'))
        self.client.force_login(otro)
        self.assertEqual(self.client.get(self.url(self.texto)).status_code, 404)

    def test_rechaza_otros_roles(self):
        profe = Usuario.objects.create_user('2001', password='clave-segura-123')
        profe.groups.add(Group.objects.get(name='profesor'))
        self.client.force_login(profe)
        self.assertEqual(self.client.get(self.url(self.texto)).status_code, 403)
