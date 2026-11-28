# Testing

## Como correr los tests
```bash
python manage.py test                     # 122 tests rápidos, sin red, base temporal
python manage.py test --tag=e2e          # solo el recorrido E2E en navegador
python manage.py test --exclude-tag=e2e  # todo menos el E2E
```

El E2E necesita preparar el entorno de desarrollo (ver abajo). Sin eso se saltea y el resto corre igual.

## Entorno de desarrollo para el E2E

Una sola vez, con el entorno virtual activado:

```bash
pip install -r requirements-dev.txt   # Playwright
playwright install chromium           # el navegador (~125 MB)
```

Estas dependencias van aparte de `requirements.txt` a propósito: el lanzador `iniciar.*` solo instala lo que necesita quien usa el aula, y el navegador de pruebas pesaría de más. Si Playwright se actualiza y el E2E se saltea pidiendo el navegador, hay que repetir `playwright install chromium`.

## Criterio
Probamos las reglas del dominio que, si fallan, rompen el recorrido del alumno o exponen datos ajenos: desbloqueo de unidades, cuándo se completa un contenido, la ventana de la clase en vivo y el acceso por rol. No probamos lo que ya garantiza Django (ORM, admin, login).

Por cada regla buscamos tres tipos de caso:

- **Normal:** el camino esperado.
- **Límite:** el valor exacto donde cambia el resultado, porque ahí aparecen los errores de `<` contra `<=`.
- **Error:** entradas inválidas o accesos indebidos, que tienen que fallar de forma controlada (404, 403, reintento).

La IA se reemplaza por `ProveedorFalso` y mocks: los tests no dependen de la red, son deterministas y verifican nuestra lógica, no la del modelo.

## Ejemplos
| Regla | Caso | Tipo | Test |
| --- | --- | --- | --- |
| La clase en vivo abre 15 min antes y cierra al terminar | 18:14 cerrada, 18:15 abierta; 20:00 abierta, 20:01 cerrada | Límite | [`test_clase.py:136`](../aula/test_clase.py#L136), [`:140`](../aula/test_clase.py#L140) |
| El cuestionario se aprueba con el mínimo de aciertos (50 %) | 1 de 2 aprueba, justo en el umbral | Límite | [`test_contenido.py:78`](../aula/test_contenido.py#L78) |
| Un cuestionario no aprobado se puede reintentar | 0 de 2: no se completa, cuenta el intento y el segundo intento aprueba | Error | [`test_contenido.py:85`](../aula/test_contenido.py#L85) |
| Completar una unidad desbloquea la siguiente | la unidad 2 se abre al completar la 1 | Normal | [`tests.py:39`](../aula/tests.py#L39) |
| Un alumno no ve contenido ajeno ni borradores | ambos dan 404, no 403, para no revelar que existen | Error | [`test_contenido.py:146`](../aula/test_contenido.py#L146) |
| El endpoint del tutor valida acceso y entrada | 400, 403, 404 y 503 además del 200 | Error | [`test_tutor.py:80`](../aula/test_tutor.py#L80) |

## E2E del alumno

[`aula/test_e2e_alumno.py`](../aula/test_e2e_alumno.py) maneja un Chromium real contra el aula levantada de verdad. Es lo único que ejecuta `tutor.js`, y verifica que las pantallas funcionen encadenadas.

- **Un recorrido feliz** que toca CU-01 a CU-08: hub, cursada y avisos, calendario con filtro, clase de hoy y asistencia, cuestionario que desbloquea la unidad siguiente, y tutor con un enlace que lleva al material.
- **Un caso de error:** entrar por URL a un contenido de una unidad bloqueada explica qué falta.
- **Pocos y largos a propósito:** son lentos y frágiles, así que cubren solo el flujo crítico; las reglas finas ya están en los tests unitarios y de integración.
- **Datos y IA:** usa los datos de `cargar_demo` con tres ajustes para no depender del día ni de la hora (clase abierta hoy, unidad lista para desbloquear, tutor con una referencia real). La IA es `ProveedorFalso`, así que no usa red ni la clave.
- **Buscar por lo que ve el usuario:** los elementos se ubican por rol y texto visible, no por clases CSS.

## Limitaciones
- Los mocks no prueban el proveedor de IA real; eso se verifica a mano con `python manage.py demo_ia`.
- El E2E prueba que el widget y el endpoint funcionan juntos, no la calidad de las respuestas del modelo.
- El E2E corre en un solo navegador (Chromium) y a un solo tamaño de pantalla.
