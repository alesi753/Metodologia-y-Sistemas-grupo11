# Desarrollo

## Instalación manual

Requisitos: Python 3.12+. La base es SQLite (incluida con Python). La IA es opcional.

```bash
git clone https://github.com/alesi753/metodologia-y-sistemas-grupo11.git
cd metodologia-y-sistemas-grupo11
python3 -m venv .venv
source .venv/bin/activate          # fish: activate.fish · PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env               # Windows: copy .env.example .env
python manage.py migrate
python manage.py cargar_demo       # opcional (solo DEBUG=True): cursadas y usuarios de prueba
python manage.py runserver
```

`cargar_demo` imprime los accesos: alumno `50231`, admin `admin-demo`, contraseña `demo1234`.

## Variables de entorno

`config/settings.py` las lee de `.env` (plantilla: [`.env.example`](../.env.example)). Una variable del entorno tiene prioridad sobre el archivo. Nunca versionar claves reales.

| Variable | Por defecto | Uso |
| --- | --- | --- |
| `IA_PROVEEDOR` | `openrouter` | `openrouter`, `anthropic` o `falso` (sin conexión). |
| `OPENROUTER_API_KEY` | — | Clave de [OpenRouter](https://openrouter.ai/settings/keys). |
| `IA_OPENROUTER_MODELO` | `openrouter/free` | Con saldo: `deepseek/deepseek-v4.1-flash`. |
| `ANTHROPIC_API_KEY` | — | Clave de Anthropic, si `IA_PROVEEDOR=anthropic`. |
| `IA_ANTHROPIC_MODELO` | `claude-sonnet-5-5` | Modelo de Anthropic. |
| `SECRET_KEY` | clave insegura local | Obligatoria en producción. |

## Comandos

```bash
python manage.py check && python manage.py test   # validación antes de un PR (sin red; el E2E se saltea si falta Playwright)
python manage.py test aula.test_tutor             # un módulo puntual
python manage.py test --tag=e2e                   # solo el E2E (preparación en testing.md)
python manage.py cargar_demo --reset              # datos de ejemplo desde cero
python manage.py demo_ia --falso                  # los 3 casos de uso de IA por consola
```

Los tests usan una base temporal (no tocan `db.sqlite3`) y `ProveedorFalso` con mocks para correr sin internet.

## Estructura

```text
├── iniciar.bat / .command / .sh  # Lanzadores de doble clic
├── scripts/iniciar.py            # Lógica común de los lanzadores
├── .env.example                  # Plantilla de configuración
├── config/                       # settings.py, urls.py, wsgi.py, asgi.py
├── aula/
│   ├── models.py                 # Dominio y reglas de desbloqueo/progreso
│   ├── admin.py                  # Panel institucional (/admin)
│   ├── decorators.py             # Decorator: @rol_requerido
│   ├── formatos.py               # Strategy: Texto, Cuestionario, Practica
│   ├── signals.py                # Observer: unidad_completada, aviso_publicado
│   ├── views/                    # Una vista por pantalla
│   ├── services/                 # IA (Facade, Adapter, Factory) y tutor
│   ├── templates/ · static/      # HTML, CSS y widget del tutor
│   ├── management/commands/      # cargar_demo, demo_ia
│   └── tests.py · test_*.py      # Suite de tests
└── docs/                         # Documentación
```

## Flujo de trabajo

Cada cambio parte de `develop` en una rama por capa (`infraestructura/`, `backend/`, `frontend/`, `docs/`) y entra por Pull Request con `check` y `test` en verde. Detalle en [plan-de-trabajo.md](plan-de-trabajo.md).
