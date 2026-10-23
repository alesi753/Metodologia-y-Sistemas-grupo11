# Panel de administración: alta y edición de datos institucionales desde /admin
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Carrera, Catedra, Contenido, Materia, Progreso, Unidad, Usuario


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ('Datos personales', {'fields': ('dni', 'fecha_nacimiento')}),
    )
    list_display = ['username', 'first_name', 'last_name', 'dni', 'is_staff']


admin.site.register(Carrera)


@admin.register(Materia)
class MateriaAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'carrera']
    list_filter = ['carrera']
    search_fields = ['nombre']


class UnidadInline(admin.TabularInline):
    model = Unidad
    fields = ['orden', 'titulo', 'fecha_apertura', 'fecha_limite']
    extra = 0
    show_change_link = True


@admin.register(Catedra)
class CatedraAdmin(admin.ModelAdmin):
    list_display = ['materia', 'anio', 'cuatrimestre']
    list_filter = ['materia__carrera', 'anio', 'cuatrimestre']
    search_fields = ['materia__nombre']
    filter_horizontal = ['profesores', 'alumnos']
    inlines = [UnidadInline]


class ContenidoInline(admin.TabularInline):
    model = Contenido
    fields = ['titulo', 'formato', 'publicado', 'autor']
    extra = 0
    show_change_link = True


@admin.register(Unidad)
class UnidadAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'catedra', 'fecha_apertura', 'fecha_limite']
    list_filter = ['catedra__materia']
    inlines = [ContenidoInline]


@admin.register(Contenido)
class ContenidoAdmin(admin.ModelAdmin):
    list_display = ['titulo', 'unidad', 'formato', 'publicado']
    list_filter = ['formato', 'publicado', 'unidad__catedra__materia']
    search_fields = ['titulo']


@admin.register(Progreso)
class ProgresoAdmin(admin.ModelAdmin):
    list_display = ['alumno', 'contenido', 'completado_en', 'intentos']
    list_filter = ['contenido__unidad__catedra__materia', 'contenido__formato']
