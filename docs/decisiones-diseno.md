# Decisiones de Diseño y Arquitectura - Aula Virtual

*Contexto:* Documento de registro de decisiones técnicas (ADR) para el Taller II de Metodología de Sistemas II. Se prioriza la mantenibilidad, la reducción de deuda técnica y la simplicidad (Clean Code), aplicando patrones de diseño solo frente a tensiones de acoplamiento reales.

---

## 1. Patrones Estructurales (Aplicados)
Objetivo: Conectar componentes sin propagar incompatibilidades ni ensuciar la lógica de dominio.

### 1.1. Facade (Fachada)
* *Dónde:* aula/services/ia_facade.py (AsistenteIAFacade).
* *Problema:* La generación de sílabos requiere orquestar múltiples pasos técnicos: leer credenciales, armar el prompt JSON, llamar a la API de Anthropic y capturar excepciones.
* *Decisión:* Ocultar este ritual técnico detrás de una Fachada. Las vistas web consumen un único método limpio (generar_silabo(materia)).
* *Beneficio:* Reducción drástica del acoplamiento. La vista expresa la intención de alto nivel sin conocer la infraestructura de la IA.

### 1.2. Adapter (Adaptador)
* *Dónde:* Integrado dentro de ia_facade.py.
* *Problema:* El SDK de Anthropic (Claude) utiliza sus propias firmas, modelos de datos y excepciones.
* *Decisión:* Envolver el cliente de Anthropic para que traduzca la respuesta externa al formato de diccionario/JSON estandarizado que espera nuestro dominio.
* *Beneficio:* Si a futuro se migra de Anthropic a OpenAI, el cambio queda aislado en el adaptador sin alterar ni una línea del resto del sistema.

### 1.3. Decorator (Decorador)
* *Dónde:* Funciones de views.py.
* *Problema:* Validar la sesión y el rol (Alumno vs. Profesor) dentro de cada vista genera duplicación masiva (Code Smell) y mezcla reglas de seguridad con lógica de negocio.
* *Decisión:* Utilizar los decoradores nativos de Django (@login_required, @user_passes_test).
* *Beneficio:* Interceptan la petición agregando la capa de validación antes de la ejecución de la función. Protege las rutas manteniendo las vistas con una única responsabilidad (SRP).

---

## 2. Patrones de Comportamiento
Objetivo: Organizar interacciones, reacciones y responsabilidades.

### 2.1. Observer (Aplicado / Preparado)
* *Dónde:* aula/signals.py (Django Signals).
* *Problema:* La creación de un contenido o la calificación de una entrega debe disparar acciones secundarias (ej. logs, notificaciones futuras por email) sin bloquear el proceso de guardado (Publisher).
* *Decisión:* Desacoplar las reacciones usando el patrón Observer mediante señales (post_save). 
* *Beneficio:* El modelo de base de datos guarda la entidad y emite el evento; los suscriptores reaccionan de manera independiente, respetando el principio Open/Closed (OCP).

### 2.2. Strategy (Descartado temporalmente)
* *Problema evaluado:* ¿Múltiples formas de calcular la aprobación o evaluar entregas?
* *Justificación de rechazo:* Actualmente el sistema cuenta con una *única regla fija* (evaluación de la condición esta_desbloqueada). Implementar clases Strategy para un único algoritmo es overengineering. 
* *Evolución:* Si a futuro se integran múltiples métodos de evaluación (PDF, Cuestionario Automático, Oral por Zoom), se introducirá Strategy para evitar condicionales gigantes (if/elif).

### 2.3. Command (Descartado)
* *Problema evaluado:* ¿Tratar las acciones del usuario como objetos para encolarlas o reintentarlas?
* *Justificación de rechazo:* Las acciones en el Aula Virtual (inscribirse, entregar, calificar) son peticiones HTTP síncronas e inmediatas. No existen procesos batch pesados ni necesidad de Undo/Redo que justifiquen la complejidad de encolar comandos.

---

## 3. Patrones Creacionales (Descartados)
Objetivo: Centralizar la creación de objetos. En este proyecto: No requeridos.

* *Decisión global:* El ORM de Django (models.py) centraliza la persistencia y la creación de entidades, actuando como única fuente de verdad. La instanciación directa es el mecanismo nativo, simple y estable.
* *Factory:* Rechazado. Se colapsó la herencia de Contenido utilizando un campo discriminador (tipo), eliminando la necesidad de seleccionar entre múltiples subclases concretas.
* *Builder:* Rechazado. Las entidades de dominio (Catedra, Cursada, Unidad) no poseen construcciones de múltiples pasos complejos. 
* *Singleton:* Rechazado. El framework ya administra eficientemente el ciclo de vida de los recursos globales (conexión SQLite en settings.py). Implementarlo manualmente introduciría estado global oculto y dificultaría la inyección en las pruebas unitarias.

---

## 4. Reutilización del framework

* *Panel de administración:* El alta de carreras, materias, cátedras y usuarios se resuelve configurando aula/admin.py, que Django descubre por convención y convierte en un CRUD completo con validación y permisos sin escribir vistas ni formularios propios.
