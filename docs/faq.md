# Preguntas frecuentes

## Clave de IA

- **Dónde la consigo:** en <https://openrouter.ai/settings/keys>, con **Create API Key**. Empieza con `sk-or-`. Los modelos gratuitos no requieren saldo.
- **Cómo la cambio o la sumo después:** borrá `.env` de la carpeta del aula y volvé a abrir el lanzador. También podés editar `OPENROUTER_API_KEY` en `.env`.
- **Dónde queda guardada:** solo en `.env`, en tu computadora. No se sube al repositorio (`.gitignore`).
- **Sin IA:** Enter vacío cuando el lanzador pide la clave, o `IA_PROVEEDOR=falso` en `.env`. El tutor responde textos de ejemplo.

## El tutor da error

Los modelos gratuitos tienen límites bajos (unas 50 consultas por día) y a veces cortan la respuesta: reintentá en un rato. Con saldo en OpenRouter, agregá `IA_OPENROUTER_MODELO=deepseek/deepseek-v4.1-flash` a `.env`.

## Avisos de seguridad

- **Windows ("Windows protegió su PC"):** **Más información → Ejecutar de todas formas**.
- **Windows (firewall pregunta por Python):** podés cancelar; el aula solo escucha en tu computadora.
- **macOS ("no se puede abrir"):** clic derecho sobre `iniciar.command` → **Abrir** → **Abrir**.

## El lanzador no arranca

- **Windows dice que descomprimas el ZIP:** clic derecho sobre el ZIP → **Extraer todo**, y abrí `iniciar.bat` desde la carpeta extraída.
- **"El aula ya está abierta":** ya hay una ventana del aula corriendo; el lanzador solo abre el navegador.
- **Otro error:** copiá el mensaje de la ventana y mandalo al grupo.

## Datos de ejemplo

Para volver a los datos originales, con el entorno activado: `python manage.py cargar_demo --reset`. Ver [desarrollo.md](desarrollo.md).

## Mensaje `invalid pdf header` en los tests

Es esperado: lo produce `test_pdf_sin_texto_es_error` (`aula/test_ia.py`).
