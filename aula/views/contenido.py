# Realizar un contenido (CU-07): leer un texto, resolver un cuestionario o
# entregar una práctica. Cada formato es una estrategia (aula/formatos.py) que
# define su template y cuándo el contenido queda completo.
from pathlib import Path

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from aula.decorators import rol_requerido
from aula.formatos import registrar_progreso
from aula.models import Contenido, Progreso


def _contenidos_del_alumno(usuario):
    return Contenido.objects.filter(
        publicado=True, unidad__catedra__alumnos=usuario,
    ).select_related('unidad__catedra__materia')


def _siguiente_unidad(unidad):
    return unidad.catedra.unidades.filter(
        orden__gt=unidad.orden, es_fe_de_erratas=False,
    ).first()


def extensiones_aceptadas(contenido):
    """'.pdf, .zip' -> {'.pdf', '.zip'}. Vacío si la práctica acepta cualquier archivo."""
    texto = contenido.cuerpo.get('formatos_aceptados', '')
    return {
        f".{parte.strip().lstrip('.').lower()}"
        for parte in texto.split(',') if parte.strip()
    }


def _datos_del_intento(request, contenido):
    """Lee lo que manda el alumno según el formato. Devuelve (datos, archivo, error)."""
    if contenido.formato == Contenido.Formato.CUESTIONARIO:
        respuestas = []
        for i, _ in enumerate(contenido.cuerpo.get('preguntas', [])):
            try:
                respuestas.append(int(request.POST.get(f'pregunta-{i}', '')))
            except ValueError:
                respuestas.append(None)  # sin responder: cuenta como error
        return {'respuestas': respuestas}, None, None

    if contenido.formato == Contenido.Formato.PRACTICA:
        archivo = request.FILES.get('archivo')
        if archivo is None:
            return None, None, 'Elegí un archivo para entregar.'
        aceptadas = extensiones_aceptadas(contenido)
        if aceptadas and Path(archivo.name).suffix.lower() not in aceptadas:
            return None, None, f'El archivo tiene que ser {contenido.cuerpo["formatos_aceptados"]}.'
        return {}, archivo, None

    return {}, None, None  # texto: se completa al marcarlo como leído


def _avisar_resultado(request, contenido, progreso, unidad_estaba_completa):
    if progreso.completado_en is None:
        # 5a. Cuestionario no aprobado: queda el intento y puede reintentar.
        messages.error(request, 'No alcanzaste el mínimo para aprobar. Podés volver a intentarlo.')
        return
    mensaje = '¡Listo! Completaste este contenido.'
    if not progreso.en_termino():
        mensaje += ' Quedó registrado fuera de término.'  # 5b
    messages.success(request, mensaje)

    unidad = contenido.unidad
    if not unidad_estaba_completa and unidad.completada_por(request.user):
        siguiente = None if unidad.es_fe_de_erratas else _siguiente_unidad(unidad)
        if siguiente and siguiente.esta_desbloqueada(request.user):
            messages.success(request, f'Completaste la {unidad}. Se desbloqueó la {siguiente}.')
        else:
            messages.success(request, f'Completaste la {unidad}.')


def _resultado_cuestionario(contenido, progreso):
    """Aciertos del último intento, para mostrarlos después de responder."""
    if progreso is None or not progreso.respuesta.get('respuestas'):
        return None
    preguntas = contenido.cuerpo.get('preguntas', [])
    respuestas = progreso.respuesta['respuestas']
    aciertos = sum(1 for p, r in zip(preguntas, respuestas) if p['correcta'] == r)
    return {
        'aciertos': aciertos,
        'total': len(preguntas),
        'minimo': round(contenido.cuerpo.get('aprobacion', 0.6) * 100),
        'respuestas': respuestas,
    }


@rol_requerido('alumno')
def contenido(request, contenido_id):
    contenido = get_object_or_404(_contenidos_del_alumno(request.user), pk=contenido_id)
    unidad = contenido.unidad
    alumno = request.user

    # 2. El contenido solo se puede hacer si su unidad está desbloqueada.
    if not unidad.esta_desbloqueada(alumno):
        anterior = unidad.catedra.unidades.filter(
            orden__lt=unidad.orden, es_fe_de_erratas=False,
        ).last()
        return render(request, 'aula/contenido/bloqueado.html', {
            'contenido': contenido,
            'unidad': unidad,
            'abre_mas_adelante': bool(unidad.fecha_apertura and timezone.localdate() < unidad.fecha_apertura),
            'anterior': None if unidad.es_fe_de_erratas else anterior,
        })

    progreso = Progreso.objects.filter(alumno=alumno, contenido=contenido).first()

    if request.method == 'POST':
        if progreso and progreso.completado_en:
            messages.info(request, 'Este contenido ya estaba completado.')
            return redirect('contenido', contenido.id)
        datos, archivo, error = _datos_del_intento(request, contenido)
        if error:
            messages.error(request, error)
            return redirect('contenido', contenido.id)
        unidad_estaba_completa = unidad.completada_por(alumno)
        progreso = registrar_progreso(alumno, contenido, datos, archivo)
        _avisar_resultado(request, contenido, progreso, unidad_estaba_completa)
        return redirect('contenido', contenido.id)

    return render(request, contenido.estrategia.template, {
        'contenido': contenido,
        'unidad': unidad,
        'progreso': progreso,
        'completado': bool(progreso and progreso.completado_en),
        'resultado': _resultado_cuestionario(contenido, progreso)
        if contenido.formato == Contenido.Formato.CUESTIONARIO else None,
        'accept': ','.join(sorted(extensiones_aceptadas(contenido)))
        if contenido.formato == Contenido.Formato.PRACTICA else '',
    })
