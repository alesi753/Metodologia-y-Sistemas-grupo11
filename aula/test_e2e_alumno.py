"""E2E de la perspectiva del alumno (CU-01 a CU-08) en un navegador real.

Cubre lo que el cliente de Django no puede: el JavaScript del tutor y el
recorrido completo entre pantallas. No corre con la suite normal si Playwright
no está instalado. Preparación del entorno en docs/testing.md. Para correrlo:

    uv pip install -r requirements-dev.txt && playwright install chromium
    python manage.py test --tag=e2e
"""
import os
import re
from datetime import time
from unittest import SkipTest, skipUnless
from unittest.mock import patch

from django.contrib.auth.models import Group
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.test import override_settings, tag
from django.utils import timezone

from .management import datos_demo as datos
from .management.commands.cargar_demo import CargaDemo
from .models import Asistencia, Clase, Contenido, Progreso, Unidad, Usuario
from .services.ia_proveedores import ProveedorFalso

try:
    from playwright.sync_api import Error as PlaywrightError
    from playwright.sync_api import expect, sync_playwright
except ImportError:
    sync_playwright = None


@tag('e2e')
@skipUnless(sync_playwright, 'Falta Playwright: pip install -r requirements-dev.txt')
@override_settings(
    IA_PROVEEDOR='falso',
    PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'],
)
class RecorridoAlumnoE2E(StaticLiveServerTestCase):
    @classmethod
    def setUpClass(cls):
        # Playwright corre su propio loop asíncrono y Django prohíbe tocar la base desde ahí.
        cls.enterClassContext(patch.dict(os.environ, {'DJANGO_ALLOW_ASYNC_UNSAFE': 'true'}))
        super().setUpClass()
        cls.playwright = sync_playwright().start()
        cls.addClassCleanup(cls.playwright.stop)
        try:
            cls.navegador = cls.playwright.chromium.launch()
        except PlaywrightError as error:
            raise SkipTest(f'Falta el navegador: playwright install chromium ({error})') from error
        cls.addClassCleanup(cls.navegador.close)

    def setUp(self):
        # Este tipo de test vacía la base entre casos, incluidos los grupos que crea una migración.
        for rol in ('alumno', 'profesor'):
            Group.objects.get_or_create(name=rol)
        self.hoy = timezone.localdate()
        CargaDemo(self.hoy).cargar()
        self.preparar_clase_en_vivo()
        self.preparar_unidad_por_desbloquear()
        self.preparar_respuesta_del_tutor()

        contexto = self.navegador.new_context(locale='es-AR')
        contexto.set_default_timeout(10_000)
        # Solo el aula: sin CDN, el resultado no depende de la red.
        contexto.route('**/*', lambda ruta: (
            ruta.continue_() if ruta.request.url.startswith(self.live_server_url) else ruta.abort()
        ))
        self.addCleanup(contexto.close)
        self.contexto = contexto
        self.page = contexto.new_page()

    # Datos: la demo con tres ajustes para que el resultado no dependa del día ni de la hora.

    def preparar_clase_en_vivo(self):
        """La demo ubica las clases según el día de la semana: dejamos una abierta hoy, todo el día."""
        clase = Clase.objects.get(catedra__materia__nombre='Gestión de Desarrollo de Software',
                                  titulo='Modelos de proceso')
        Asistencia.objects.filter(clase=clase).delete()
        Clase.objects.filter(pk=clase.pk).update(
            fecha=self.hoy, hora_inicio=time(0, 0), hora_fin=time(23, 59, 59),
            link_videollamada=f'{self.live_server_url}/',
        )
        self.clase = Clase.objects.get(pk=clase.pk)

    def preparar_unidad_por_desbloquear(self):
        """En Metodología, solo el cuestionario separa al alumno de la unidad 2."""
        alumno = Usuario.objects.get(username=datos.ALUMNO_DEMO)
        practica = Contenido.objects.get(
            titulo='Diagramas de secuencia', unidad__catedra__materia__nombre='Metodología de Sistemas II',
        )
        Progreso.objects.update_or_create(
            alumno=alumno, contenido=practica, defaults={'completado_en': timezone.now(), 'intentos': 1},
        )
        Unidad.objects.filter(titulo='Arquitectura en capas').update(fecha_apertura=None)
        self.contenido_bloqueado = Contenido.objects.get(titulo='De MVC a MVT')

    def preparar_respuesta_del_tutor(self):
        """El proveedor falso responde siempre lo mismo: acá le damos una referencia real."""
        material = Contenido.objects.get(titulo='Patrones de comportamiento')
        respuesta = {
            'texto': 'Strategy encapsula algoritmos intercambiables.',
            'referencias': [{'contenido_id': material.id, 'titulo': material.titulo}],
        }
        self.enterContext(patch.dict(ProveedorFalso.RESPUESTAS, {'tutor': respuesta}))

    # Recorrido

    def ingresar(self):
        page = self.page
        page.goto(f'{self.live_server_url}/accounts/login/')
        page.get_by_label('Legajo').fill(datos.ALUMNO_DEMO)
        page.get_by_label('Contraseña').fill(datos.CLAVE)
        page.get_by_role('button', name='Ingresar').click()

    def test_recorrido_completo(self):
        page = self.page

        # CU-01: el hub muestra las cursadas.
        self.ingresar()
        expect(page.get_by_role('heading', name='Mis cursadas')).to_be_visible()
        expect(page.locator('article.cursada')).to_have_count(4)

        # CU-02 y CU-03: ficha de la cursada y avisos de la cátedra.
        page.get_by_role('link', name='Gestión de Desarrollo de Software').first.click()
        expect(page.get_by_role('heading', name='Recorrido')).to_be_visible()
        page.get_by_role('link', name='Ver todos').click()
        expect(page.get_by_text('La clase de hoy también va por Meet')).to_be_visible()

        # CU-04: calendario con filtro.
        page.get_by_role('link', name='Calendario').click()
        page.get_by_role('link', name='Clases', exact=True).click()
        expect(page.get_by_role('link', name='Clases', exact=True)).to_have_attribute('aria-current', 'true')

        # CU-05 y CU-06: la clase de hoy, unirse y quedar con presente.
        page.get_by_role('link', name='Clase de hoy').click()
        expect(page.get_by_role('heading', name=f'Clase {self.clase.numero}: Modelos de proceso')).to_be_visible()
        with self.contexto.expect_event('page') as nueva:
            page.get_by_role('button', name='Unirse a la clase en vivo').click()
        self.assertEqual(nueva.value.url, f'{self.live_server_url}/')
        page.reload()
        expect(page.get_by_text('Presente registrado')).to_be_visible()

        # CU-07: el cuestionario es lo último que le faltaba a la unidad 1.
        page.get_by_role('link', name='Inicio').click()
        page.get_by_role('link', name='Metodología de Sistemas II').first.click()
        expect(page.locator('article.unidad-bloqueada')).to_have_count(1)
        page.get_by_role('link', name='Strategy y Observer').click()
        primera = page.get_by_role('group', name=re.compile(r'^1\.'))
        segunda = page.get_by_role('group', name=re.compile(r'^2\.'))
        primera.get_by_label('Strategy').check()
        segunda.get_by_label('Observer').check()
        page.get_by_role('button', name='Enviar respuestas').click()
        expect(page.get_by_text('Aprobaste con 2 de 2')).to_be_visible()

        # CU-08: el tutor responde y el enlace lleva al material.
        page.get_by_role('button', name='Tutor IA').click()
        page.get_by_placeholder('¿Qué querés repasar?').fill('¿Qué es Strategy?')
        page.get_by_role('button', name='Preguntar').click()
        mensajes = page.locator('.tutor-mensajes')
        expect(mensajes).to_contain_text('Strategy encapsula algoritmos intercambiables.')
        mensajes.get_by_role('link', name='Patrones de comportamiento').click()
        expect(page.get_by_role('heading', name='Patrones de comportamiento')).to_be_visible()

        # Y completar la unidad 1 abrió la 2.
        page.get_by_role('link', name='‹ Metodología de Sistemas II').click()
        expect(page.locator('article.unidad-bloqueada')).to_have_count(0)
        expect(page.locator('article.unidad', has_text='Arquitectura en capas')).to_have_class(
            re.compile(r'unidad-en-curso'),
        )

    def test_contenido_de_unidad_bloqueada(self):
        """Entrar a la URL de un contenido bloqueado no lo muestra: explica qué falta."""
        self.ingresar()
        self.page.goto(f'{self.live_server_url}/contenido/{self.contenido_bloqueado.id}/')
        expect(self.page.get_by_text('todavía está bloqueada')).to_be_visible()
        expect(self.page.get_by_text('Primero completá la')).to_be_visible()
        expect(self.page.get_by_role('button', name='Marcar como leído')).to_have_count(0)
