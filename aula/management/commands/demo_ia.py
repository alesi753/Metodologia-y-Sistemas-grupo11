"""Prueba los tres métodos de AsistenteIA desde la consola.

    python manage.py demo_ia                  # Anthropic si hay ANTHROPIC_API_KEY
    python manage.py demo_ia --falso          # sin conexión
    python manage.py demo_ia --pdf programa.pdf

Si la base no tiene un alumno con material publicado, crea datos de ejemplo
dentro de una transacción que se deshace al final: la base queda como estaba.
"""
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from aula.models import Carrera, Catedra, Contenido, Materia, Unidad, Usuario
from aula.services.ia_facade import AsistenteIA, ErrorIA, ProveedorFalso, proveedor_por_defecto

LINEAS_PROGRAMA = [
    'Programa: Legislacion - TUP 2026',
    'Unidad 1: Derecho constitucional. Supremacia, derechos y garantias.',
    'Unidad 2: Derecho civil. Personas, contratos y responsabilidad.',
    'Unidad 3: Derecho informatico. Datos personales y propiedad intelectual.',
]


def pdf_de_ejemplo(lineas=LINEAS_PROGRAMA):
    """Arma un PDF mínimo de una página con las líneas dadas."""
    texto = ' '.join(f'({linea}) Tj 0 -24 Td' for linea in lineas)
    flujo = f'BT /F1 12 Tf 60 760 Td {texto} ET'.encode('latin-1')
    objetos = [
        b'<< /Type /Catalog /Pages 2 0 R >>',
        b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
        b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] '
        b'/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>',
        b'<< /Length %d >>\nstream\n%s\nendstream' % (len(flujo), flujo),
        b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',
    ]
    salida = bytearray(b'%PDF-1.4\n')
    posiciones = []
    for numero, objeto in enumerate(objetos, start=1):
        posiciones.append(len(salida))
        salida += b'%d 0 obj\n%s\nendobj\n' % (numero, objeto)
    inicio_xref = len(salida)
    salida += b'xref\n0 %d\n0000000000 65535 f \n' % (len(objetos) + 1)
    salida += b''.join(b'%010d 00000 n \n' % p for p in posiciones)
    salida += b'trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n' % (
        len(objetos) + 1, inicio_xref,
    )
    return bytes(salida)


def crear_datos_de_ejemplo():
    alumno = Usuario.objects.create_user('demo-ia-alumno')
    materia = Materia.objects.create(
        nombre='Legislación', carrera=Carrera.objects.create(nombre='Demo IA'),
    )
    catedra = Catedra.objects.create(materia=materia, anio=2026, cuatrimestre=2)
    catedra.alumnos.add(alumno)
    unidad = Unidad.objects.create(
        catedra=catedra, orden=1, titulo='Derecho constitucional',
        conceptos=['Supremacía constitucional', 'Derechos y garantías'],
    )
    Contenido.objects.create(
        unidad=unidad, formato='texto', titulo='La pirámide de Kelsen', publicado=True,
        cuerpo={'secciones': [{'titulo': 'Supremacía', 'texto': 'La Constitución está arriba.'}]},
    )
    Contenido.objects.create(
        unidad=unidad, formato='cuestionario', titulo='Repaso de garantías', publicado=True,
    )
    return alumno


def buscar_alumno_con_material():
    contenido = Contenido.objects.filter(
        publicado=True, unidad__catedra__alumnos__isnull=False,
    ).select_related('unidad__catedra').first()
    if contenido:
        return contenido.unidad.catedra.alumnos.first()
    return None


