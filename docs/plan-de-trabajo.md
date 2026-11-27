# Plan de trabajo

## Cómo trabajamos

- Todo sale de `develop` y vuelve a `develop` por PR. `main` solo recibe versiones cerradas.
- Una rama por tema, con prefijo según la capa: `infraestructura/`, `backend/`, `frontend/` o `docs/`.
- Cada PR deja los tests pasando y, si cambia una decisión, actualiza [decisiones-diseno.md](decisiones-diseno.md).
- Las migraciones se crean solo en ramas `infraestructura/`. Si una rama de backend o frontend necesita un campo nuevo, se pide ahí. Así evitamos dos migraciones con el mismo número.
- Antes de empezar una rama, anotá tu nombre al lado en esta lista. Al mergear, marcala como hecha.

## Incremento 1: perspectiva del alumno

Objetivo: que el alumno pueda seguir su cursada completa. Los casos de uso están en [casos-de-uso/alumno.md](casos-de-uso/alumno.md).

Las ramas en **negrita** bloquean a las que vienen después. El resto se puede trabajar en paralelo una vez cumplido lo que indica cada una.

### docs/
- [x] `docs/casos-de-uso-alumno`: diagrama y especificación del alumno.
- [x] `docs/adr-actualizacion`: decisiones de diseño al día, README y este plan.

### infraestructura/
- [x] **`infraestructura/schema-alumno`**: modelos nuevos (horarios, clases, asistencia, eventos, avisos, fe de erratas) y su carga desde el admin.
- [x] `infraestructura/datos-demo`: grupos alumno y profesor, comando para cargar datos de ejemplo y archivos subidos en desarrollo. *Después de `schema-alumno`.*

### backend/
- [x] `backend/rol-requerido`: Decorator para restringir vistas por rol. *Después de `schema-alumno`.*
- [x] `backend/formatos-contenido`: Strategy por formato y registro del progreso. *Después de `schema-alumno`.*
- [x] `backend/observer`: reacciones al completar contenido y al publicar avisos. *Después de `formatos-contenido`.*
- [x] `backend/ia-facade`: Facade y Adapter de la IA, con un proveedor falso para tests. *Se puede empezar ya.*
- [x] `backend/tutor`: consulta al tutor con el contexto de la pantalla y enlaces al material. *Después de `ia-facade`.*

### frontend/
Cada rama de pantalla incluye su vista y su template.

- [x] **`frontend/base-navegacion`** (Amado): estructura común (encabezado, navegación inferior y lugar para el tutor). *Después de `rol-requerido`.*
- [x] `frontend/hub` (Amado): inicio con cursadas, próximas fechas y avisos (CU-01). *Después de `base-navegacion`.*
- [x] `frontend/curso-avisos` (Amado): ficha del curso, unidades y avisos (CU-02, CU-03). *Después de `base-navegacion`.*
- [x] `frontend/calendario` (Amado): clases y fechas del mes con filtro (CU-04). *Después de `base-navegacion`.*
- [x] `frontend/clase` (Amado): clase del día, link en vivo y asistencia (CU-05, CU-06). *Después de `base-navegacion`.*
- [x] `frontend/contenido` (Amado): un template por formato (CU-07). *Después de `formatos-contenido` y `base-navegacion`.*
- [x] `frontend/tutor-widget` (Amado): botón y panel del tutor (CU-08). *Después de `tutor` y `base-navegacion`.*

## Incremento 2: perspectiva del profesorado

Objetivo: que el profesor arme y siga su cátedra sin pasar por el admin: importar el programa, generar contenido con IA, revisarlo y publicarlo, cargar clases, fechas y avisos, y seguir el progreso. Los casos de uso están en [casos-de-uso/profesor.md](casos-de-uso/profesor.md).

Las pantallas del profesor van en `aula/views/` como las del alumno, un módulo por pantalla. Las rutas del profesor cuelgan de `catedra/<id>/` para no mezclarse con las del alumno (`cursada/<id>/`).

### docs/
- [ ] `docs/casos-de-uso-profesor`: diagrama y especificación del profesor, y este plan.

### infraestructura/
- [ ] `infraestructura/fechas-cursada`: `inicio` y `fin` en `Catedra`, en el admin y en los datos de la demo. El calendario del alumno deja de suponer los meses del cuatrimestre.

### backend/
- [ ] **`backend/catedra-a-cargo`**: restringir las vistas del profesor a sus cátedras (decorator o helper junto a `rol_requerido`) y menú del profesor en la navegación.
- [ ] **`backend/edicion-formatos`**: cada estrategia de `aula/formatos.py` suma su formulario de edición, que arma y valida el `cuerpo`. *Lo usan la generación y la revisión de contenido.*
- [ ] `backend/fe-de-erratas`: publicar en una unidad ya completada por algún alumno manda el contenido a la fe de erratas de la cátedra (la crea si no existe). *Después de `edicion-formatos`.*
- [ ] `backend/notificar-avisos`: receptor de `aviso_publicado` que avisa a los inscriptos (mail por consola en desarrollo) y emisión de la señal recién al llegar `publicado_en`. *Según la decisión 4 de los casos de uso.*

### frontend/
Cada rama de pantalla incluye su vista y su template. Todas van *después de `catedra-a-cargo`*.

- [ ] `frontend/profesor-hub`: inicio con cátedras a cargo, avance, borradores pendientes y próximas fechas (CU-09).
- [ ] `frontend/importar-programa`: subir el PDF, revisar las unidades propuestas y confirmarlas (CU-10).
- [ ] `frontend/contenidos-catedra`: listado de contenidos, generar con IA, editar y publicar (CU-11, CU-12). *Después de `edicion-formatos`; la publicación en fe de erratas, después de `fe-de-erratas`.*
- [ ] `frontend/profesor-clases`: generar el cronograma desde los horarios y editar cada clase (CU-13). *Después de `fechas-cursada`.*
- [ ] `frontend/fechas-avisos`: fechas importantes y avisos de la cátedra (CU-14, CU-15).
- [ ] `frontend/seguimiento`: progreso por alumno y unidad, entregas y asistencia (CU-16).
