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
export OPENROUTER_API_KEY=tu-clave   # o IA_PROVEEDOR=anthropic + ANTHROPIC_API_KEY
python manage.py migrate
python manage.py cargar_demo     # opcional: cursada de ejemplo; al final muestra usuarios y URLs
python manage.py createsuperuser
python manage.py runserver
```

### IA

El servicio de IA se elige con la variable `IA_PROVEEDOR`:

| Valor | Clave | Para qué |
|---|---|---|
| `openrouter` (por defecto) | `OPENROUTER_API_KEY` (gratis en openrouter.ai) | Desarrollo y demos. Por defecto usa modelos gratuitos (`openrouter/free`); con saldo cargado conviene `IA_OPENROUTER_MODELO=deepseek/deepseek-v4.1-flash`. |
| `anthropic` | `ANTHROPIC_API_KEY` (cuenta de API, no sirve un plan Pro) | Instalación con cuenta propia. Modelo en `IA_ANTHROPIC_MODELO` (por defecto `claude-sonnet-5-5`). |
| `falso` | — | Respuestas fijas sin conexión. |

El detalle de modelos y esfuerzo por tarea está en `config/settings.py`.

Tests: `python manage.py test`

Demo de la IA: `python manage.py demo_ia` prueba importar un programa, generar contenido y consultar al tutor. Usa el proveedor de `IA_PROVEEDOR` (o `--proveedor`); si falta su clave, o con `--falso`, usa respuestas fijas sin conexión. Con `--pdf ruta` importa un programa propio.
