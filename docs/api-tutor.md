# Endpoint del tutor IA

Único endpoint JSON, consumido por el widget (`aula/static/aula/tutor.js`) e implementado en `aula/views/tutor.py`.

- **Ruta:** `POST /tutor/consultar/`. Requiere sesión con rol `alumno`, `Content-Type: application/json` y `X-CSRFToken`.
- **Entrada:** `{"pregunta": "...", "pantalla": "roadmap", "catedra_id": 1}`. `pregunta` es obligatoria; los IDs son opcionales y enteros.
- **Salida (`200`):** `{"texto": "...", "referencias": [{"contenido_id": 4, "titulo": "...", "url": "/contenido/4/"}]}`.

| Código | Motivo |
| --- | --- |
| `400` | JSON o datos inválidos |
| `403` | Rol no autorizado, cátedra ajena (anti-IDOR) o borrador |
| `404` | ID inexistente |
| `405` | Método distinto de `POST` |
| `503` | Falló el proveedor de IA |
