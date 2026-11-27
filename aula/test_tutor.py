import json
from datetime import time
from unittest.mock import patch

from django.contrib.auth.models import Group
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Carrera, Catedra, Clase, Contenido, Materia, Unidad, Usuario
from .services.ia_facade import AsistenteIA, ErrorIA
from .services.ia_proveedores import ProveedorFalso
from .services.tutor_service import armar_contexto_pantalla, consultar_tutor_alumno


class TutorBackendTests(TestCase):
    def setUp(self):
        self.alumno = Usuario.objects.create_user('2002', password='clave-segura-123')
        self.alumno.groups.add(Group.objects.get(name='alumno'))
        self.otro_alumno = Usuario.objects.create_user('2003', password='clave-segura-123')
        self.otro_alumno.groups.add(Group.objects.get(name='alumno'))
        self.profesor = Usuario.objects.create_user('3002', password='clave-segura-123')
        self.profesor.groups.add(Group.objects.get(name='profesor'))

        carrera = Carrera.objects.create(nombre='TUP')
        materia = Materia.objects.create(nombre='Legislación', carrera=carrera)
        self.catedra = Catedra.objects.create(materia=materia, anio=2026, cuatrimestre=2)
        self.catedra.alumnos.add(self.alumno)

        self.unidad = Unidad.objects.create(catedra=self.catedra, orden=1, titulo='Constitucional')
        self.contenido = Contenido.objects.create(
            unidad=self.unidad, formato='texto', titulo='Pirámide de Kelsen', publicado=True,
        )
        self.borrador = Contenido.objects.create(
            unidad=self.unidad, formato='texto', titulo='Borrador privado', publicado=False,
        )
        self.clase = Clase.objects.create(
            catedra=self.catedra, numero=1, fecha=timezone.localdate(),
            hora_inicio=time(18, 30), hora_fin=time(20, 30),
            titulo='Introducción', unidad=self.unidad,
        )

    def test_armar_contexto_por_catedra_y_clase_con_url_dinamica(self):
        ctx_curso = armar_contexto_pantalla(self.alumno, 'curso', catedra_id=self.catedra.id)
        self.assertEqual(ctx_curso['url_catedra'], reverse('roadmap', args=[self.catedra.id]))
        self.assertIn('Legislación', ctx_curso['catedra'])

        ctx_clase = armar_contexto_pantalla(self.alumno, 'clase', clase_id=self.clase.id)
        self.assertEqual(ctx_clase['clase']['id'], self.clase.id)
        self.assertEqual(ctx_clase['unidad'], self.unidad.titulo)

    def test_armar_contexto_anti_idor_y_borrador(self):
        with self.assertRaises(PermissionDenied):
            armar_contexto_pantalla(self.otro_alumno, 'curso', catedra_id=self.catedra.id)
        with self.assertRaises(PermissionDenied):
            armar_contexto_pantalla(self.alumno, 'contenido', contenido_id=self.borrador.id)
        with self.assertRaises(Http404):
            armar_contexto_pantalla(self.alumno, 'curso', catedra_id=99999)

    def test_consultar_tutor_resuelve_enlaces_reales_sin_red(self):
        proveedor = ProveedorFalso({
            'tutor': {
                'texto': 'Revisá la jerarquía normativa.',
                'referencias': [{'contenido_id': self.contenido.id, 'titulo': self.contenido.titulo}],
            },
        })
        res = consultar_tutor_alumno(
            self.alumno,
            '¿Qué es la pirámide?',
            pantalla='curso',
            catedra_id=self.catedra.id,
            asistente=AsistenteIA(proveedor),
        )
        self.assertEqual(res.texto, 'Revisá la jerarquía normativa.')
        self.assertEqual(len(res.referencias), 1)
        self.assertEqual(
            res.referencias[0].url,
            f"{reverse('roadmap', args=[self.catedra.id])}#contenido-{self.contenido.id}",
        )

    def test_endpoint_tutor_control_acceso_errores_y_exito(self):
        url = reverse('tutor_consultar')

        # Profesor no autorizado -> 403
        self.client.force_login(self.profesor)
        r_prof = self.client.post(url, data=json.dumps({'pregunta': 'Hola'}), content_type='application/json')
        self.assertEqual(r_prof.status_code, 403)

        # Alumno autenticado
        self.client.force_login(self.alumno)

        # Pregunta vacía -> 400
        r_vacia = self.client.post(url, data=json.dumps({'pregunta': '   '}), content_type='application/json')
        self.assertEqual(r_vacia.status_code, 400)

        # Recurso inexistente -> 404
        r_404 = self.client.post(
            url, data=json.dumps({'pregunta': 'Hola', 'catedra_id': 99999}), content_type='application/json',
        )
        self.assertEqual(r_404.status_code, 404)

        # Error de proveedor IA -> 503
        with patch('aula.services.tutor_service.AsistenteIA.consultar_tutor', side_effect=ErrorIA('caído')):
            r_503 = self.client.post(
                url, data=json.dumps({'pregunta': 'Hola'}), content_type='application/json',
            )
        self.assertEqual(r_503.status_code, 503)

        # Éxito con ProveedorFalso -> 200
        proveedor = ProveedorFalso({
            'tutor': {
                'texto': 'Respuesta OK',
                'referencias': [{'contenido_id': self.contenido.id, 'titulo': self.contenido.titulo}],
            },
        })
        with patch('aula.services.tutor_service.AsistenteIA', return_value=AsistenteIA(proveedor)):
            r_ok = self.client.post(
                url,
                data=json.dumps({'pregunta': 'Explicame', 'catedra_id': self.catedra.id}),
                content_type='application/json',
            )
        self.assertEqual(r_ok.status_code, 200)
        body = r_ok.json()
        self.assertEqual(body['texto'], 'Respuesta OK')
        self.assertEqual(
            body['referencias'][0]['url'],
            f"{reverse('roadmap', args=[self.catedra.id])}#contenido-{self.contenido.id}",
        )
