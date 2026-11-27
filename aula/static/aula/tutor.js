// Widget del tutor IA (CU-08): abre el panel, manda la pregunta con el
// contexto de la pantalla a /tutor/consultar/ y muestra la respuesta con
// enlaces al material citado.
(function () {
  'use strict';

  const raiz = document.querySelector('.tutor');
  if (!raiz) return;

  const boton = raiz.querySelector('.tutor-boton');
  const panel = raiz.querySelector('.tutor-panel');
  const cerrar = raiz.querySelector('.tutor-cerrar');
  const form = raiz.querySelector('.tutor-form');
  const campo = form.querySelector('textarea');
  const enviar = form.querySelector('button[type="submit"]');
  const mensajes = raiz.querySelector('.tutor-mensajes');

  function abrir(abierto) {
    panel.hidden = !abierto;
    boton.setAttribute('aria-expanded', String(abierto));
    if (abierto) campo.focus();
    else boton.focus();
  }

  function contexto() {
    const datos = { pantalla: raiz.dataset.pantalla || 'inicio' };
    if (raiz.dataset.catedraId) datos.catedra_id = Number(raiz.dataset.catedraId);
    if (raiz.dataset.claseId) datos.clase_id = Number(raiz.dataset.claseId);
    if (raiz.dataset.contenidoId) datos.contenido_id = Number(raiz.dataset.contenidoId);
    return datos;
  }

  // Todo el texto se agrega con textContent: nunca se interpreta como HTML.
  function agregar(clase, texto) {
    const mensaje = document.createElement('div');
    mensaje.className = 'tutor-mensaje ' + clase;
    mensaje.textContent = texto;
    mensajes.appendChild(mensaje);
    mensajes.scrollTop = mensajes.scrollHeight;
    return mensaje;
  }

  function agregarReferencias(mensaje, referencias) {
    // Solo enlaces internos del aula.
    const validas = (referencias || []).filter(
      (r) => typeof r.url === 'string' && r.url.startsWith('/') && !r.url.startsWith('//')
    );
    if (!validas.length) return;
    const lista = document.createElement('ul');
    validas.forEach((r) => {
      const item = document.createElement('li');
      const enlace = document.createElement('a');
      enlace.href = r.url;
      enlace.textContent = r.titulo;
      item.appendChild(enlace);
      lista.appendChild(item);
    });
    const titulo = document.createElement('small');
    titulo.textContent = 'Dónde estudiarlo:';
    mensaje.appendChild(titulo);
    mensaje.appendChild(lista);
  }

  function mensajeDeError(estado, cuerpo) {
    if (estado === 503) return 'El tutor no está disponible en este momento. Probá de nuevo más tarde.';
    if (cuerpo && cuerpo.error) return cuerpo.error;
    return 'No se pudo consultar al tutor.';
  }

  async function preguntar(evento) {
    evento.preventDefault();
    const pregunta = campo.value.trim();
    if (!pregunta) return;

    agregar('tutor-pregunta', pregunta);
    campo.value = '';
    enviar.disabled = true;
    enviar.setAttribute('aria-busy', 'true');
    const pensando = agregar('tutor-respuesta tutor-pensando', 'Pensando…');

    try {
      const respuesta = await fetch(raiz.dataset.url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': form.querySelector('[name=csrfmiddlewaretoken]').value,
        },
        body: JSON.stringify(Object.assign({ pregunta: pregunta }, contexto())),
      });
      const cuerpo = await respuesta.json().catch(() => null);
      pensando.remove();
      if (!respuesta.ok) {
        agregar('tutor-respuesta tutor-error', mensajeDeError(respuesta.status, cuerpo));
        return;
      }
      const mensaje = agregar('tutor-respuesta', cuerpo.texto);
      agregarReferencias(mensaje, cuerpo.referencias);
    } catch (error) {
      pensando.remove();
      agregar('tutor-respuesta tutor-error', 'No hay conexión con el aula. Revisá tu conexión.');
    } finally {
      enviar.disabled = false;
      enviar.removeAttribute('aria-busy');
      campo.focus();
    }
  }

  boton.addEventListener('click', () => abrir(panel.hidden));
  cerrar.addEventListener('click', () => abrir(false));
  form.addEventListener('submit', preguntar);
  campo.addEventListener('keydown', (evento) => {
    // Enter envía; Shift+Enter agrega un salto de línea.
    if (evento.key === 'Enter' && !evento.shiftKey) {
      evento.preventDefault();
      form.requestSubmit();
    }
  });
  document.addEventListener('keydown', (evento) => {
    if (evento.key === 'Escape' && !panel.hidden) abrir(false);
  });
})();
