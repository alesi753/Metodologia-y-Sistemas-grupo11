# Tests de la fachada de IA. Usan ProveedorFalso o un cliente simulado: no hay red.
import json
import os
from types import SimpleNamespace
from unittest.mock import Mock, patch

import anthropic
import httpx2 as httpx
from django.test import TestCase

from .models import Carrera, Catedra, Contenido, Materia, Unidad, Usuario
from .services.ia_facade import (
    AnthropicAdapter, AsistenteIA, BorradorContenido, ErrorIA, ProveedorFalso, Referencia,
)


class AsistenteIATests(TestCase):
    def setUp(self):
        self.alumno = Usuario.objects.create_user('1001')
        materia = Materia.objects.create(nombre='Legislación', carrera=Carrera.objects.create(nombre='TUP'))
        self.catedra = Catedra.objects.create(materia=materia, anio=2026, cuatrimestre=2)
        self.catedra.alumnos.add(self.alumno)
        self.unidad = Unidad.objects.create(catedra=self.catedra, orden=1, titulo='Constitucional')
        self.publicado = Contenido.objects.create(
            unidad=self.unidad, formato='texto', titulo='Supremacía', publicado=True,
            cuerpo={'secciones': [{'titulo': 'Pirámide', 'texto': '...'}]},
        )
        self.borrador = Contenido.objects.create(unidad=self.unidad, formato='texto', titulo='Borrador')
        otra = Catedra.objects.create(materia=materia, anio=2025, cuatrimestre=1)
        otra_unidad = Unidad.objects.create(catedra=otra, orden=1, titulo='Otra')
        self.ajeno = Contenido.objects.create(
            unidad=otra_unidad, formato='texto', titulo='Ajeno', publicado=True,
        )

    def asistente(self, **respuestas):
        self.proveedor = ProveedorFalso(respuestas)
        return AsistenteIA(self.proveedor)

    def test_importar_programa(self):
        programa = self.asistente().importar_programa(b'%PDF-1.4')
        self.assertEqual(len(programa.unidades), 2)
        self.assertEqual(programa.unidades[0].titulo, 'Introducción a la materia')
        self.assertEqual(self.proveedor.llamadas[0]['documento_pdf'], b'%PDF-1.4')

    def test_programa_sin_unidades_es_error(self):
        with self.assertRaises(ErrorIA):
            self.asistente(programa={'unidades': []}).importar_programa(b'%PDF-1.4')

    def test_generar_contenido(self):
        texto = {'formato': 'texto', 'titulo': 'Intro', 'cuerpo': {'secciones': [{'titulo': 'A', 'texto': 'B'}]}}
        borrador = self.asistente(contenido=texto).generar_contenido(self.unidad, ['Supremacía'], 'práctica')
        self.assertEqual(borrador, BorradorContenido('texto', 'Intro', texto['cuerpo']))
        self.assertFalse(Contenido.objects.filter(titulo='Intro').exists())

    def test_generar_cuestionario_por_defecto(self):
        borrador = self.asistente().generar_contenido(self.unidad, ['Supremacía'], 'teórica')
        self.assertEqual(borrador.formato, Contenido.Formato.CUESTIONARIO)

    def test_formato_desconocido_es_error(self):
        flashcard = {'formato': 'flashcard', 'titulo': 'X', 'cuerpo': {}}
        with self.assertRaises(ErrorIA):
            self.asistente(contenido=flashcard).generar_contenido(self.unidad, [], '')

    def test_cuerpo_que_no_corresponde_al_formato_es_error(self):
        mal = {'formato': 'cuestionario', 'titulo': 'X', 'cuerpo': {'secciones': []}}
        with self.assertRaises(ErrorIA):
            self.asistente(contenido=mal).generar_contenido(self.unidad, [], '')

    def test_correcta_fuera_de_rango_es_error(self):
        mal = {'formato': 'cuestionario', 'titulo': 'X', 'cuerpo': {
            'aprobacion': 0.7, 'preguntas': [{'enunciado': '?', 'opciones': ['a', 'b'], 'correcta': 2}],
        }}
        with self.assertRaises(ErrorIA):
            self.asistente(contenido=mal).generar_contenido(self.unidad, [], '')

    def test_tutor_solo_manda_material_publicado_del_alumno(self):
        self.asistente().consultar_tutor(self.alumno, '¿Qué es la supremacía?', {'pantalla': 'curso'})
        material = json.loads(self.proveedor.llamadas[0]['mensaje'])['material']
        self.assertEqual([m['id'] for m in material], [self.publicado.id])

    def test_tutor_descarta_referencias_no_permitidas(self):
        respuesta = self.asistente(tutor={'texto': 'Explicación', 'referencias': [
            {'contenido_id': self.publicado.id, 'titulo': 'otro título'},
            {'contenido_id': self.borrador.id, 'titulo': 'Borrador'},
            {'contenido_id': self.ajeno.id, 'titulo': 'Ajeno'},
            {'contenido_id': 9999, 'titulo': 'Inventado'},
        ]}).consultar_tutor(self.alumno, '¿Qué es la supremacía?', {})
        self.assertEqual(respuesta.texto, 'Explicación')
        self.assertEqual(respuesta.referencias, [Referencia(self.publicado.id, 'Supremacía')])

    def test_tutor_sin_texto_es_error(self):
        with self.assertRaises(ErrorIA):
            self.asistente(tutor={'referencias': []}).consultar_tutor(self.alumno, '?', {})


class AnthropicAdapterTests(TestCase):
    def test_error_del_sdk_se_traduce(self):
        cliente = Mock()
        pedido = httpx.Request('POST', 'https://api.anthropic.com/v1/messages')
        cliente.messages.create.side_effect = anthropic.APIConnectionError(request=pedido)
        with self.assertRaises(ErrorIA):
            AnthropicAdapter(cliente=cliente).completar('tutor', 'sistema', 'hola', {})

    @patch.dict(os.environ, {}, clear=True)
    def test_sin_clave_es_error(self):
        with self.assertRaises(ErrorIA):
            AnthropicAdapter().completar('tutor', 'sistema', 'hola', {})

    def test_json_invalido_se_traduce(self):
        cliente = Mock()
        cliente.messages.create.return_value = SimpleNamespace(
            stop_reason='end_turn', content=[SimpleNamespace(type='text', text='no es json')],
        )
        with self.assertRaises(ErrorIA):
            AnthropicAdapter(cliente=cliente).completar('tutor', 'sistema', 'hola', {})

    def test_respuesta_valida_y_pdf(self):
        cliente = Mock()
        cliente.messages.create.return_value = SimpleNamespace(
            stop_reason='end_turn', content=[SimpleNamespace(type='text', text='{"ok": true}')],
        )
        datos = AnthropicAdapter(modelo='modelo-x', cliente=cliente).completar(
            'programa', 'sistema', 'hola', {}, documento_pdf=b'%PDF',
        )
        self.assertEqual(datos, {'ok': True})
        argumentos = cliente.messages.create.call_args.kwargs
        self.assertEqual(argumentos['model'], 'modelo-x')
        self.assertEqual(argumentos['messages'][0]['content'][0]['type'], 'document')
