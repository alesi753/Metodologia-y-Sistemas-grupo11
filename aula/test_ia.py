# Tests de la fachada de IA. Usan ProveedorFalso o un cliente simulado: no hay red.
import json
import os
from types import SimpleNamespace
from unittest.mock import Mock, patch

import anthropic
import httpx2 as httpx
import openai
from django.core.exceptions import ImproperlyConfigured
from django.test import TestCase, override_settings

from .models import Carrera, Catedra, Contenido, Materia, Unidad, Usuario
from .management.commands.demo_ia import pdf_de_ejemplo
from .services.ia_facade import AsistenteIA, BorradorContenido, ErrorIA, Referencia
from .services.ia_proveedores import (
    AnthropicAdapter, OpenRouterAdapter, ProveedorFalso, crear_proveedor, texto_del_pdf,
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
        self.assertEqual(argumentos['output_config']['effort'], 'medium')

    def test_tutor_usa_esfuerzo_bajo(self):
        cliente = Mock()
        cliente.messages.create.return_value = SimpleNamespace(
            stop_reason='end_turn', content=[SimpleNamespace(type='text', text='{}')],
        )
        AnthropicAdapter(cliente=cliente).completar('tutor', 'sistema', 'hola', {})
        argumentos = cliente.messages.create.call_args.kwargs
        self.assertEqual(argumentos['output_config']['effort'], 'low')
        self.assertEqual(argumentos['model'], 'claude-sonnet-5-5')


def respuesta_openrouter(contenido, finish_reason='stop'):
    return SimpleNamespace(choices=[SimpleNamespace(
        finish_reason=finish_reason, message=SimpleNamespace(content=contenido),
    )])


class OpenRouterAdapterTests(TestCase):
    MODELOS = {'programa': 'modelo-a', 'contenido': 'modelo-a', 'tutor': 'modelo-b'}

    def adaptador(self, respuesta):
        cliente = Mock()
        cliente.chat.completions.create.return_value = respuesta
        return OpenRouterAdapter(modelos=self.MODELOS, cliente=cliente), cliente

    def test_pide_json_con_esquema_y_modelo_por_tarea(self):
        adaptador, cliente = self.adaptador(respuesta_openrouter('{"ok": true}'))
        self.assertEqual(adaptador.completar('tutor', 'sistema', 'hola', {'type': 'object'}), {'ok': True})
        argumentos = cliente.chat.completions.create.call_args.kwargs
        self.assertEqual(argumentos['model'], 'modelo-b')
        self.assertEqual(argumentos['response_format']['type'], 'json_schema')
        self.assertTrue(argumentos['extra_body']['provider']['require_parameters'])

    def test_pdf_se_manda_como_texto(self):
        adaptador, cliente = self.adaptador(respuesta_openrouter('{}'))
        adaptador.completar('programa', 'sistema', 'Extraé', {}, documento_pdf=pdf_de_ejemplo())
        mensaje = cliente.chat.completions.create.call_args.kwargs['messages'][1]['content']
        self.assertIn('Derecho constitucional', mensaje)

    def test_json_entre_backticks(self):
        adaptador, _ = self.adaptador(respuesta_openrouter('```json\n{"ok": 1}\n```'))
        self.assertEqual(adaptador.completar('tutor', 's', 'm', {}), {'ok': 1})

    def test_respuesta_cortada_es_error(self):
        adaptador, _ = self.adaptador(respuesta_openrouter('{"ok"', finish_reason='length'))
        with self.assertRaises(ErrorIA):
            adaptador.completar('tutor', 's', 'm', {})

    def test_error_del_sdk_se_traduce(self):
        cliente = Mock()
        cliente.chat.completions.create.side_effect = openai.OpenAIError('sin servicio')
        with self.assertRaises(ErrorIA):
            OpenRouterAdapter(modelos=self.MODELOS, cliente=cliente).completar('tutor', 's', 'm', {})

    @patch.dict(os.environ, {}, clear=True)
    def test_sin_clave_es_error(self):
        with self.assertRaises(ErrorIA):
            OpenRouterAdapter().completar('tutor', 's', 'm', {})

    def test_pdf_sin_texto_es_error(self):
        with self.assertRaises(ErrorIA):
            texto_del_pdf(b'esto no es un pdf')


class CrearProveedorTests(TestCase):
    @override_settings(IA_PROVEEDOR='openrouter')
    def test_usa_el_de_la_configuracion(self):
        self.assertIsInstance(crear_proveedor(), OpenRouterAdapter)
        self.assertIsInstance(AsistenteIA().proveedor, OpenRouterAdapter)

    def test_por_nombre(self):
        self.assertIsInstance(crear_proveedor('anthropic'), AnthropicAdapter)
        self.assertIsInstance(crear_proveedor('falso'), ProveedorFalso)

    def test_nombre_desconocido(self):
        with self.assertRaises(ImproperlyConfigured):
            crear_proveedor('otro')

