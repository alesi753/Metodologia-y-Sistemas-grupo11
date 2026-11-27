# Recorrido de una cursada: estado de cada unidad para el alumno
from django.shortcuts import get_object_or_404, render
from django.utils import timezone

from aula.decorators import rol_requerido
from aula.models import Progreso


@rol_requerido('alumno')
def roadmap(request, catedra_id):
    # Solo cursadas del usuario: si no está inscripto, 404.
    catedra = get_object_or_404(request.user.cursadas.select_related('materia'), pk=catedra_id)
    alumno = request.user

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

    return render(request, 'aula/roadmap.html', {
        'catedra': catedra,
        'unidades': unidades,
        'hechos': hechos,
        'hoy': timezone.localdate(),
    })
