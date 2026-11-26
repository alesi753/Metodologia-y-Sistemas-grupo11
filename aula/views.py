# Módulo de lógica: funciones que reciben requests y calculan el roadmap
import json

from django.core.exceptions import PermissionDenied
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .decorators import rol_requerido
from .models import Progreso
from .services.ia_facade import ErrorIA
from .services.tutor_service import consultar_tutor_alumno


def _parsear_entero_opcional(valor, campo):
    if valor is None or valor == '':
        return None
    if isinstance(valor, bool):
        raise ValueError(f'{campo} debe ser un entero válido.')
    try:
        return int(valor)
    except (TypeError, ValueError) as exc:
        raise ValueError(f'{campo} debe ser un entero válido.') from exc


@rol_requerido('alumno', 'profesor')
def inicio(request):
    return render(request, 'aula/inicio.html', {
        'cursadas': request.user.cursadas.select_related('materia'),
        'catedras': request.user.catedras.select_related('materia'),
    })


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


@require_POST
@rol_requerido('alumno')
def tutor_consultar(request):
    try:
        payload = json.loads(request.body.decode('utf-8') or '{}')
    except (UnicodeDecodeError, json.JSONDecodeError):
        return JsonResponse({'error': 'El cuerpo debe ser un JSON válido.'}, status=400)

    if not isinstance(payload, dict):
        return JsonResponse({'error': 'El cuerpo debe ser un objeto JSON.'}, status=400)

    pregunta = payload.get('pregunta', '')
    if pregunta is not None and not isinstance(pregunta, str):
        return JsonResponse({'error': 'La pregunta debe ser texto.'}, status=400)

    try:
        resultado = consultar_tutor_alumno(
            request.user,
            pregunta or '',
            pantalla=str(payload.get('pantalla') or 'inicio'),
            catedra_id=_parsear_entero_opcional(payload.get('catedra_id'), 'catedra_id'),
            unidad_id=_parsear_entero_opcional(payload.get('unidad_id'), 'unidad_id'),
            clase_id=_parsear_entero_opcional(payload.get('clase_id'), 'clase_id'),
            contenido_id=_parsear_entero_opcional(payload.get('contenido_id'), 'contenido_id'),
        )
    except ValueError as error:
        return JsonResponse({'error': str(error)}, status=400)
    except PermissionDenied as error:
        return JsonResponse({'error': str(error)}, status=403)
    except Http404 as error:
        return JsonResponse({'error': str(error)}, status=404)
    except ErrorIA as error:
        return JsonResponse({'error': str(error)}, status=503)

    return JsonResponse({
        'texto': resultado.texto,
        'referencias': [
            {
                'contenido_id': ref.contenido_id,
                'titulo': ref.titulo,
                'url': ref.url,
            }
            for ref in resultado.referencias
        ],
    })
