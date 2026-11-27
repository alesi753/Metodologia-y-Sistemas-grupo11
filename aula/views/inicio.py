# Pantalla de inicio: cursadas del alumno o cátedras del profesor
from django.shortcuts import render

from aula.decorators import rol_requerido


@rol_requerido('alumno', 'profesor')
def inicio(request):
    return render(request, 'aula/inicio.html', {
        'cursadas': request.user.cursadas.select_related('materia'),
        'catedras': request.user.catedras.select_related('materia'),
    })
