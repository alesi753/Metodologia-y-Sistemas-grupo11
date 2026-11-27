"""Levanta el aula virtual: clave de IA, base de datos, datos de ejemplo y servidor.

Lo llaman iniciar.bat, iniciar.sh e iniciar.command después de preparar Python,
así la lógica vive en un solo lugar para los tres sistemas. Usa solo la
biblioteca estándar: corre antes de que importe nada de Django.
"""

import os
import socket
import subprocess
import sys
import threading
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
ENV = RAIZ / '.env'
HOST, PUERTO = '127.0.0.1', 8000
URL_AULA = f'http://{HOST}:{PUERTO}/'
URL_CLAVES = 'https://openrouter.ai/settings/keys'
URL_VERIFICAR = 'https://openrouter.ai/api/v1/key'


def main():
    sys.stdout.reconfigure(line_buffering=True)  # mensajes en orden con los de Django
    if aula_abierta():
        print(f'El aula ya está abierta en {URL_AULA}')
        webbrowser.open(URL_AULA)
        return
    if not ENV.exists():
        configurar_ia()
    manage('migrate', '--noinput', '-v0')
    manage('cargar_demo')
    threading.Timer(2, webbrowser.open, [URL_AULA]).start()
    print(f'\nAula abierta en {URL_AULA} . Para cerrarla, cerrá esta ventana o apretá Ctrl+C.\n')
    try:
        manage('runserver', f'{HOST}:{PUERTO}')
    except KeyboardInterrupt:
        print('\nAula cerrada.')


def aula_abierta():
    with socket.socket() as conexion:
        conexion.settimeout(0.5)
        return conexion.connect_ex((HOST, PUERTO)) == 0


def manage(*args):
    subprocess.run([sys.executable, str(RAIZ / 'manage.py'), *args], cwd=RAIZ, check=True)


def configurar_ia():
    print('\n=== Tutor IA (solo la primera vez) ===')
    print('El tutor usa OpenRouter. Te abrimos la página oficial para crear tu clave:')
    print(f'  {URL_CLAVES}')
    print('Iniciá sesión, tocá "Create API Key" y copiá la clave (empieza con sk-or-).\n')
    webbrowser.open(URL_CLAVES)
    while True:
        clave = input('Pegá la clave y apretá Enter (Enter vacío = usar el aula sin IA): ').strip()
        if not clave:
            guardar_env({'IA_PROVEEDOR': 'falso'})
            print('Listo: el aula funciona sin IA. Para sumarla después, borrá el archivo .env y volvé a abrir iniciar.')
            return
        error = verificar(clave)
        if error is None:
            guardar_env({'IA_PROVEEDOR': 'openrouter', 'OPENROUTER_API_KEY': clave})
            print('Clave guardada. No te la vamos a volver a pedir.')
            return
        print(error)


def verificar(clave):
    """Devuelve un mensaje si la clave no sirve, o None si sirve o no se pudo comprobar."""
    if not clave.startswith('sk-or-'):
        return 'Esa no parece una clave de OpenRouter: tiene que empezar con sk-or-. Probá de nuevo.'
    pedido = urllib.request.Request(URL_VERIFICAR, headers={'Authorization': f'Bearer {clave}'})
    try:
        urllib.request.urlopen(pedido, timeout=10)
    except urllib.error.HTTPError as error:
        if error.code == 401:
            return 'OpenRouter rechazó la clave. Revisá que esté completa y volvé a pegarla.'
        print(f'Aviso: no pudimos verificar la clave (OpenRouter respondió {error.code}). La guardamos igual.')
    except OSError:
        print('Aviso: no pudimos conectarnos a OpenRouter para verificar la clave. La guardamos igual.')
    return None


def guardar_env(variables):
    lineas = ['# Generado por iniciar. Para cambiar la clave, borrá este archivo y volvé a abrir iniciar.']
    lineas += [f'{nombre}={valor}' for nombre, valor in variables.items()]
    ENV.write_text('\n'.join(lineas) + '\n', encoding='utf-8')
    if os.name == 'posix':
        ENV.chmod(0o600)


if __name__ == '__main__':
    main()
