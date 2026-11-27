"""Datos comunes a todas las pantallas: el rol del usuario y su navegación.

Cada rol tiene su menú de la navegación inferior como una lista de
(nombre de ruta, etiqueta). Una ruta que todavía no existe se omite, así que
cada rama de pantalla solo tiene que registrar su ruta con ese nombre en
aula/urls.py para aparecer en el menú.
"""
from django.urls import NoReverseMatch, reverse

MENUS = {
    'alumno': [
        ('inicio', 'Inicio'),
        ('calendario', 'Calendario'),
        ('clase_hoy', 'Clase de hoy'),
    ],
    'profesor': [
        ('inicio', 'Inicio'),
    ],
}


def navegacion(request):
    usuario = getattr(request, 'user', None)
    if usuario is None or not usuario.is_authenticated:
        return {'es_alumno': False, 'es_profesor': False, 'menu': []}

    grupos = set(usuario.groups.values_list('name', flat=True))
    # Un usuario con los dos roles navega como profesor.
    rol = 'profesor' if 'profesor' in grupos else 'alumno' if 'alumno' in grupos else None

    match = getattr(request, 'resolver_match', None)
    actual = match.url_name if match else None
    menu = []
    for nombre, etiqueta in MENUS.get(rol, []):
        try:
            url = reverse(nombre)
        except NoReverseMatch:
            continue
        menu.append({'url': url, 'etiqueta': etiqueta, 'activo': nombre == actual})

    return {
        'es_alumno': 'alumno' in grupos,
        'es_profesor': 'profesor' in grupos,
        'menu': menu,
    }
