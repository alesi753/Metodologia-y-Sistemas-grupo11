"""Fachada de la IA del aula (ver docs/decisiones-diseno.md, §1.1).

`AsistenteIA` expone un método por cada necesidad del producto y las vistas
solo hablan con él. Delega el pedido en un `ProveedorIA` (ver
`ia_proveedores.py`), así que no sabe qué servicio de IA hay detrás.

Nada de lo que devuelve este módulo es un tipo de un SDK: el resto del sistema
solo ve las dataclasses de abajo y `ErrorIA`.
"""
import json
from dataclasses import dataclass, field

from aula.models import Contenido

from .ia_proveedores import ErrorIA, crear_proveedor

__all__ = [
    'AsistenteIA', 'BorradorContenido', 'ErrorIA', 'ProgramaImportado', 'Referencia',
    'RespuestaTutor', 'UnidadPropuesta',
]

# --- Tipos del dominio -------------------------------------------------------

@dataclass
class UnidadPropuesta:
    titulo: str
    conceptos: list[str] = field(default_factory=list)


@dataclass
class ProgramaImportado:
    unidades: list[UnidadPropuesta]


@dataclass
class BorradorContenido:
    """Contenido sugerido por la IA. No se guarda: lo revisa el profesor."""
    formato: str
    titulo: str
    cuerpo: dict


@dataclass
class Referencia:
    contenido_id: int
    titulo: str


@dataclass
class RespuestaTutor:
    texto: str
    referencias: list[Referencia] = field(default_factory=list)


# --- Esquemas de respuesta ---------------------------------------------------

def _objeto(**propiedades):
    return {
        'type': 'object',
        'properties': propiedades,
        'required': list(propiedades),
        'additionalProperties': False,
    }


TEXTO = {'type': 'string'}
LISTA_TEXTOS = {'type': 'array', 'items': TEXTO}

ESQUEMA_PROGRAMA = _objeto(
    unidades={'type': 'array', 'items': _objeto(titulo=TEXTO, conceptos=LISTA_TEXTOS)},
)

ESQUEMA_CONTENIDO = _objeto(
    formato={'type': 'string', 'enum': Contenido.Formato.values},
    titulo=TEXTO,
    cuerpo={'anyOf': [
        _objeto(secciones={'type': 'array', 'items': _objeto(titulo=TEXTO, texto=TEXTO)}),
        _objeto(
            aprobacion={'type': 'number'},
            preguntas={'type': 'array', 'items': _objeto(
                enunciado=TEXTO, opciones=LISTA_TEXTOS, correcta={'type': 'integer'},
            )},
        ),
        _objeto(consigna=TEXTO, entregables=LISTA_TEXTOS, formatos_aceptados=TEXTO),
    ]},
)

ESQUEMA_TUTOR = _objeto(
    texto=TEXTO,
    referencias={'type': 'array', 'items': _objeto(contenido_id={'type': 'integer'}, titulo=TEXTO)},
)


# --- Validación de lo que devuelve la IA -------------------------------------

def _exigir(condicion, mensaje):
    if not condicion:
        raise ErrorIA(f'Respuesta de la IA mal formada: {mensaje}.')


def _es_lista_de_textos(valor):
    return isinstance(valor, list) and all(isinstance(v, str) for v in valor)


def _validar_cuerpo(formato, cuerpo):
    _exigir(isinstance(cuerpo, dict), 'el cuerpo no es un objeto')
    if formato == Contenido.Formato.TEXTO:
        secciones = cuerpo.get('secciones')
        _exigir(isinstance(secciones, list) and secciones, 'el texto no tiene secciones')
        for seccion in secciones:
            _exigir(isinstance(seccion, dict) and {'titulo', 'texto'} <= seccion.keys(),
                    'sección sin título o texto')
    elif formato == Contenido.Formato.CUESTIONARIO:
        _exigir(isinstance(cuerpo.get('aprobacion'), (int, float))
                and 0 < cuerpo['aprobacion'] <= 1, 'aprobación fuera de rango')
        preguntas = cuerpo.get('preguntas')
        _exigir(isinstance(preguntas, list) and preguntas, 'el cuestionario no tiene preguntas')
        for pregunta in preguntas:
            _exigir(isinstance(pregunta, dict) and isinstance(pregunta.get('enunciado'), str),
                    'pregunta sin enunciado')
            opciones = pregunta.get('opciones')
            _exigir(_es_lista_de_textos(opciones) and len(opciones) >= 2, 'pregunta con menos de dos opciones')
            correcta = pregunta.get('correcta')
            _exigir(isinstance(correcta, int) and 0 <= correcta < len(opciones), 'respuesta correcta inválida')
    else:
        _exigir(isinstance(cuerpo.get('consigna'), str), 'la práctica no tiene consigna')
        _exigir(_es_lista_de_textos(cuerpo.get('entregables')), 'entregables inválidos')
        _exigir(isinstance(cuerpo.get('formatos_aceptados'), str), 'formatos aceptados inválidos')


# --- Facade ------------------------------------------------------------------

SISTEMA_PROGRAMA = (
    'Sos asistente de una cátedra universitaria argentina. Leé el programa de la '
    'materia adjunto y devolvé sus unidades en orden, cada una con su título y los '
    'conceptos principales que trata. Respetá los nombres del programa.'
)

