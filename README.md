# Metodologia-y-Sistemas-grupo11
# Caso de Uso: Gestionar Actividad Académica y Trámites

**Sistema:** Sistema de Gestión de Aulas Virtuales
**Autores:** David, Naim, Alejo y Amado
**Fecha de Creación:** 11/09/2026 | **Última Modificación:** 11/09/2026

## Resumen
| Atributo | Descripción |
| :--- | :--- |
| **Descripción** | Describe el proceso mediante el cual un alumno autenticado accede al sistema para visualizar su estado académico y ejecutar trámites estudiantiles. |
| **Actor Primario** | Alumno |
| **Actores Secundarios** | Ninguno (No hay sistemas externos involucrados en esta etapa) |
| **Precondiciones** | El alumno debe estar registrado en la institución y poseer credenciales de acceso activas. |
| **Postcondiciones** | El alumno visualiza la información solicitada o completa el trámite deseado de forma exitosa. |

---

## Flujo de Eventos

### Curso Normal (Flujo Principal)
1. **El Alumno** ingresa sus credenciales en la pantalla de inicio de sesión.
2. **El Sistema** valida las credenciales y despliega el panel principal (dashboard).
3. **El Alumno** selecciona un área específica desde el menú principal (ej. "Actividad Académica" o "Trámites").
4. **El Sistema** carga y muestra las opciones y datos disponibles correspondientes a esa área.
5. **El Alumno** selecciona un elemento, trámite o consulta específica para interactuar.
6. **El Sistema** procesa la solicitud y devuelve el resultado esperado (formulario, certificado, historial de notas, etc.).

### Cursos Alternativos (Flujos de Excepción)
* **1.1 Credenciales Inválidas:** Si los datos ingresados en el paso 1 son incorrectos, el Sistema muestra un mensaje de error y solicita reingresar las credenciales. Retorna al paso 1.
* **4.1 Área en Mantenimiento / No Disponible:** Si el área seleccionada en el paso 3 está deshabilitada, el Sistema notifica que la sección no se encuentra disponible temporalmente. Retorna al paso 2.
* **6.1 Elemento Restringido:** Si el elemento seleccionado en el paso 5 requiere permisos especiales o requisitos que el alumno no cumple (ej. correlativas pendientes para un trámite), el Sistema emite una alerta indicando el motivo de la restricción. Retorna al paso 4.
