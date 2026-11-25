from functools import wraps

from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied


def rol_requerido(*roles):
    def decorador(vista):
        @wraps(vista)
        def envuelta(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect_to_login(request.get_full_path())
            if not request.user.groups.filter(name__in=roles).exists():
                raise PermissionDenied
            return vista(request, *args, **kwargs)
        return envuelta
    return decorador