SISTEMA_CONTENIDO = (
    'Sos asistente de una cátedra universitaria argentina y preparás material para '
    'los alumnos. Elegí el formato más adecuado para los conceptos pedidos: "texto" '
    'para explicar teoría (cuerpo con secciones), "cuestionario" para repasar '
    '(aprobación entre 0 y 1 y preguntas de opción múltiple con el índice de la '
    'correcta) o "practica" para aplicar lo aprendido (consigna, entregables y '
    'formatos aceptados). Escribí en español rioplatense, claro y sin relleno.'
)

SISTEMA_TUTOR = (
    'Sos el tutor de un aula virtual universitaria. Explicá el tema de la pregunta '
    'en términos generales, en pocos párrafos, y citá en "referencias" los '
    'contenidos del material donde se estudia, usando solo ids del material dado. '
    'Nunca resuelvas cuestionarios ni prácticas ni des sus respuestas: si te lo '
    'piden, explicá el concepto y mandá al material. Si el tema está en una unidad '
    'que el alumno todavía no desbloqueó, aclaralo.'
)


class AsistenteIA:
    """Fachada de la IA. No guarda nada: devuelve borradores y las vistas persisten."""

    def __init__(self, proveedor=None):
        self.proveedor = proveedor or crear_proveedor()

    def importar_programa(self, pdf: bytes) -> ProgramaImportado:
        datos = self.proveedor.completar(
            'programa', SISTEMA_PROGRAMA, 'Extraé las unidades de este programa.',
            ESQUEMA_PROGRAMA, documento_pdf=pdf,
        )
        unidades = datos.get('unidades') if isinstance(datos, dict) else None
        _exigir(isinstance(unidades, list) and unidades, 'el programa no tiene unidades')
        propuestas = []
        for unidad in unidades:
            _exigir(isinstance(unidad, dict) and isinstance(unidad.get('titulo'), str),
                    'unidad sin título')
            _exigir(_es_lista_de_textos(unidad.get('conceptos')), 'conceptos inválidos')
            propuestas.append(UnidadPropuesta(unidad['titulo'], unidad['conceptos']))
        return ProgramaImportado(propuestas)

    def generar_contenido(self, unidad, conceptos, perspectiva) -> BorradorContenido:
        mensaje = json.dumps({
            'materia': unidad.catedra.materia.nombre,
            'unidad': unidad.titulo,
            'conceptos': conceptos,
            'perspectiva': perspectiva,
        }, ensure_ascii=False)
        datos = self.proveedor.completar('contenido', SISTEMA_CONTENIDO, mensaje, ESQUEMA_CONTENIDO)
        _exigir(isinstance(datos, dict), 'no es un objeto')
        formato = datos.get('formato')
        _exigir(formato in Contenido.Formato.values, f'formato desconocido {formato!r}')
        _exigir(isinstance(datos.get('titulo'), str), 'falta el título')
        _validar_cuerpo(formato, datos.get('cuerpo'))
        return BorradorContenido(formato, datos['titulo'], datos['cuerpo'])

    def consultar_tutor(self, alumno, pregunta, contexto: dict) -> RespuestaTutor:
        permitidos = self._material_del_alumno(alumno)
        mensaje = json.dumps({
            'pregunta': pregunta,
            'pantalla': contexto,
            'material': list(permitidos.values()),
        }, ensure_ascii=False, default=str)
        datos = self.proveedor.completar('tutor', SISTEMA_TUTOR, mensaje, ESQUEMA_TUTOR)
        _exigir(isinstance(datos, dict) and isinstance(datos.get('texto'), str), 'falta el texto')
        referencias = datos.get('referencias', [])
        _exigir(isinstance(referencias, list), 'referencias inválidas')
        # La IA puede inventar ids: solo quedan los contenidos que el alumno puede ver.
        return RespuestaTutor(datos['texto'], [
            Referencia(r['contenido_id'], permitidos[r['contenido_id']]['titulo'])
            for r in referencias
            if isinstance(r, dict) and isinstance(r.get('contenido_id'), int)
            and r['contenido_id'] in permitidos
        ])

    @staticmethod
    def _material_del_alumno(alumno):
        """Contenido publicado de las cátedras del alumno, indexado por id.

        De los cuestionarios y prácticas solo se manda el título, para que la IA
        no tenga las respuestas a mano.
        """
        contenidos = Contenido.objects.filter(
            publicado=True, unidad__catedra__in=alumno.cursadas.all(),
        ).select_related('unidad__catedra__materia')
        material = {}
        for contenido in contenidos:
            unidad = contenido.unidad
            item = {
                'id': contenido.id,
                'titulo': contenido.titulo,
                'formato': contenido.formato,
                'catedra': str(unidad.catedra),
                'unidad': unidad.titulo,
                'conceptos': unidad.conceptos,
                'unidad_desbloqueada': unidad.esta_desbloqueada(alumno),
            }
            if contenido.es_teoria:
                item['secciones'] = [s.get('titulo') for s in contenido.cuerpo.get('secciones', [])]
            material[contenido.id] = item
        return material
