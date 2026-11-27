# Pantallas de una cursada del alumno: la ficha del curso con su recorrido
# de unidades (CU-02) y los avisos de la cátedra (CU-03).
from django.db.models import Q
from django.shortcuts import get_object_or_404, render
from django.utils import timezone

from aula.decorators import rol_requerido
from aula.models import Progreso


def _cursada_del_alumno(request, catedra_id):
    # Solo cursadas del usuario: si no está inscripto, 404.
    return get_object_or_404(request.user.cursadas.select_related('materia'), pk=catedra_id)


def _avisos_publicados(catedra):
    return catedra.avisos.filter(publicado_en__lte=timezone.now()).select_related('autor')


@rol_requerido('alumno')
def roadmap(request, catedra_id):
    """Ficha del curso (CU-02): profesorado, horarios, próxima clase y recorrido."""
    catedra = _cursada_del_alumno(request, catedra_id)
    alumno = request.user
    ahora = timezone.localtime()

    unidades = []
    for unidad in catedra.unidades.all():
        if unidad.completada_por(alumno):
            estado = 'completa'
        elif unidad.esta_desbloqueada(alumno):
            estado = 'en curso'
        else:
            estado = 'bloqueada'
        unidades.append({
            'unidad': unidad,
            'estado': estado,
            'contenidos': unidad.contenidos.filter(publicado=True),
        })

    hechos = set(Progreso.objects.filter(
        alumno=alumno, contenido__unidad__catedra=catedra, completado_en__isnull=False,
    ).values_list('contenido_id', flat=True))

    # La próxima clase es la de hoy mientras no terminó, o la siguiente.
    proxima_clase = catedra.clases.filter(
        Q(fecha__gt=ahora.date()) | Q(fecha=ahora.date(), hora_fin__gte=ahora.time()),
    ).first()

    return render(request, 'aula/roadmap.html', {
        'catedra': catedra,
        'profesores': catedra.profesores.all(),
        'horarios': catedra.horarios.all(),
        'proxima_clase': proxima_clase,
        'ultimo_aviso': _avisos_publicados(catedra).first(),
        'unidades': unidades,
        'hechos': hechos,
        'hoy': ahora.date(),
    })


@rol_requerido('alumno')
def avisos(request, catedra_id):
    """Avisos de la cátedra (CU-03). Solo lectura: publica el profesorado."""
    catedra = _cursada_del_alumno(request, catedra_id)
    return render(request, 'aula/avisos.html', {
        'catedra': catedra,
        'avisos': _avisos_publicados(catedra),
    })
