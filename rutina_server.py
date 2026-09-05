#!/usr/bin/env python3
import http.server
import socketserver
import json
import os
import html
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

PORT = 8090
# Sirve index.html/rutina.html desde donde esté este script (el checkout git
# en el servidor), no de una carpeta separada — así "git pull" alcanza.
DIRECTORY = os.path.dirname(os.path.abspath(__file__))
TZ = ZoneInfo('America/Santiago')

# El panel (ironcross-dashboard) es la fuente de verdad sobre Postgres.
# Este servidor ya no toca la base: todo pasa por su API.
PANEL_API_URL = os.environ.get('PANEL_API_URL', 'https://panel.ironcross.cl').rstrip('/')
IPAD_API_TOKEN = os.environ.get('IPAD_API_TOKEN', '')

PAGE_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">
<title>Ironcross - Rutina</title>
<style>
  * {{ margin:0; padding:0; -webkit-box-sizing:border-box; box-sizing:border-box; }}
  html, body {{ width:100%; height:100%; background:#0A0A09; }}
  body {{ font-family: Helvetica, Arial, sans-serif; }}
  #topbar {{ padding:16px 20px; }}
  #back {{ color:#7A7568; text-decoration:none; font-size:16px; letter-spacing:2px; }}
  #brand {{ color:#C23B22; font-weight:bold; font-size:22px; letter-spacing:6px; margin-top:8px; text-transform:uppercase; }}
  form {{ position:absolute; top:90px; left:0; right:0; bottom:0; padding:0 20px 20px 20px; }}
  textarea {{
    width:100%;
    height:78%;
    background:#141412;
    color:#EDE9DF;
    border:1px solid #2A2A26;
    font-size:22px;
    font-family: Helvetica, Arial, sans-serif;
    padding:14px;
  }}
  button {{
    margin-top:14px;
    width:100%;
    height:64px;
    background:#C23B22;
    color:#EDE9DF;
    font-weight:bold;
    font-size:22px;
    letter-spacing:3px;
    border:0;
  }}
</style>
</head>
<body>
  <div id="topbar">
    <a id="back" href="/">&larr; RELOJ</a>
    <div id="brand">Rutina de {fecha}</div>
  </div>
  <form method="POST" action="/guardar">
    <input type="hidden" name="fecha" value="{fecha}">
    <textarea name="rutina">{rutina}</textarea>
    <button type="submit">GUARDAR</button>
  </form>
</body>
</html>
"""


def hoy():
    return datetime.now(TZ).date().isoformat()


def maniana():
    return (datetime.now(TZ).date() + timedelta(days=1)).isoformat()


class PanelError(Exception):
    """La API del panel respondió mal, o no se pudo llegar a ella."""

    def __init__(self, status, detail=''):
        super().__init__('panel API {}: {}'.format(status, detail))
        self.status = status


def panel_request(method, path, params=None, json_body=None):
    """Llama a la API de ironcross-dashboard. Nunca toca Postgres directo."""
    if not IPAD_API_TOKEN:
        raise PanelError(500, 'IPAD_API_TOKEN no configurado')

    url = PANEL_API_URL + path
    if params:
        url += '?' + urllib.parse.urlencode(params)

    data = None
    headers = {'Authorization': 'Bearer ' + IPAD_API_TOKEN}
    if json_body is not None:
        data = json.dumps(json_body).encode('utf-8')
        headers['Content-Type'] = 'application/json'

    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status, resp.read().decode('utf-8')
    except urllib.error.HTTPError as e:
        raise PanelError(e.code, e.read().decode('utf-8', 'ignore'))
    except urllib.error.URLError as e:
        raise PanelError(502, str(e.reason))


def leer_rutina(fecha):
    """Trae la rutina del día desde el panel (ya incluye la plantilla si está vacía)."""
    _, body = panel_request('GET', '/api/rutina', params={'fecha': fecha})
    try:
        data = json.loads(body)
    except ValueError:
        raise PanelError(502, 'respuesta no-JSON de /api/rutina')
    return data.get('contenido', '')


def guardar_rutina(fecha, contenido):
    panel_request('POST', '/api/rutina', json_body={'fecha': fecha, 'contenido': contenido})


def dias_disponibles():
    """DIAS: hoy + mañana (calculados acá, sin red) + los que ya tienen rutina (del panel)."""
    dias = set()
    try:
        _, body = panel_request('GET', '/api/rutina/dias')
        data = json.loads(body)
        dias.update(data.get('dias', []))
    except (PanelError, ValueError):
        pass  # degradar a solo hoy/mañana antes que romper la pestaña RUTINA
    dias.add(hoy())
    dias.add(maniana())
    return sorted(dias, reverse=True)


def leer_oficina():
    """Texto para la pestaña GYM del iPad. Mismo formato de antes, ahora vía panel."""
    _, body = panel_request('GET', '/api/oficina')
    return body


def es_fecha_valida(fecha):
    try:
        date.fromisoformat(fecha)
        return True
    except ValueError:
        return False


class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        qs = urllib.parse.parse_qs(parsed.query)

        if parsed.path == '/rutina.html' or parsed.path == '/rutina':
            fecha = qs.get('fecha', [hoy()])[0]
            if not es_fecha_valida(fecha):
                fecha = hoy()
            try:
                rutina = leer_rutina(fecha)
            except PanelError:
                self.send_response(502)
                self.end_headers()
                return
            body = PAGE_TEMPLATE.format(fecha=fecha, rutina=html.escape(rutina)).encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif parsed.path == '/api/rutina':
            fecha = qs.get('fecha', [hoy()])[0]
            if not es_fecha_valida(fecha):
                self.send_response(400)
                self.end_headers()
                return
            try:
                body = leer_rutina(fecha).encode('utf-8')
            except PanelError:
                self.send_response(502)
                self.end_headers()
                return
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif parsed.path == '/api/rutina/dias':
            hoy_str = hoy()
            man_str = maniana()
            texto = 'HOY:' + hoy_str + '\n' + 'MANIANA:' + man_str + '\n' + 'DIAS:' + ','.join(dias_disponibles())
            body = texto.encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif parsed.path == '/api/oficina':
            try:
                body = leer_oficina().encode('utf-8')
            except PanelError:
                self.send_response(502)
                self.end_headers()
                return
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            super().do_GET()

    def do_POST(self):
        if self.path == '/guardar':
            length = int(self.headers.get('Content-Length', 0))
            raw = self.rfile.read(length).decode('utf-8')
            data = urllib.parse.parse_qs(raw)
            rutina = data.get('rutina', [''])[0]
            fecha = data.get('fecha', [hoy()])[0]
            if not es_fecha_valida(fecha):
                fecha = hoy()
            try:
                guardar_rutina(fecha, rutina)
            except PanelError:
                self.send_response(502)
                if self.headers.get('X-Requested-With') != 'XMLHttpRequest':
                    self.send_header('Content-Type', 'text/plain; charset=utf-8')
                    self.end_headers()
                    self.wfile.write(b'No se pudo guardar')
                else:
                    self.end_headers()
                return
            if self.headers.get('X-Requested-With') == 'XMLHttpRequest':
                body = b'ok'
                self.send_response(200)
                self.send_header('Content-Type', 'text/plain; charset=utf-8')
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            else:
                self.send_response(303)
                self.send_header('Location', '/rutina.html?fecha=' + fecha)
                self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass


if __name__ == '__main__':
    if not IPAD_API_TOKEN:
        print('ADVERTENCIA: IPAD_API_TOKEN no configurado, la API del panel va a rechazar todo con 401/500.')
    with Server(('0.0.0.0', PORT), Handler) as httpd:
        print('Serving on port', PORT)
        httpd.serve_forever()
