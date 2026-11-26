# Configuracion interna del módulo (generado por django)
from django.apps import AppConfig


class AulaConfig(AppConfig):
    name = 'aula'

    def ready(self):
        from . import signals  # noqa: F401