def resumir_cuerpo(borrador):
    """Líneas legibles del cuerpo de un borrador, según su formato."""
    cuerpo = borrador.cuerpo
    if borrador.formato == Contenido.Formato.TEXTO:
        return [f'- {s["titulo"]}' for s in cuerpo['secciones']]
    if borrador.formato == Contenido.Formato.CUESTIONARIO:
        lineas = [f'Aprobación: {cuerpo["aprobacion"]:.0%}']
        for pregunta in cuerpo['preguntas']:
            lineas.append(f'- {pregunta["enunciado"]}')
            lineas += [
                f'    {"*" if i == pregunta["correcta"] else " "} {opcion}'
                for i, opcion in enumerate(pregunta['opciones'])
            ]
        return lineas
    return [f'Consigna: {cuerpo["consigna"]}', *(f'- {e}' for e in cuerpo['entregables']),
            f'Formatos: {cuerpo["formatos_aceptados"]}']


def primer_contenido(alumno):
    return Contenido.objects.filter(
        publicado=True, unidad__catedra__alumnos=alumno,
    ).select_related('unidad__catedra__materia').first()


class Command(BaseCommand):
    help = 'Ejecuta los tres métodos de AsistenteIA e imprime los resultados.'

    def add_arguments(self, parser):
        parser.add_argument('--falso', action='store_true', help='Usar el proveedor falso, sin red.')
        parser.add_argument('--pdf', help='Ruta de un programa en PDF para importar_programa.')

    def handle(self, *args, falso, pdf, **opciones):
        pdf_bytes = Path(pdf).read_bytes() if pdf else pdf_de_ejemplo()
        with transaction.atomic():
            alumno = buscar_alumno_con_material() or crear_datos_de_ejemplo()
            proveedor = ProveedorFalso() if falso else proveedor_por_defecto()
            if isinstance(proveedor, ProveedorFalso):
                proveedor.respuestas['tutor'] = self._tutor_falso(alumno)
            self.stdout.write(f'Proveedor: {type(proveedor).__name__}\n')
            try:
                self._demo(AsistenteIA(proveedor), alumno, pdf_bytes)
            except ErrorIA as error:
                raise CommandError(f'Falló la IA: {error}') from error
            finally:
                transaction.set_rollback(True)

    def _demo(self, asistente, alumno, pdf_bytes):
        self._titulo('1. importar_programa')
        programa = asistente.importar_programa(pdf_bytes)
        for numero, unidad in enumerate(programa.unidades, start=1):
            self.stdout.write(f'  Unidad {numero}: {unidad.titulo}')
            self.stdout.write(f'    Conceptos: {", ".join(unidad.conceptos)}')

        unidad = primer_contenido(alumno).unidad
        catedra = unidad.catedra
        conceptos = unidad.conceptos or [unidad.titulo]
        self._titulo(f'2. generar_contenido ({unidad.titulo})')
        borrador = asistente.generar_contenido(unidad, conceptos, 'introductoria, con ejemplos')
        self.stdout.write(f'  Formato sugerido: {borrador.formato}')
        self.stdout.write(f'  Título: {borrador.titulo}')
        for linea in resumir_cuerpo(borrador):
            self.stdout.write(f'    {linea}')

        pregunta = f'No entiendo bien {conceptos[0]}, ¿me lo explicás?'
        self._titulo('3. consultar_tutor')
        self.stdout.write(f'  Alumno: {alumno} | Pregunta: {pregunta}')
        respuesta = asistente.consultar_tutor(alumno, pregunta, {
            'pantalla': 'curso', 'catedra': str(catedra), 'unidad': unidad.titulo,
        })
        self.stdout.write(f'  Respuesta: {respuesta.texto}')
        for referencia in respuesta.referencias:
            self.stdout.write(f'  -> Contenido {referencia.contenido_id}: {referencia.titulo}')

    def _titulo(self, texto):
        self.stdout.write(self.style.MIGRATE_HEADING(f'\n{texto}'))

    @staticmethod
    def _tutor_falso(alumno):
        """Respuesta fija del tutor que cita el primer contenido del alumno."""
        contenido = primer_contenido(alumno)
        return {
            'texto': 'Es un tema central de la unidad. Repasá el material citado y '
                     'volvé con dudas puntuales.',
            'referencias': [{'contenido_id': contenido.id, 'titulo': contenido.titulo}],
        }
