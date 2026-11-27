# Pantalla de inicio. Para el alumno es el hub de sus cursadas (CU-01):
# en qué unidad va de cada una, las próximas fechas y los últimos avisos.
from django.shortcuts import render
from django.utils import timezone

from aula.decorators import rol_requerido
from aula.models import Alumno, Aviso, Contenido, Evento, Progreso

PROXIMAS_FECHAS = 5
ULTIMOS_AVISOS = 5


@rol_requerido('alumno', 'profesor')
def inicio(request):
    contexto = {'catedras': request.user.catedras.select_related('materia')}
    if request.user.groups.filter(name='alumno').exists():
        contexto.update(_hub_del_alumno(request.user))
    return render(request, 'aula/inicio.html', contexto)


def _hub_del_alumno(usuario):
    alumno = Alumno.objects.get(pk=usuario.pk)
    cursadas = list(alumno.cursadas.select_related('materia'))
    completados = set(Progreso.objects.filter(
        alumno=alumno, completado_en__isnull=False,
    ).values_list('contenido_id', flat=True))

    resumen = []
    for catedra in cursadas:
        publicados = set(Contenido.objects.filter(
            unidad__catedra=catedra, publicado=True,
        ).values_list('id', flat=True))
        resumen.append({
            'catedra': catedra,
            'unidad_actual': alumno.unidad_actual(catedra),
            'total': len(publicados),
            'hechos': len(publicados & completados),
        })

    hoy = timezone.localdate()
    fechas = list(
        Evento.objects.filter(catedra__in=cursadas, fecha__gte=hoy)
        .select_related('catedra__materia')[:PROXIMAS_FECHAS]
    )
    # Si la fecha es una entrega dentro del aula, su estado sale del Progreso.
    for evento in fechas:
        evento.entregado = evento.contenido_id in completados if evento.contenido_id else None

    avisos = (
        Aviso.objects.filter(catedra__in=cursadas, publicado_en__lte=timezone.now())
        .select_related('catedra__materia', 'autor')[:ULTIMOS_AVISOS]
    )
    return {'cursadas': resumen, 'fechas': fechas, 'avisos': avisos, 'hoy': hoy}
