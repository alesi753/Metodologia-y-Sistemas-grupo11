"""Strategy: cada formato de contenido define cómo se valida y cuándo se completa."""
from django.core.exceptions import ValidationError
from django.utils import timezone


class Formato:
    template = ''
    cuenta_intentos = False

    def validar(self, cuerpo):
        """Lanza ValidationError si el cuerpo no tiene la forma esperada."""

    def esta_completo(self, progreso, datos, archivo):
        raise NotImplementedError


class Texto(Formato):
    template = 'aula/contenido/texto.html'

    def validar(self, cuerpo):
        secciones = cuerpo.get('secciones')
        if not isinstance(secciones, list) or not secciones:
            raise ValidationError('El texto necesita al menos una sección.')
        for s in secciones:
            if not isinstance(s, dict) or not s.get('titulo') or not s.get('texto'):
                raise ValidationError('Cada sección necesita título y texto.')

    def esta_completo(self, progreso, datos, archivo):
        return True  # se completa al marcarlo como leído


class Cuestionario(Formato):
    template = 'aula/contenido/cuestionario.html'
    cuenta_intentos = True

    def validar(self, cuerpo):
        aprobacion = cuerpo.get('aprobacion')
        if not isinstance(aprobacion, (int, float)) or not 0 < aprobacion <= 1:
            raise ValidationError('La aprobación tiene que estar entre 0 y 1.')
        preguntas = cuerpo.get('preguntas')
        if not isinstance(preguntas, list) or not preguntas:
            raise ValidationError('El cuestionario necesita al menos una pregunta.')
        for p in preguntas:
            opciones = p.get('opciones') if isinstance(p, dict) else None
            if not p.get('enunciado') or not isinstance(opciones, list) or len(opciones) < 2:
                raise ValidationError('Cada pregunta necesita enunciado y al menos dos opciones.')
            correcta = p.get('correcta')
            if not isinstance(correcta, int) or not 0 <= correcta < len(opciones):
                raise ValidationError('Cada pregunta necesita una opción correcta válida.')

    def esta_completo(self, progreso, datos, archivo):
        cuerpo = progreso.contenido.cuerpo
        preguntas = cuerpo.get('preguntas', [])
        respuestas = datos.get('respuestas', [])
        progreso.respuesta = {'respuestas': respuestas}
        aciertos = sum(1 for p, r in zip(preguntas, respuestas) if p['correcta'] == r)
        return bool(preguntas) and aciertos / len(preguntas) >= cuerpo.get('aprobacion', 0.6)


class Practica(Formato):
    template = 'aula/contenido/practica.html'
    cuenta_intentos = True

    def validar(self, cuerpo):
        if not cuerpo.get('consigna'):
            raise ValidationError('La práctica necesita una consigna.')
        entregables = cuerpo.get('entregables')
        if not isinstance(entregables, list) or not all(isinstance(e, str) for e in entregables):
            raise ValidationError('Los entregables tienen que ser una lista de textos.')
        if not isinstance(cuerpo.get('formatos_aceptados'), str):
            raise ValidationError('Faltan los formatos aceptados.')

    def esta_completo(self, progreso, datos, archivo):
        if archivo is None:
            return False
        progreso.archivo = archivo
        return True  # se completa al entregar el archivo


ESTRATEGIAS = {
    'texto': Texto(),
    'cuestionario': Cuestionario(),
    'practica': Practica(),
}


def registrar_progreso(alumno, contenido, datos=None, archivo=None):
    """Registra un intento del alumno.

    Guarda con save() (no update()) para que el observer de progreso se entere.
    """
    from .models import Progreso

    progreso, _ = Progreso.objects.get_or_create(alumno=alumno, contenido=contenido)
    if progreso.completado_en:
        return progreso  # una vez completado, no se reabre
    estrategia = contenido.estrategia
    if estrategia.cuenta_intentos:
        progreso.intentos += 1
    if estrategia.esta_completo(progreso, datos or {}, archivo):
        progreso.completado_en = timezone.now()
    progreso.save()
    return progreso