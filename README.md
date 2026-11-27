**Aula Virtual — Grupo 11** · Proyecto integrador de **Metodología de Sistemas II** (TUP 2026) · David, Naim, Alejo y Amado.

# ¿Qué es el proyecto?

Aula virtual universitaria organizada como un recorrido secuencial de unidades. El progreso se mide por contenidos completados (en término o fuera de término), sin sistema de notas; parciales y entregas son eventos del calendario. Un tutor IA acompaña al alumno: explica los temas y lo deriva al material donde se estudian.

- **Implementado (Incremento 1 — Alumno, CU-01 a CU-08):** hub de cursadas, ficha y roadmap secuencial, avisos, calendario filtrable, clase del día y asistencia en vivo, contenidos en 3 formatos (`texto`, `cuestionario`, `practica`), unidad *Fe de erratas* fuera de secuencia y widget flotante del Tutor IA contextual.
- **Planificado (Incremento 2 — Profesor, CU-09 a CU-16):** pantallas docentes para importar programas PDF, generar/editar material con IA y seguir el avance (la carga institucional hoy se realiza desde `/admin` y la lógica de IA ya vive en `aula/services/`).

**Stack:** Python 3.12+ · Django 6.1 (MVT + Capa de Servicios + Signals) · SQLite · Templates Django + Pico CSS · OpenRouter / Anthropic.

---

# Cómo levantarlo

## Opción rápida: doble clic (sin saber programar)

Solo hace falta conexión a internet la primera vez. No hay que instalar Python: el lanzador lo prepara solo.

1. **Descargar el aula:** en GitHub, botón verde **Code → Download ZIP**, y descomprimir la carpeta.
2. **Abrir el lanzador** que corresponde a tu sistema:
   - **Windows:** doble clic en `iniciar.bat`.
   - **macOS:** doble clic en `iniciar.command`.
   - **Linux:** abrir una terminal en la carpeta y ejecutar `./iniciar.sh`.
3. **Conectar el tutor IA (solo la primera vez):** el lanzador abre la página oficial de claves de OpenRouter, **<https://openrouter.ai/settings/keys>**. Ahí creás tu cuenta, tocás **Create API Key**, copiás la clave (empieza con `sk-or-`) y la pegás en la ventana del lanzador. La verifica en el momento y la guarda: no te la vuelve a pedir. Si apretás Enter sin pegar nada, el aula funciona igual pero sin IA.
4. **Entrar:** se abre el navegador en `http://127.0.0.1:8000/`. Usuario del alumno de prueba: legajo `50231`, contraseña `demo1234`. En la ventana del lanzador se listan todos los accesos.

Para cerrar el aula, cerrá la ventana del lanzador. Para volver a usarla, abrí el mismo lanzador.

## Instalación manual (desarrollo)

**Requisitos:** Python 3.12+ (con `venv` y `pip`). La base es SQLite, incluida con Python. La IA es opcional: en modo `falso` funciona sin clave ni internet.

```bash
git clone https://github.com/alesi753/metodologia-y-sistemas-grupo11.git
cd metodologia-y-sistemas-grupo11
python3 -m venv .venv
source .venv/bin/activate          # fish: source .venv/bin/activate.fish · PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env               # Windows: copy .env.example .env  → completar OPENROUTER_API_KEY o poner IA_PROVEEDOR=falso
python manage.py migrate
python manage.py cargar_demo       # Opcional (solo DEBUG=True): cursadas y usuarios de prueba
python manage.py runserver
```

`cargar_demo` imprime los accesos disponibles (alumno demo: legajo `50231`, admin: `admin-demo`, contraseña común: `demo1234`).

## Verificación y comandos útiles

```bash
# Validación completa antes de abrir un PR (configuración + 122 tests sin red)
python manage.py check && python manage.py test

# Ejecutar un módulo de tests puntual
python manage.py test aula.test_tutor

# Reiniciar los datos de ejemplo desde cero
python manage.py cargar_demo --reset

# Probar los 3 casos de uso de IA por consola (sin conexión)
python manage.py demo_ia --falso
```

> **Sobre los tests:** Django crea y destruye una base de datos temporal en cada corrida (no modifica `db.sqlite3`) y la suite usa `ProveedorFalso` y mocks para correr sin internet. El mensaje `invalid pdf header: b'esto '` durante la corrida es esperado: corresponde a `test_pdf_sin_texto_es_error` (`aula/test_ia.py`).

## Configuración y variables de entorno

`config/settings.py` las lee del archivo `.env` de la raíz (plantilla: [`.env.example`](.env.example)); una variable definida en el entorno tiene prioridad sobre el archivo. **Nunca versionar claves ni tokens reales:** `.env` está en `.gitignore`.

