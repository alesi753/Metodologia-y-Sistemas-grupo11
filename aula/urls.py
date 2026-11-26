# Rutas propias del aula, montadas en config/urls.py
from django.urls import path

from . import views

urlpatterns = [
    path('', views.inicio, name='inicio'),
    path('cursada/<int:catedra_id>/', views.roadmap, name='roadmap'),
    path('tutor/consultar/', views.tutor_consultar, name='tutor_consultar'),
]
