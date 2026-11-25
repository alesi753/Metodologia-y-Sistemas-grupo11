from django.contrib.auth.models import AnonymousUser, Group
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.test import RequestFactory, TestCase

from .decorators import rol_requerido
from .models import Usuario


@rol_requerido('profesor')
def vista_profesor(request):
    return HttpResponse('ok')


class RolRequeridoTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.profe = Usuario.objects.create_user('profe', password='x')
        self.profe.groups.add(Group.objects.get_or_create(name='profesor')[0])
        self.alumno = Usuario.objects.create_user('ana', password='x')
        self.alumno.groups.add(Group.objects.get_or_create(name='alumno')[0])

    def pedir(self, usuario):
        request = self.factory.get('/')
        request.user = usuario
        return vista_profesor(request)

    def test_rol_correcto_pasa(self):
        self.assertEqual(self.pedir(self.profe).status_code, 200)

    def test_rol_incorrecto_da_403(self):
        with self.assertRaises(PermissionDenied):
            self.pedir(self.alumno)

    def test_sin_sesion_redirige_al_login(self):
        self.assertEqual(self.pedir(AnonymousUser()).status_code, 302)