| Variable | Por defecto | Uso |
| --- | --- | --- |
| `IA_PROVEEDOR` | `openrouter` | Proveedor activo: `openrouter`, `anthropic` o `falso` (sin conexión). |
| `OPENROUTER_API_KEY` | — | Clave de [OpenRouter](https://openrouter.ai/settings/keys) (requerida si `IA_PROVEEDOR=openrouter`). |
| `IA_OPENROUTER_MODELO` | `openrouter/free` | Modelo de OpenRouter (con saldo: `deepseek/deepseek-v4.1-flash`). |
| `ANTHROPIC_API_KEY` | — | Clave de API de Anthropic (requerida si `IA_PROVEEDOR=anthropic`). |
| `IA_ANTHROPIC_MODELO` | `claude-sonnet-5-5` | Modelo de Anthropic. |
| `SECRET_KEY` | clave insegura local | Obligatoria en producción. |

---

# Índice y FAQ

## Estructura del repositorio

```text
├── iniciar.bat / .command / .sh  # Lanzadores de doble clic (Windows / macOS / Linux)
├── scripts/iniciar.py            # Lógica común de los lanzadores: clave de IA, base y servidor
├── .env.example                  # Plantilla de configuración (el .env real no se versiona)
├── manage.py                     # CLI de Django
├── requirements.txt              # Dependencias del proyecto
├── config/                       # Configuración global (settings.py, urls.py, wsgi.py, asgi.py)
├── aula/
│   ├── models.py                 # Entidades de dominio y reglas de desbloqueo/progreso
│   ├── migrations/               # Esquema versionado y grupos de rol (alumno / profesor)
│   ├── admin.py                  # Panel institucional (/admin)
│   ├── decorators.py             # Decorator: @rol_requerido
│   ├── formatos.py               # Strategy: Texto, Cuestionario, Practica y registrar_progreso
│   ├── signals.py + apps.py      # Observer: señales unidad_completada y aviso_publicado (on_commit)
│   ├── views/                    # Vistas HTTP separadas por pantalla (inicio, cursada, calendario, clase, contenido, tutor)
│   ├── services/                 # Lógica desacoplada de HTTP: ia_facade.py, ia_proveedores.py, tutor_service.py
│   ├── templates/ y static/      # Plantillas HTML, CSS y widget JS (tutor.js)
│   ├── management/commands/      # Comandos propios: cargar_demo y demo_ia
│   └── tests.py + test_*.py      # Suite de 122 tests (13 módulos)
└── docs/                         # Decisiones de diseño, plan de trabajo, casos de uso y esquema
```

## Documentación técnica

| Documento | Contenido |
| --- | --- |
| [Decisiones de diseño (ADR)](docs/decisiones-diseno.md) | Patrones aplicados, descartados y sus motivos |
| [Plan de trabajo](docs/plan-de-trabajo.md) | Reglas de ramas y estado de los incrementos |
| [Casos de uso del alumno](docs/casos-de-uso/alumno.md) | Especificación CU-01 a CU-08 y diagrama (`alumno.puml`) |
| [Casos de uso del profesor](docs/casos-de-uso/profesor.md) | Especificación CU-09 a CU-16 y diagrama (`profesor.puml`) |
| [Diagrama de dominio](docs/schemas/schema.mmd) | Modelo de clases en Mermaid |

## Endpoint del Tutor IA

Único endpoint JSON consumido por el widget (`aula/static/aula/tutor.js`), implementado en `aula/views/tutor.py`:

- **Ruta:** `POST /tutor/consultar/` (requiere sesión con rol `alumno`, `Content-Type: application/json` y `X-CSRFToken`).
- **Entrada:** `{"pregunta": "...", "pantalla": "roadmap", "catedra_id": 1}` (`pregunta` obligatoria; IDs opcionales y enteros).
- **Salida (`200 OK`):** `{"texto": "...", "referencias": [{"contenido_id": 4, "titulo": "...", "url": "/contenido/4/"}]}`.
- **Errores:** `400` (JSON o datos inválidos), `403` (rol no autorizado, cátedra ajena Anti-IDOR o borrador), `404` (ID inexistente), `405` (método distinto de `POST`), `503` (fallo del proveedor IA).

## Flujo de trabajo

Todo cambio parte de `develop` en una rama por capa (`infraestructura/`, `backend/`, `frontend/`, `docs/`) y se integra por Pull Request con `python manage.py check && python manage.py test` en verde y documentación actualizada.

## Preguntas frecuentes

**¿Dónde consigo la clave de IA?** En la página oficial de OpenRouter, <https://openrouter.ai/settings/keys>: creás una cuenta, tocás **Create API Key** y copiás la clave. Los modelos gratuitos no requieren cargar saldo.

**¿Cómo cambio la clave o sumo la IA después?** Borrá el archivo `.env` de la carpeta del aula y volvé a abrir el lanzador: te la pide de nuevo. Si sabés editar archivos, también podés cambiar `OPENROUTER_API_KEY` directamente en `.env`.

**¿Dónde queda guardada mi clave?** Solo en el archivo `.env` de tu computadora. No se sube a GitHub (`.gitignore`) y el aula la usa únicamente para hablar con OpenRouter.

**El tutor responde con un error o dice que la respuesta quedó incompleta.** Los modelos gratuitos tienen límites bajos (del orden de 50 consultas por día) y a veces están saturados o cortan la respuesta: volvé a preguntar en un rato. Con unos pocos dólares de saldo en OpenRouter, agregá `IA_OPENROUTER_MODELO=deepseek/deepseek-v4.1-flash` al `.env` para respuestas más estables.

**Windows dice "Windows protegió su PC".** Tocá **Más información → Ejecutar de todas formas**. Pasa con cualquier archivo descargado que no está firmado.

**macOS dice que no puede abrir `iniciar.command`.** Hacé clic derecho sobre el archivo → **Abrir** → **Abrir**. Solo hace falta la primera vez.

**Abrí el lanzador dos veces.** No pasa nada: si el aula ya está abierta, el lanzador solo abre el navegador.

**¿Puedo usar el aula sin IA?** Sí. Apretá Enter sin pegar clave (o poné `IA_PROVEEDOR=falso` en `.env`): todo funciona y el tutor responde con textos de ejemplo.

**Quiero volver a los datos de ejemplo originales.** Con el entorno activado, `python manage.py cargar_demo --reset`.
