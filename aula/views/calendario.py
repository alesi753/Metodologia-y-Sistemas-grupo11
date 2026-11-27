# Calendario del alumno (CU-04): clases y fechas importantes del mes de
# todas sus cursadas, con filtro por clases o por fechas (deadlines).
import calendar
from collections import defaultdict
from datetime import date, time, timedelta

from django.shortcuts import render
from django.utils import timezone

from aula.decorators import rol_requerido
from aula.models import Clase, Evento, Unidad

FILTROS = {
    'todo': 'Todo',
    'clases': 'Clases',
    'fechas': 'Fechas',
}

# Meses que abarca cada cuatrimestre. Los horarios se repiten solo dentro de
# ellos, para no llenar de clases los meses sin cursada.
MESES_CUATRIMESTRE = {1: (3, 7), 2: (8, 12)}


def _mes_pedido(valor, hoy):
    """Lee ?mes=AAAA-MM. Si falta o es inválido, usa el mes actual."""
    try:
        anio, mes = (int(parte) for parte in valor.split('-'))
        return date(anio, mes, 1)
    except (AttributeError, ValueError):
        return hoy.replace(day=1)


def _en_cuatrimestre(catedra, fecha):
    desde, hasta = MESES_CUATRIMESTRE.get(catedra.cuatrimestre, (1, 12))
    return fecha.year == catedra.anio and desde <= fecha.month <= hasta


def _clases(cursadas, desde, hasta):
    """Clases cargadas y, en los días de cursada sin clase cargada, el horario semanal."""
    items = []
    con_clase = set()
    clases = Clase.objects.filter(
        catedra__in=cursadas, fecha__range=(desde, hasta),
    ).select_related('catedra__materia')
    for clase in clases:
        con_clase.add((clase.catedra_id, clase.fecha))
        items.append({
            'fecha': clase.fecha, 'hora': clase.hora_inicio, 'tipo': 'clase',
            'titulo': f'Clase {clase.numero}: {clase.titulo}', 'catedra': clase.catedra,
        })

    for catedra in cursadas:
        for horario in catedra.horarios.all():
            fecha = desde + timedelta(days=(horario.dia - desde.weekday()) % 7)
            while fecha <= hasta:
                if (catedra.id, fecha) not in con_clase and _en_cuatrimestre(catedra, fecha):
                    items.append({
                        'fecha': fecha, 'hora': horario.hora_inicio, 'tipo': 'horario',
                        'titulo': f'Cursada hasta las {horario.hora_fin:%H:%M}',
                        'catedra': catedra,
                    })
                fecha += timedelta(weeks=1)
    return items


def _fechas(cursadas, desde, hasta):
    """Fechas importantes (Evento) y fechas límite de las unidades."""
    items = [
        {
            'fecha': evento.fecha, 'hora': None, 'tipo': evento.tipo,
            'titulo': f'{evento.get_tipo_display()}: {evento.titulo}', 'catedra': evento.catedra,
        }
        for evento in Evento.objects.filter(
            catedra__in=cursadas, fecha__range=(desde, hasta),
        ).select_related('catedra__materia')
    ]
    items += [
        {
            'fecha': unidad.fecha_limite, 'hora': None, 'tipo': 'limite',
            'titulo': f'Cierra la {unidad}', 'catedra': unidad.catedra,
        }
        for unidad in Unidad.objects.filter(
            catedra__in=cursadas, es_fe_de_erratas=False, fecha_limite__range=(desde, hasta),
        ).select_related('catedra__materia')
    ]
    return items


@rol_requerido('alumno')
def calendario(request):
    hoy = timezone.localdate()
    primero = _mes_pedido(request.GET.get('mes'), hoy)
    ver = request.GET.get('ver') if request.GET.get('ver') in FILTROS else 'todo'

    semanas = calendar.Calendar(firstweekday=0).monthdatescalendar(primero.year, primero.month)
    desde, hasta = semanas[0][0], semanas[-1][-1]
    cursadas = list(request.user.cursadas.select_related('materia').prefetch_related('horarios'))

    items = []
    if ver in ('todo', 'clases'):
        items += _clases(cursadas, desde, hasta)
    if ver in ('todo', 'fechas'):
        items += _fechas(cursadas, desde, hasta)

    por_dia = defaultdict(list)
    for item in sorted(items, key=lambda i: (i['fecha'], i['hora'] or time.min, i['titulo'])):
        item['es_clase'] = item['tipo'] in ('clase', 'horario')
        por_dia[item['fecha']].append(item)

    grilla = [
        [{'fecha': dia, 'del_mes': dia.month == primero.month, 'items': por_dia.get(dia, [])}
         for dia in semana]
        for semana in semanas
    ]
    agenda = [
        (dia, por_dia[dia])
        for semana in semanas for dia in semana
        if dia.month == primero.month and por_dia.get(dia)
    ]
    anterior = (primero - timedelta(days=1)).replace(day=1)
    siguiente = (primero + timedelta(days=31)).replace(day=1)

    return render(request, 'aula/calendario.html', {
        'mes': primero,
        'grilla': grilla,
        'agenda': agenda,
        'hoy': hoy,
        'ver': ver,
        'filtros': FILTROS,
        'anterior': f'{anterior:%Y-%m}',
        'siguiente': f'{siguiente:%Y-%m}',
        'actual': f'{hoy:%Y-%m}',
        'dias_semana': ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom'],
    })
