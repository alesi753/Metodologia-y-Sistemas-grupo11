# Aula Virtual - Grupo 11

Metodología de Sistemas II, TUP 2026. David, Naim, Alejo y Amado.

## Objetivo

Aula virtual donde cada cursada es un recorrido de unidades secuenciales. El alumno avanza cuando completa la unidad anterior y el profesor genera material a partir del programa de su cátedra.

- El profesor sube el PDF del programa y la IA lo convierte en unidades y conceptos.
- Elige conceptos y una perspectiva, la IA sugiere un formato (texto, cuestionario o práctica) y arma un borrador para revisar.
- El alumno sigue su cursada desde un inicio con sus materias, próximas fechas, clases y avisos de la cátedra.
- El tutor IA explica el tema en general y enlaza el material donde se estudia. No resuelve actividades.
- Sin notas: el progreso se mide por contenidos completados, en término o fuera de término. Parciales y entregas son fechas del calendario.

## Stack

| Capa | Elección |
|---|---|
| Backend | Python 3.12+, Django 6.1 |
| Base de datos | SQLite |
| Frontend | Templates de Django |
| IA | Claude (SDK anthropic) |

## Documentación

| Documento | Para qué sirve |
|---|---|
| [Plan de trabajo](docs/plan-de-trabajo.md) | Ramas del incremento actual, en qué orden van y cómo trabajamos con git |
| [Decisiones de diseño](docs/decisiones-diseno.md) | Patrones de diseño: cuáles aplicamos, cuáles faltan y cuáles descartamos |
| [Casos de uso del alumno](docs/casos-de-uso/alumno.md) | Diagrama y especificación de lo que hace el alumno |
| [Schema](docs/schemas/schema.mmd) | Diagrama de clases del dominio |

## Instalación

```bash
python -m venv .venv
source .venv/bin/activate        # en fish: source .venv/bin/activate.fish
pip install -r requirements.txt
export ANTHROPIC_API_KEY=tu-clave
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Tests: `python manage.py test`
