# Aula Virtual - Grupo 11

Metodología de Sistemas II, TUP 2026. David, Naim, Alejo y Amado.

## Objetivo

Aula virtual donde cada cursada es un recorrido de unidades secuenciales. El alumno avanza cuando completa la unidad anterior y el profesor genera material a partir del programa de su cátedra.

- El profesor sube el PDF del programa y la IA lo convierte en unidades y conceptos.
- Elige conceptos y una perspectiva, la IA sugiere un formato (texto, flashcards, cuestionario o práctica) y arma un borrador para revisar.
- El tutor IA no da respuestas: indica en qué unidad y contenido está el tema.
- Sin notas: el progreso se mide por contenidos completados, en término o fuera de término.

## Stack

| Capa | Elección |
|---|---|
| Backend | Python 3.12+, Django 6.1 |
| Base de datos | SQLite |
| Frontend | Templates de Django |
| IA | Claude (SDK anthropic) |

## Patrones de diseño

Detalle en [docs/decisiones-diseno.md](docs/decisiones-diseno.md).

- Facade: `aula/services/ia_facade.py` concentra el uso de la IA.
- Adapter: traduce respuestas y errores del SDK a tipos propios.
- Strategy: cada formato de contenido define su prompt, template y criterio de completado.
- Decorator: `@rol_requerido` para restringir vistas por rol.
- Observer: signals de Django ante cambios de progreso.

## Instalación

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py seed
python manage.py runserver
```
