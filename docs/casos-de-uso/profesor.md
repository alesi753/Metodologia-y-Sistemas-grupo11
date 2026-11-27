# Casos de uso: Profesor

Fuente editable del diagrama: [profesor.puml](profesor.puml). Para generar el SVG: `java -jar plantuml.jar -tsvg docs/casos-de-uso/profesor.puml` (queda en `profesor.svg`, junto al del alumno).

Precondición común: el profesor inició sesión, pertenece al grupo `profesor` y solo opera sobre las cátedras que tiene a cargo (`Catedra.profesores`). Una cátedra ajena responde 404, igual que una cursada ajena para el alumno.

| CU | Nombre | Pantalla | Qué resuelve | Modelos que usa | Patrón |
|---|---|---|---|---|---|
| CU-09 | Consultar cátedras a cargo | Inicio | Cada cátedra con su avance general, los borradores pendientes de revisar y las próximas clases y fechas | `Catedra`, `Contenido`, `Progreso`, `Clase`, `Evento` | Decorator (rol y cátedra a cargo) |
| CU-10 | Importar el programa | Programa | Subir el PDF del programa; la IA propone unidades y conceptos, el profesor los revisa y confirma | `Catedra`, `Unidad` | Facade + Adapter |
| CU-11 | Generar contenido con IA | Generar contenido | Elegir unidad, conceptos y perspectiva; la IA sugiere el formato y arma un borrador | `Unidad`, `Contenido` | Facade + Adapter, Strategy (validación del borrador) |
| CU-12 | Revisar y publicar contenido | Contenidos de la cátedra | Editar un borrador con el formulario de su formato y publicarlo; corregir lo ya publicado | `Contenido`, `Unidad` | Strategy (un formulario por formato), Observer |
| CU-13 | Cargar el cronograma de clases | Clases | Generar las clases del cuatrimestre a partir de los horarios y completar temario, link y material de cada una | `Horario`, `Clase`, `Contenido` | — |
| CU-14 | Cargar fechas importantes | Fechas | Parciales, entregas, presentaciones y finales del calendario | `Evento` | — |
| CU-15 | Publicar un aviso | Avisos | Comunicar algo a los inscriptos, en el momento o programado | `Aviso` | Observer (notifica a los inscriptos) |
| CU-16 | Seguir el progreso | Progreso de la cátedra | Por alumno y unidad: completados, en término o fuera de término, intentos, entregas y asistencia | `Progreso`, `Asistencia`, `Unidad` | — |

Ninguno necesita modelos nuevos para funcionar. Solo CU-13 pide un cambio de esquema (ver [Impacto en el esquema](#impacto-en-el-esquema)).

## Flujo principal de CU-10 (Importar el programa)

1. El profesor abre la pantalla Programa de una cátedra a cargo y sube el PDF.
2. El sistema guarda el archivo en `Catedra.programa_archivo` y se lo pasa a `AsistenteIA.importar_programa`.
3. La IA devuelve las unidades propuestas, cada una con sus conceptos.
4. El sistema muestra la propuesta en un formulario editable: el profesor corrige títulos, quita o agrega conceptos y unidades, y define las fechas de apertura y límite.
5. El profesor confirma y el sistema crea las `Unidad` en ese orden y guarda la propuesta original en `Catedra.programa`.

Alternativos:
- **3a. La IA no está disponible o la respuesta no es válida:** el Adapter traduce el error (`ErrorIA`), el PDF queda guardado y el profesor puede reintentar o cargar las unidades a mano.
- **5a. La cátedra ya tiene unidades:** las nuevas se agregan al final. Una unidad que algún alumno ya empezó no se borra ni se reordena.

## Flujo principal de CU-11 y CU-12 (Generar, revisar y publicar)

1. El profesor elige una unidad, marca los conceptos que quiere cubrir y escribe la perspectiva (por ejemplo: "con un caso real de una pyme", "para repasar antes del parcial").
2. El sistema llama a `AsistenteIA.generar_contenido`. La IA sugiere el formato (texto, cuestionario o práctica) y devuelve un borrador validado por la estrategia de ese formato.
3. El sistema guarda el borrador como `Contenido` sin publicar, con el profesor como autor.
4. El profesor lo revisa en el formulario de su formato (secciones; preguntas con opciones y correcta; consigna, entregables y formatos aceptados) y lo edita. Puede cambiar el formato antes de publicar.
5. El profesor publica. Desde ese momento el contenido cuenta para el recorrido de los alumnos.

Alternativos:
- **2a. La IA no está disponible:** el profesor puede crear el contenido vacío del formato que elija y escribirlo a mano.
- **4a. El cuerpo no es válido para el formato:** la estrategia (`Formato.validar`) rechaza el guardado y el formulario indica qué falta.
- **5a. La unidad ya fue completada por algún alumno:** publicar ahí lo volvería a bloquear. El sistema ofrece publicarlo en la unidad *Fe de erratas* de la cátedra, que referencia la unidad corregida (decisión 3 de producto).
- **5b. Despublicar:** un contenido con progreso registrado no se despublica ni se borra; se corrige con una fe de erratas.

## Flujo principal de CU-13 (Cargar el cronograma de clases)

1. El profesor abre Clases de una cátedra que tiene horarios cargados.
2. El sistema propone una clase por cada bloque de horario entre el inicio y el fin del cuatrimestre, numeradas en orden.
3. El profesor quita las que no corresponden (feriados, semanas de parciales) y confirma.
4. En cada clase completa título, temario, unidad, link de videollamada y el material y las tareas que se ven ese día.

Alternativos:
- **2a. La cátedra ya tiene clases:** solo se proponen fechas nuevas, sin duplicar las existentes.

## Impacto en el esquema

| Concepto | Propuesta | Motivo |
|---|---|---|
| Fechas del cuatrimestre | `inicio` y `fin` en `Catedra` | CU-13 necesita saber entre qué fechas generar las clases. Hoy el calendario del alumno supone marzo a julio y agosto a diciembre (`MESES_CUATRIMESTRE` en `aula/views/calendario.py`); con estos campos esa suposición desaparece |

## Decisiones a confirmar con el grupo

1. **Perspectiva:** texto libre con algunas sugerencias, o una lista cerrada de opciones.
2. **Edición de contenido publicado:** si un contenido sin progreso registrado se puede editar directamente, o toda corrección va a la fe de erratas.
3. **Respuestas de los cuestionarios:** si el profesor ve qué respondió cada alumno o solo si aprobó y en cuántos intentos. Coherente con "sin notas", se propone lo segundo.
4. **Notificaciones de avisos:** si el receptor de `aviso_publicado` manda un mail (en desarrollo, a la consola) o queda para un incremento posterior. Además, hoy la señal sale al crear el aviso aunque esté programado para más adelante; habría que emitirla recién en `publicado_en`.
5. **Admin de Django:** queda para el personal institucional (carreras, materias, cátedras, inscripciones). El profesor trabaja solo desde sus pantallas.
