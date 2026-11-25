# Decisiones de diseño - Aula Virtual

Registro de decisiones del grupo para Metodología de Sistemas II. Aplicamos un patrón solo cuando resuelve un problema concreto del producto, y cada uno indica en qué estado está realmente en el código:

- **Aplicado:** ya está en el repo.
- **Planificado:** decidido, con la rama que lo implementa (ver [plan de trabajo](plan-de-trabajo.md)).
- **Descartado:** evaluado y rechazado, con el motivo.

## Resumen

| Patrón | Tipo | Estado | Dónde | Rama |
|---|---|---|---|---|
| Facade | Estructural | Aplicado | `aula/services/ia_facade.py` | `backend/ia-facade` |
| Adapter | Estructural | Aplicado | `aula/services/ia_proveedores.py` | `backend/ia-facade` |
| Decorator | Estructural | Planificado | `aula/decorators.py` | `backend/rol-requerido` |
| Strategy | Comportamiento | Aplicado | `aula/formatos.py` | `backend/formatos-contenido` |
| Observer | Comportamiento | Planificado | `aula/signals.py` | `backend/observer` |
| Command | Comportamiento | Descartado | — | — |
| Factory (simple) | Creacional | Aplicado | `aula/services/ia_proveedores.py` | `backend/ia-facade` |
| Builder, Singleton | Creacionales | Descartados | — | — |

---

## 1. Patrones estructurales

### 1.1. Facade

- **Estado:** aplicado en `AsistenteIA` (`aula/services/ia_facade.py`).
- **Problema:** la IA se usa en dos lugares muy distintos. Para el profesorado genera contenido a partir del programa de la materia; para el alumno funciona como tutor. En los dos casos hay que armar el pedido, llamar a la API y manejar errores. Si eso queda en las vistas, cada vista termina sabiendo cómo funciona la IA.
- **Decisión:** una sola clase, `AsistenteIA`, con un método por cada cosa que el producto necesita: importar el programa (`importar_programa`), generar un contenido (`generar_contenido`) y responder una consulta del tutor (`consultar_tutor`). Las vistas solo llaman a esos métodos. La fachada no guarda nada: devuelve borradores, valida que la respuesta tenga la forma esperada y descarta referencias del tutor a contenido que el alumno no puede ver.
- **Beneficio:** si cambia cómo le pedimos las cosas a la IA, se toca un solo archivo.

### 1.2. Adapter

- **Estado:** aplicado. La interfaz es `ProveedorIA` y hay tres adaptadores en `aula/services/ia_proveedores.py`.
- **Problema:** cada servicio de IA tiene su propio SDK, con sus tipos de respuesta, sus errores y sus parámetros. Además, no todos aceptan lo mismo: Claude lee un PDF entero, mientras que los modelos gratuitos de OpenRouter solo reciben texto. No queremos que nada de eso se filtre al resto del sistema.
- **Decisión:** la fachada pide siempre lo mismo (una tarea, instrucciones, un mensaje, la forma del JSON esperado y, si hace falta, un PDF) y cada adaptador lo traduce a su servicio:
  - `AnthropicAdapter`: Claude con el SDK de Anthropic. Manda el PDF tal cual y ajusta cuánto razona el modelo según la tarea.
  - `OpenRouterAdapter`: modelos de OpenRouter con el SDK de OpenAI, que es compatible. Extrae el texto del PDF antes de mandarlo y elige el modelo según la tarea.
  - `ProveedorFalso`: respuestas fijas sin conexión, para tests y demos.

  Cualquier error del servicio, JSON inválido o respuesta cortada sale como `ErrorIA`, el único error de IA que conoce el resto del sistema.
- **Beneficio:** sumar o cambiar de servicio de IA no toca la fachada ni las vistas, y los tests corren sin red.

### 1.3. Decorator

- **Estado:** aplicado en parte. Hoy las vistas usan `@login_required`, que solo verifica que haya sesión. Falta controlar el rol.
- **Problema:** alumno y profesor ven pantallas distintas. Validar el rol adentro de cada vista repite código y mezcla la seguridad con la lógica de la pantalla.
- **Decisión:** un decorador propio, `@rol_requerido('profesor')`, que envuelve la vista y corta el acceso antes de que se ejecute. Elegimos uno propio en lugar de `@user_passes_test` suelto para tener una sola regla de roles en un solo lugar.
- **Beneficio:** cada vista queda con una única responsabilidad, y la regla de roles se cambia en un solo archivo.

---

## 2. Patrones de comportamiento

### 2.1. Strategy

