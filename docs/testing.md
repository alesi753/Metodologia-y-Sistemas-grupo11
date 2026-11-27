# Testing

## Como correr los tests
```bash
python manage.py test            # 122 tests, sin red, base temporal
```

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

## Limitaciones
- Los mocks no prueban el proveedor de IA real; eso se verifica a mano con `python manage.py demo_ia`.
- `tutor.js` no corre en ningún test: el cliente de Django no ejecuta JavaScript. Cubrirlo requiere un test E2E con navegador.
