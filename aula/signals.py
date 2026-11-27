"""Observer de dominio: reacciona al guardar Progreso y Aviso sin acoplar los modelos."""
import logging

from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import Signal, receiver

from .models import Aviso, Progreso, Unidad

logger = logging.getLogger(__name__)

# Señales de dominio desacopladas de la persistencia
unidad_completada = Signal()  # kwargs: alumno, unidad, siguiente_unidad
aviso_publicado = Signal()    # kwargs: aviso, catedra, destinatarios


def _siguiente_unidad_regular(unidad: Unidad) -> Unidad | None:
    if unidad.es_fe_de_erratas:
        return None
    return (
        unidad.catedra.unidades.filter(orden__gt=unidad.orden, es_fe_de_erratas=False)
        .order_by('orden')
        .first()
    )


def _notificar_unidad_completada(progreso: Progreso) -> None:
    unidad = progreso.contenido.unidad
    alumno = progreso.alumno
    if not unidad.completada_por(alumno):
        return

    siguiente = _siguiente_unidad_regular(unidad)
    if siguiente and not siguiente.esta_desbloqueada(alumno):
        siguiente = None

    logger.info(
        'Unidad completada: alumno=%s unidad=%s siguiente=%s',
        alumno.pk,
        unidad.pk,
        siguiente.pk if siguiente else None,
    )
    unidad_completada.send(
        sender=Unidad,
        alumno=alumno,
        unidad=unidad,
        siguiente_unidad=siguiente,
    )


def _notificar_aviso_publicado(aviso: Aviso) -> None:
    destinatarios = list(aviso.catedra.alumnos.all())
    logger.info(
        'Aviso publicado: aviso=%s catedra=%s destinatarios=%d',
        aviso.pk,
        aviso.catedra_id,
        len(destinatarios),
    )
    aviso_publicado.send(
        sender=Aviso,
        aviso=aviso,
        catedra=aviso.catedra,
        destinatarios=destinatarios,
    )


@receiver(post_save, sender=Progreso)
def al_guardar_progreso(sender, instance: Progreso, created: bool, raw: bool, **kwargs) -> None:
    if raw or instance.completado_en is None:
        return
    transaction.on_commit(lambda: _notificar_unidad_completada(instance))


@receiver(post_save, sender=Aviso)
def al_publicar_aviso(sender, instance: Aviso, created: bool, raw: bool, **kwargs) -> None:
    if raw or not created:
        return
    transaction.on_commit(lambda: _notificar_aviso_publicado(instance))