- **Estado:** aplicado en `aula/formatos.py`. Hay una estrategia por formato (`Texto`, `Cuestionario`, `Practica`) y `Contenido.estrategia` elige la que corresponde según su campo `formato`. `registrar_progreso` usa la estrategia para decidir cuándo se completa un contenido.
- **Problema:** un contenido puede ser un texto, un cuestionario o una práctica para entregar. Cada formato se muestra distinto, guarda datos distintos y se completa por motivos distintos: el texto al marcarlo como leído, el cuestionario al aprobarlo y la práctica al entregar el archivo. Resolverlo con `if/elif` por formato lo desparrama por todo el sistema.
- **Decisión:** una estrategia por formato que define su template, cómo valida su contenido y cuándo se considera completo. El modelo `Contenido` elige la estrategia según su campo `formato`.
- **Beneficio:** agregar un formato nuevo es agregar una clase, sin tocar las que ya funcionan.

### 2.2. Observer

- **Estado:** planificado. `aula/signals.py` existe pero está vacío.
- **Problema:** cuando un alumno completa un contenido o la cátedra publica un aviso, pasan cosas secundarias, como avisarle que se desbloqueó la unidad siguiente o notificar a los inscriptos. Esas reacciones no deberían frenar ni ensuciar el guardado.
- **Decisión:** usar signals de Django (`post_save`). El modelo guarda y emite el evento; los receptores reaccionan cada uno por su lado.
- **Beneficio:** sumar una reacción nueva no obliga a tocar el código que guarda.

### 2.3. Command

- **Estado:** descartado.
- **Motivo:** las acciones del aula (entregar, completar, registrar asistencia) son pedidos simples que se resuelven en el momento. No hay colas, reintentos ni deshacer que justifiquen convertirlas en objetos.

---

## 3. Patrones creacionales

### 3.1. Factory (simple)

- **Estado:** aplicado en `crear_proveedor` (`aula/services/ia_proveedores.py`).
- **Problema:** qué servicio de IA usar depende de dónde se instala el sistema: el grupo desarrolla con modelos gratuitos y una institución usaría su propia cuenta. Si cada parte del código eligiera la clase a mano, cambiar de servicio obligaría a tocar varios archivos.
- **Decisión:** una función lee `IA_PROVEEDOR` (`openrouter`, `anthropic` o `falso`) y devuelve el adaptador que corresponde, a partir de un registro de nombre → clase. `AsistenteIA` la usa cuando no le pasan un proveedor.
- **Beneficio:** cambiar de servicio es cambiar una variable de entorno, y sumar uno nuevo es escribir su adaptador y agregar una línea al registro.

### 3.2. Descartados

- **Motivo general:** el ORM de Django ya centraliza la creación y la persistencia de las entidades. Crear objetos directamente es simple y suficiente.
- **Factory para contenidos:** `Contenido` es un solo modelo con un campo `formato`. No hay subclases entre las que elegir; la variación por formato la resuelve Strategy.
- **Builder:** ninguna entidad se arma en varios pasos complejos.
- **Singleton:** Django ya maneja los recursos globales, como la conexión a la base. Hacerlo a mano agrega estado oculto y complica los tests.

---

## 4. Lo que resuelve el framework

- **Panel de administración (aplicado):** la carga de datos institucionales y de cada cursada se hace desde `aula/admin.py`, sin escribir formularios propios.
- **Roles con grupos de Django (aplicado):** `Alumno` y `Profesor` son vistas sobre el mismo `Usuario`, filtradas por el grupo al que pertenecen. Sirve de base para el Decorator de roles.
- **Herencia de templates (aplicado):** todas las pantallas extienden un template base con la navegación común.

---

## 5. Decisiones de producto

Afectan el diseño, así que quedan registradas acá. El detalle está en los [casos de uso del alumno](casos-de-uso/alumno.md).

1. **Sin calificaciones.** Parciales, entregas, presentaciones y finales son fechas del calendario (`Evento`). La plataforma mide progreso, no pone notas.
2. **Alcance del tutor.** Explica el tema en general y enlaza el material donde se estudia. No resuelve cuestionarios ni prácticas.
3. **Fe de erratas.** Si la cátedra corrige contenido de una unidad que el alumno ya completó, la corrección va a una unidad aparte que no bloquea el recorrido.
4. **Tres formatos de contenido:** texto, cuestionario y práctica. Las flashcards se descartaron porque aportaban poco frente a los otros dos.
5. **Proveedor de IA.** El sistema no depende de un servicio de IA en particular:
   - **Desarrollo y demos:** OpenRouter con modelos gratuitos (`openrouter/free`, que elige entre los disponibles). Tienen límites de uso bajos (del orden de 50 pedidos por día por cuenta) y algunos pueden guardar los pedidos. Con poco saldo cargado, DeepSeek V4.1 Flash da mejor calidad a un costo muy bajo.
   - **Instalación real:** el servicio lo define la institución que la instala, con su propia cuenta de API, por ejemplo Anthropic. Así las consultas de los alumnos no pasan por modelos gratuitos.
   - **Suscripciones personales:** planes como Claude Pro no sirven para esto, porque no incluyen acceso a la API.
