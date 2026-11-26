"""Servicio del Tutor IA (CU-08): contexto seguro por pantalla, enlaces y delegación a AsistenteIA."""
from dataclasses import dataclass
from typing import Any

from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.urls import reverse
from django.utils import timezone

from aula.models import Catedra, Clase, Contenido, Evento, Unidad, Usuario
from aula.services.ia_facade import AsistenteIA


@dataclass(frozen=True)
class EnlaceReferencia:
    contenido_id: int
    titulo: str
    url: str


@dataclass(frozen=True)
class RespuestaTutorWeb:
    texto: str
    referencias: list[EnlaceReferencia]
    contexto: dict[str, Any]


def url_material(contenido: Contenido) -> str:
    """Construye una URL válida hacia el material usando resolución dinámica de Django."""
    base = reverse('roadmap', args=[contenido.unidad.catedra_id])
    return f'{base}#contenido-{contenido.id}'


def _validar_inscripcion(alumno: Usuario, catedra_id: int) -> None:
    if not alumno.cursadas.filter(pk=catedra_id).exists():
        raise PermissionDenied('No estás inscripto en esta cátedra.')


def _obtener_catedra_autorizada(alumno: Usuario, catedra_id: int) -> Catedra:
    try:
        catedra = Catedra.objects.select_related('materia').get(pk=catedra_id)
    except Catedra.DoesNotExist as exc:
        raise Http404('La cátedra no existe.') from exc
    _validar_inscripcion(alumno, catedra.pk)
    return catedra


def armar_contexto_pantalla(
    alumno: Usuario,
    pantalla: str,
    *,
    catedra_id: int | None = None,
    unidad_id: int | None = None,
    clase_id: int | None = None,
    contenido_id: int | None = None,
) -> dict[str, Any]:
    """Arma el contexto estructurado de la pantalla actual validando permisos del alumno."""
    hoy = timezone.localdate()
    contexto: dict[str, Any] = {'pantalla': pantalla or 'inicio'}
    catedra: Catedra | None = None

    if contenido_id is not None:
        try:
            contenido = Contenido.objects.select_related('unidad__catedra__materia').get(pk=contenido_id)
        except Contenido.DoesNotExist as exc:
            raise Http404('El contenido no existe.') from exc
        if not contenido.publicado:
            raise PermissionDenied('No tenés acceso a este contenido.')
        _validar_inscripcion(alumno, contenido.unidad.catedra_id)
        catedra = contenido.unidad.catedra
        contexto['contenido'] = {
            'id': contenido.id,
            'titulo': contenido.titulo,
            'formato': contenido.formato,
            'url': url_material(contenido),
        }
        contexto['unidad'] = contenido.unidad.titulo
    elif clase_id is not None:
        try:
            clase = Clase.objects.select_related('catedra__materia', 'unidad').get(pk=clase_id)
        except Clase.DoesNotExist as exc:
            raise Http404('La clase no existe.') from exc
        _validar_inscripcion(alumno, clase.catedra_id)
        catedra = clase.catedra
        contexto['clase'] = {
            'id': clase.id,
            'numero': clase.numero,
            'titulo': clase.titulo,
            'fecha': clase.fecha.isoformat(),
        }
        if clase.unidad:
            contexto['unidad'] = clase.unidad.titulo
    elif unidad_id is not None:
        try:
            unidad = Unidad.objects.select_related('catedra__materia').get(pk=unidad_id)
        except Unidad.DoesNotExist as exc:
            raise Http404('La unidad no existe.') from exc
        _validar_inscripcion(alumno, unidad.catedra_id)
        catedra = unidad.catedra
        contexto['unidad'] = unidad.titulo
    elif catedra_id is not None:
        catedra = _obtener_catedra_autorizada(alumno, catedra_id)

    if catedra is not None:
        contexto['catedra'] = str(catedra)
        contexto['url_catedra'] = reverse('roadmap', args=[catedra.id])
        proximos = Evento.objects.filter(catedra=catedra, fecha__gte=hoy).order_by('fecha')[:5]
    else:
        proximos = (
            Evento.objects.filter(catedra__in=alumno.cursadas.all(), fecha__gte=hoy)
            .select_related('catedra__materia')
            .order_by('fecha')[:5]
        )

    contexto['proximas_fechas'] = [
        {'tipo': ev.tipo, 'titulo': ev.titulo, 'fecha': ev.fecha.isoformat()}
        for ev in proximos
    ]
    return contexto


def consultar_tutor_alumno(
    alumno: Usuario,
    pregunta: str,
    pantalla: str = 'inicio',
    *,
    catedra_id: int | None = None,
    unidad_id: int | None = None,
    clase_id: int | None = None,
    contenido_id: int | None = None,
    asistente: AsistenteIA | None = None,
) -> RespuestaTutorWeb:
    """Valida la pregunta, arma el contexto, consulta a AsistenteIA y resuelve enlaces."""
    pregunta_limpia = (pregunta or '').strip()
    if not pregunta_limpia:
        raise ValueError('La pregunta no puede estar vacía.')

    contexto = armar_contexto_pantalla(
        alumno,
        pantalla,
        catedra_id=catedra_id,
        unidad_id=unidad_id,
        clase_id=clase_id,
        contenido_id=contenido_id,
    )
    servicio_ia = asistente or AsistenteIA()
    respuesta = servicio_ia.consultar_tutor(alumno, pregunta_limpia, contexto)

    ids_citados = [ref.contenido_id for ref in respuesta.referencias]
    contenidos_por_id = {
        c.id: c
        for c in Contenido.objects.filter(
            id__in=ids_citados,
            publicado=True,
            unidad__catedra__in=alumno.cursadas.all(),
        ).select_related('unidad')
    }
    enlaces = [
        EnlaceReferencia(
            contenido_id=ref.contenido_id,
            titulo=ref.titulo,
            url=url_material(contenidos_por_id[ref.contenido_id]),
        )
        for ref in respuesta.referencias
        if ref.contenido_id in contenidos_por_id
    ]
    return RespuestaTutorWeb(texto=respuesta.texto, referencias=enlaces, contexto=contexto)
