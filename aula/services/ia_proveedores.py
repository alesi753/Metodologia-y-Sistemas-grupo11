"""Proveedores de IA (ver docs/decisiones-diseno.md, §1.2 y §3).

- Adapter: `ProveedorIA` es la interfaz que espera la fachada. Cada adaptador
  traduce un servicio externo a esa interfaz y convierte sus errores en `ErrorIA`.
- Factory: `crear_proveedor` elige el adaptador según `settings.IA_PROVEEDOR`,
  así cambiar de servicio es cambiar una variable de entorno.
"""
import base64
import io
import json
import os
from abc import ABC, abstractmethod

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


class ErrorIA(Exception):
    """Único error que ve el resto del sistema cuando la IA falla."""


class ProveedorIA(ABC):
    """Interfaz que la fachada espera de cualquier proveedor de IA."""

    #: Variable de entorno con la clave del servicio (None si no necesita).
    variable_clave = None

    @abstractmethod
    def completar(self, tarea, sistema, mensaje, esquema, documento_pdf=None) -> dict:
        """Devuelve la respuesta ya parseada como dict, con la forma de `esquema`.

        `tarea` identifica el pedido ('programa', 'contenido' o 'tutor'). Cada
        proveedor lo usa para elegir modelo o esfuerzo; el falso, la respuesta.
        """

    def _clave(self):
        clave = os.environ.get(self.variable_clave)
        if not clave:
            raise ErrorIA(f'Falta la variable de entorno {self.variable_clave}.')
        return clave


def parsear_json(texto):
    """Lee el JSON de la respuesta, tolerando que venga entre ```json ... ```."""
    texto = (texto or '').strip()
    if texto.startswith('```'):
        texto = texto.strip('`').removeprefix('json').strip()
    try:
        return json.loads(texto)
    except json.JSONDecodeError as error:
        raise ErrorIA('La IA devolvió un JSON inválido.') from error


def texto_del_pdf(pdf):
    """Extrae el texto de un PDF, para modelos que no leen PDFs directamente."""
    from pypdf import PdfReader
    from pypdf.errors import PdfReadError

    try:
        paginas = PdfReader(io.BytesIO(pdf)).pages
        texto = '\n'.join(pagina.extract_text() or '' for pagina in paginas).strip()
    except PdfReadError as error:
        raise ErrorIA('No se pudo leer el PDF.') from error
    if not texto:
        raise ErrorIA('El PDF no tiene texto para leer (¿es una imagen escaneada?).')
    return texto


class AnthropicAdapter(ProveedorIA):
    """Claude por la API de Anthropic. Lee el PDF entero, tablas incluidas."""

    variable_clave = 'ANTHROPIC_API_KEY'

    def __init__(self, modelo=None, esfuerzos=None, cliente=None):
        self.modelo = modelo or settings.IA_ANTHROPIC_MODELO
        self.esfuerzos = esfuerzos or settings.IA_ANTHROPIC_ESFUERZO
        self._cliente = cliente

    def _obtener_cliente(self):
        import anthropic

        if self._cliente is None:
            self._cliente = anthropic.Anthropic(api_key=self._clave())
        return self._cliente

    def completar(self, tarea, sistema, mensaje, esquema, documento_pdf=None):
        import anthropic

        contenido = []
        if documento_pdf:
            contenido.append({
                'type': 'document',
                'source': {
                    'type': 'base64',
                    'media_type': 'application/pdf',
                    'data': base64.standard_b64encode(documento_pdf).decode(),
                },
            })
        contenido.append({'type': 'text', 'text': mensaje})

        try:
            respuesta = self._obtener_cliente().messages.create(
                model=self.modelo,
                max_tokens=16000,
                system=sistema,
                messages=[{'role': 'user', 'content': contenido}],
                output_config={
                    'effort': self.esfuerzos.get(tarea, 'medium'),
                    # Salida estructurada: la API garantiza JSON con esta forma.
                    'format': {'type': 'json_schema', 'schema': esquema},
                },
            )
        except anthropic.AnthropicError as error:
            raise ErrorIA(f'No se pudo consultar a la IA: {error}') from error

        if respuesta.stop_reason == 'refusal':
            raise ErrorIA('La IA rechazó el pedido.')
        if respuesta.stop_reason == 'max_tokens':
            raise ErrorIA('La respuesta de la IA quedó incompleta.')
        return parsear_json(next((b.text for b in respuesta.content if b.type == 'text'), ''))


