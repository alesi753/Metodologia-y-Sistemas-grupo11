# Módulo de lógica: funciones que reciben requests y calculan el roadmap
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render
from django.utils import timezone

from .models import Progreso


@login_required
def inicio(request):
    return render(request, 'aula/inicio.html', {
        'cursadas': request.user.cursadas.select_related('materia'),
        'catedras': request.user.catedras.select_related('materia'),
    })


@login_required
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
