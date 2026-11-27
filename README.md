**Aula Virtual — Grupo 11** · Metodología de Sistemas II (TUP 2026) · David, Naim, Alejo y Amado.

# ¿Qué es el proyecto?

Aula virtual universitaria: cada cursada es un recorrido de unidades que se desbloquean al completar contenidos. No pone notas; parciales y entregas son fechas del calendario. Un tutor IA explica los temas y deriva al material donde se estudian.

- **Incremento 1 — alumno (implementado):** cursadas, roadmap, avisos, calendario, clase en vivo con asistencia, contenidos (texto, cuestionario, práctica) y tutor IA.
- **Incremento 2 — profesor (planificado):** importar programas en PDF, generar material con IA y seguir el avance.

**Stack:** Python 3.12+ · Django 6.1 · SQLite · Pico CSS · OpenRouter / Anthropic.

# Cómo levantar la demo

1. Descargá el ZIP (**Code → Download ZIP**) y descomprimilo.
2. Abrí `iniciar.bat` (Windows), `iniciar.command` (macOS) o `./iniciar.sh` (Linux). Python se instala solo.
3. La primera vez se abre <https://openrouter.ai/settings/keys>: creá una clave y pegala en la ventana. Enter vacío = aula sin IA.
4. Entrá en `http://127.0.0.1:8000/` con legajo `50231` y contraseña `demo1234`.

Para cerrar el aula, cerrá la ventana. Instalación manual y comandos de desarrollo: [docs/desarrollo.md](docs/desarrollo.md).

# Índice y FAQ

| Tema | Documento |
| --- | --- |
| Instalación manual, variables, tests y estructura | [docs/desarrollo.md](docs/desarrollo.md) |
| Decisiones de diseño y patrones | [docs/decisiones-diseno.md](docs/decisiones-diseno.md) |
| Plan de trabajo e incrementos | [docs/plan-de-trabajo.md](docs/plan-de-trabajo.md) |
| Casos de uso del alumno y del profesor | [alumno.md](docs/casos-de-uso/alumno.md) · [profesor.md](docs/casos-de-uso/profesor.md) |
| Modelo de dominio | [docs/schemas/schema.mmd](docs/schemas/schema.mmd) |
| Endpoint del tutor IA | [docs/api-tutor.md](docs/api-tutor.md) |
| Problemas frecuentes | [docs/faq.md](docs/faq.md) |

- **¿Cómo cambio la clave de IA?** Borrá `.env` y volvé a abrir el lanzador. → [FAQ](docs/faq.md#clave-de-ia)
- **El tutor da error.** Los modelos gratuitos tienen límites; reintentá. → [FAQ](docs/faq.md#el-tutor-da-error)
- **Windows o macOS no me deja abrir el lanzador.** → [FAQ](docs/faq.md#avisos-de-seguridad)
- **¿Cómo vuelvo a los datos de ejemplo?** → [FAQ](docs/faq.md#datos-de-ejemplo)
