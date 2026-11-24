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
- [ ] `docs/adr-actualizacion`: decisiones de diseño al día, README y este plan.

### infraestructura/
- [ ] **`infraestructura/schema-alumno`**: modelos nuevos (horarios, clases, asistencia, eventos, avisos, fe de erratas) y su carga desde el admin.
- [ ] `infraestructura/datos-demo`: grupos alumno y profesor, comando para cargar datos de ejemplo y archivos subidos en desarrollo. *Después de `schema-alumno`.*

### backend/
- [ ] `backend/rol-requerido`: Decorator para restringir vistas por rol. *Después de `schema-alumno`.*
- [ ] `backend/formatos-contenido`: Strategy por formato y registro del progreso. *Después de `schema-alumno`.*
- [ ] `backend/observer`: reacciones al completar contenido y al publicar avisos. *Después de `formatos-contenido`.*
- [ ] `backend/ia-facade`: Facade y Adapter de la IA, con un proveedor falso para tests. *Se puede empezar ya.*
- [ ] `backend/tutor`: consulta al tutor con el contexto de la pantalla y enlaces al material. *Después de `ia-facade`.*

### frontend/
Cada rama de pantalla incluye su vista y su template.

- [ ] **`frontend/base-navegacion`**: estructura común (encabezado, navegación inferior y lugar para el tutor). *Después de `rol-requerido`.*
- [ ] `frontend/hub`: inicio con cursadas, próximas fechas y avisos (CU-01). *Después de `base-navegacion`.*
- [ ] `frontend/curso-avisos`: ficha del curso, unidades y avisos (CU-02, CU-03). *Después de `base-navegacion`.*
- [ ] `frontend/calendario`: clases y fechas del mes con filtro (CU-04). *Después de `base-navegacion`.*
- [ ] `frontend/clase`: clase del día, link en vivo y asistencia (CU-05, CU-06). *Después de `base-navegacion`.*
- [ ] `frontend/contenido`: un template por formato (CU-07). *Después de `formatos-contenido` y `base-navegacion`.*
- [ ] `frontend/tutor-widget`: botón y panel del tutor (CU-08). *Después de `tutor` y `base-navegacion`.*

## Próximo incremento

Perspectiva del profesorado: importar el programa, generar contenido con IA, revisar y publicar, cargar clases, fechas y avisos, y seguir el progreso. Arranca cuando esté completa la lista de arriba.
