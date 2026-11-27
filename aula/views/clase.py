# Clase del día (CU-05) y unirse a la clase en vivo con registro de
# asistencia (CU-06).
from datetime import datetime, timedelta

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from aula.decorators import rol_requerido
from aula.models import Asistencia, Clase, Progreso

# Desde cuánto antes del inicio se puede entrar a la clase en vivo.
ANTICIPO_PARA_UNIRSE = timedelta(minutes=15)
PROXIMAS_HABILITADAS = 5


def _clases_del_alumno(usuario):
    return Clase.objects.filter(catedra__alumnos=usuario).select_related(
        'catedra__materia', 'unidad',
    )


def esta_habilitada(clase, alumno, hoy):
    """Una clase se puede ver desde su fecha, o antes si su unidad ya está desbloqueada."""
    if clase.fecha <= hoy:
        return True
    return clase.unidad is not None and clase.unidad.esta_desbloqueada(alumno)


def en_vivo(clase, ahora):
    """Si ahora se puede entrar a la clase en vivo: desde un rato antes hasta que termina."""
    inicio = datetime.combine(clase.fecha, clase.hora_inicio) - ANTICIPO_PARA_UNIRSE
    fin = datetime.combine(clase.fecha, clase.hora_fin)
    return inicio <= ahora.replace(tzinfo=None) <= fin


def _detalle(clase, alumno, ahora):
    """Datos de una clase para el template: temario, material, tareas y asistencia."""
    hechos = set(Progreso.objects.filter(
        alumno=alumno, contenido__in=clase.contenidos.all(), completado_en__isnull=False,
    ).values_list('contenido_id', flat=True))
    contenidos = [c for c in clase.contenidos.all() if c.publicado]
    return {
        'clase': clase,
        'material': [c for c in contenidos if c.es_teoria],
        'tareas': [c for c in contenidos if not c.es_teoria],
        'hechos': hechos,
        'presente': Asistencia.objects.filter(alumno=alumno, clase=clase).exists(),
        'en_vivo': bool(clase.link_videollamada) and en_vivo(clase, ahora),
        'es_hoy': clase.fecha == ahora.date(),
        'termino': datetime.combine(clase.fecha, clase.hora_fin) < ahora.replace(tzinfo=None),
    }


@rol_requerido('alumno')
def clase_hoy(request):
    """Clases de hoy de todas las cursadas; si no hay, la próxima."""
    alumno = request.user
    ahora = timezone.localtime()
    hoy = ahora.date()
    clases = _clases_del_alumno(alumno)

    de_hoy = list(clases.filter(fecha=hoy))
    proxima = None if de_hoy else clases.filter(fecha__gt=hoy).first()

    # Clases futuras que el alumno ya puede adelantar porque su unidad está abierta.
    habilitadas = []
    for clase in clases.filter(fecha__gt=hoy, unidad__isnull=False):
        if clase != proxima and esta_habilitada(clase, alumno, hoy):
            habilitadas.append(clase)
        if len(habilitadas) == PROXIMAS_HABILITADAS:
            break

    return render(request, 'aula/clase_hoy.html', {
        'clases': [_detalle(clase, alumno, ahora) for clase in de_hoy],
        'proxima': proxima,
        'proxima_habilitada': proxima is not None and esta_habilitada(proxima, alumno, hoy),
        'habilitadas': habilitadas,
    })


@rol_requerido('alumno')
def detalle(request, clase_id):
    """Una clase puntual: la de otro día o una próxima que se adelanta."""
    alumno = request.user
    ahora = timezone.localtime()
    clase = get_object_or_404(_clases_del_alumno(alumno), pk=clase_id)
    contexto = {'clase': clase, 'habilitada': esta_habilitada(clase, alumno, ahora.date())}
    if contexto['habilitada']:
        contexto.update(_detalle(clase, alumno, ahora))
    return render(request, 'aula/clase.html', contexto)


@require_POST
@rol_requerido('alumno')
def unirse(request, clase_id):
    """Registra la asistencia y redirige a la videollamada (CU-06)."""
    clase = get_object_or_404(_clases_del_alumno(request.user), pk=clase_id)
    if not clase.link_videollamada:
        messages.error(request, 'Esta clase no tiene link de videollamada.')
        return redirect('clase', clase.id)
    if not en_vivo(clase, timezone.localtime()):
        messages.error(request, 'La clase en vivo no está disponible en este momento.')
        return redirect('clase', clase.id)
    Asistencia.objects.get_or_create(alumno=request.user, clase=clase)
    return redirect(clase.link_videollamada)