class OpenRouterAdapter(ProveedorIA):
    """Modelos de varios proveedores (incluidos gratuitos) por la API de OpenRouter.

    OpenRouter es compatible con la API de OpenAI, así que usa ese SDK. Como no
    todos los modelos leen PDFs, el programa se manda como texto extraído.
    """

    variable_clave = 'OPENROUTER_API_KEY'
    URL = 'https://openrouter.ai/api/v1'

    def __init__(self, modelos=None, cliente=None):
        self.modelos = modelos or settings.IA_OPENROUTER_MODELOS
        self._cliente = cliente

    def _obtener_cliente(self):
        import openai

        if self._cliente is None:
            self._cliente = openai.OpenAI(base_url=self.URL, api_key=self._clave())
        return self._cliente

    def completar(self, tarea, sistema, mensaje, esquema, documento_pdf=None):
        import openai

        if documento_pdf:
            mensaje = f'{mensaje}\n\nTexto del documento:\n{texto_del_pdf(documento_pdf)}'

        try:
            respuesta = self._obtener_cliente().chat.completions.create(
                model=self.modelos[tarea],
                max_tokens=8000,
                messages=[
                    {'role': 'system', 'content': sistema},
                    {'role': 'user', 'content': mensaje},
                ],
                response_format={
                    'type': 'json_schema',
                    'json_schema': {'name': tarea, 'strict': True, 'schema': esquema},
                },
                # Solo proveedores que respeten la salida estructurada.
                extra_body={'provider': {'require_parameters': True}},
            )
        except openai.OpenAIError as error:
            raise ErrorIA(f'No se pudo consultar a la IA: {error}') from error

        if not respuesta.choices:
            raise ErrorIA('La IA no devolvió respuesta.')
        eleccion = respuesta.choices[0]
        if eleccion.finish_reason == 'length':
            raise ErrorIA('La respuesta de la IA quedó incompleta.')
        return parsear_json(eleccion.message.content)


class ProveedorFalso(ProveedorIA):
    """Responde siempre lo mismo, sin red. Guarda los pedidos para inspeccionarlos."""

    RESPUESTAS = {
        'programa': {
            'unidades': [
                {'titulo': 'Introducción a la materia', 'conceptos': ['Objetivos', 'Conceptos básicos']},
                {'titulo': 'Desarrollo del tema central', 'conceptos': ['Modelos', 'Casos de estudio']},
            ],
        },
        'contenido': {
            'formato': 'cuestionario',
            'titulo': 'Repaso de la unidad',
            'cuerpo': {
                'aprobacion': 0.7,
                'preguntas': [{
                    'enunciado': '¿Qué concepto se trabajó en la unidad?',
                    'opciones': ['El primero', 'Ninguno'],
                    'correcta': 0,
                }],
            },
        },
        'tutor': {
            'texto': 'Es un tema general de la unidad. Te conviene repasar el material indicado.',
            'referencias': [],
        },
    }

    def __init__(self, respuestas=None):
        self.respuestas = {**self.RESPUESTAS, **(respuestas or {})}
        self.llamadas = []

    def completar(self, tarea, sistema, mensaje, esquema, documento_pdf=None):
        self.llamadas.append({'tarea': tarea, 'mensaje': mensaje, 'documento_pdf': documento_pdf})
        return self.respuestas[tarea]


PROVEEDORES = {
    'openrouter': OpenRouterAdapter,
    'anthropic': AnthropicAdapter,
    'falso': ProveedorFalso,
}


def crear_proveedor(nombre=None):
    """Instancia el proveedor configurado en `settings.IA_PROVEEDOR` (o el pedido)."""
    nombre = nombre or settings.IA_PROVEEDOR
    clase = PROVEEDORES.get(nombre)
    if clase is None:
        opciones = ', '.join(PROVEEDORES)
        raise ImproperlyConfigured(f'IA_PROVEEDOR={nombre!r} no existe. Opciones: {opciones}.')
    return clase()
