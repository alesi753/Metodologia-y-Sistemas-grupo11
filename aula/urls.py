# Rutas propias del aula, montadas en config/urls.py.
# Cada pantalla vive en su módulo de aula/views/. Los nombres de ruta que
# aparecen en la navegación están en aula/context_processors.py.
from django.urls import path

from .views import cursada, inicio

urlpatterns = [
    path('', inicio.inicio, name='inicio'),
    path('cursada/<int:catedra_id>/', cursada.roadmap, name='roadmap'),
    path('cursada/<int:catedra_id>/avisos/', cursada.avisos, name='avisos'),
]
