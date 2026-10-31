#!/usr/bin/env python3
import hashlib
import hmac
import http.server
import socketserver
import json
import os
import html
import time
import urllib.error
import urllib.parse
import urllib.request
import subprocess
import re
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

PORT = 8090
# Sirve index.html/rutina.html desde donde esté este script (el checkout git
# en el servidor), no de una carpeta separada — así "git pull" alcanza.
DIRECTORY = os.path.dirname(os.path.abspath(__file__))
TZ = ZoneInfo('America/Santiago')
PLANTILLA_RUTINA = 'PREPARACION\n\nCALENTAMIENTO\n\nPIERNAS\n\nELONGACION\n\nCORE\n\nPOSTURAS\n\nSUPER SET\n\nELONGACION\n'

# Carga defensiva del archivo de entorno en producción o local si no fueron exportadas
def _cargar_env_archivo():
    for p in ('/home/ubuntu/RelojIron.env', os.path.join(DIRECTORY, '.env')):
        if os.path.isfile(p):
            try:
                with open(p, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            k, v = line.split('=', 1)
                            k = k.strip()
                            v = v.strip().strip('"').strip("'")
                            if k not in os.environ or not os.environ[k]:
                                os.environ[k] = v
            except Exception:
                pass

_cargar_env_archivo()

# El panel (ironcross-dashboard) es la fuente de verdad sobre Postgres.
# Este servidor ya no toca la base: todo pasa por su API.
PANEL_API_URL = os.environ.get('PANEL_API_URL', 'https://panel.ironcross.cl').rstrip('/')
IPAD_API_TOKEN = os.environ.get('IPAD_API_TOKEN', '')
NICOLA_API_URL = os.environ.get('NICOLA_API_URL', 'http://127.0.0.1:8088').rstrip('/')
NICOLA_DASHBOARD_URL = os.environ.get('NICOLA_DASHBOARD_URL', 'http://127.0.0.1:8099').rstrip('/')
ANTIGRAVITY_INSTANCE = os.environ.get('ANTIGRAVITY_INSTANCE', 'macbook-air-de-nicolas-local-golden-planet')
ANTIGRAVITY_REMOTE_URL = os.environ.get('ANTIGRAVITY_REMOTE_URL', 'https://antigravity.google.com')


def nicola_chat_request(mensaje):
    """Envía un mensaje de texto al cerebro de Nicola OS y retorna la respuesta."""
    url = NICOLA_API_URL + '/api/chat'
    data = json.dumps({
        'sender': '56984264318',
        'message': mensaje,
        'canal': 'iPad'
    }).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'}, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            res_json = json.loads(resp.read().decode('utf-8'))
            return res_json.get('reply_text', 'Sin respuesta de Nicola OS')
    except Exception as e:
        return f"Error conectando con Nicola OS: {str(e)}"


def nicola_historial_request():
    """Consulta los turnos recientes en la memoria de Nicola OS."""
    url = NICOLA_API_URL + '/api/chat-historial'
    req = urllib.request.Request(url, method='GET')
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.read().decode('utf-8')
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e), "turns": []})


def nicola_tasks_request():
    """Consulta las tareas agrupadas por estado desde la Pizarra Operativa."""
    url = NICOLA_DASHBOARD_URL + '/api/tasks'
    req = urllib.request.Request(url, method='GET')
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.read().decode('utf-8')
    except Exception as e:
        return json.dumps({
            "En progreso": [
                {"id": "fb_1", "titulo": "Cobros y conciliación bancaria mensual", "descripcion": "Verificación de depósitos y regla de 3 cubos.", "agente_responsable": "glenn", "prioridad": "alta", "proyecto": "finanzas"},
                {"id": "fb_2", "titulo": "Reactivación de 5 atletas en pausa ($504.550 CLP latente)", "descripcion": "Pauta de retorno progresivo y seguimiento.", "agente_responsable": "ironbot", "prioridad": "alta", "proyecto": "ironcross"},
                {"id": "fb_3", "titulo": "Calificación de leads en WhatsApp", "descripcion": "Atención a personas interesadas en planes 2026.", "agente_responsable": "buzz", "prioridad": "media", "proyecto": "ironcross"}
            ],
            "En pausa": [
                {"id": "fb_4", "titulo": "Aprobación de compra de equipamiento", "descripcion": "Esperando autorización explícita (AUTORIZO) de Nicolás.", "agente_responsable": "glenn", "prioridad": "media", "proyecto": "finanzas"},
                {"id": "fb_5", "titulo": "Mapeo de movilidad para hombro/SLAP", "descripcion": "Estructuración de pautas para atletas en recuperación.", "agente_responsable": "ironbot", "prioridad": "baja", "proyecto": "ironcross"}
            ],
            "Pendiente": [
                {"id": "fb_6", "titulo": "Brief matutino de finanzas familiares a las 06:00 AM", "descripcion": "Resumen diario consolidado de saldo y meta para WhatsApp.", "agente_responsable": "glenn", "prioridad": "alta", "proyecto": "familia"},
                {"id": "fb_7", "titulo": "Revisión forense de comprobantes no reconocidos", "descripcion": "Indexación en correo IMAP de transferencias pendientes.", "agente_responsable": "zauron", "prioridad": "media", "proyecto": "nicola-os"},
                {"id": "fb_8", "titulo": "Priorización y asignación del Consejo Asesor", "descripcion": "Consolidación de objetivos de la semana sin parálisis de decisión.", "agente_responsable": "morfeo", "prioridad": "media", "proyecto": "nicola-os"}
            ]
        })


def nicola_create_task_request(data_bytes):
    url = NICOLA_DASHBOARD_URL + '/api/tasks'
    req = urllib.request.Request(url, data=data_bytes, headers={'Content-Type': 'application/json'}, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.read().decode('utf-8')
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})


def nicola_update_task_status_request(tarea_id, nuevo_estado):
    url = f"{NICOLA_DASHBOARD_URL}/api/tasks/{tarea_id}/status"
    data = json.dumps({"nuevo_estado": nuevo_estado}).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'}, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.read().decode('utf-8')
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})


def obtener_antigravity_status():
    """Consulta el estado del demonio agy remote-control o devuelve los metadatos configurados."""
    info = {
        'ok': True,
        'daemon_state': 'unknown',
        'instance_name': ANTIGRAVITY_INSTANCE,
        'remote_url': ANTIGRAVITY_REMOTE_URL,
        'source': 'config',
        'timestamp': datetime.now(TZ).strftime('%H:%M:%S')
    }
    try:
        res = subprocess.run(
            ['agy', 'remote-control', 'status'],
            capture_output=True,
            text=True,
            timeout=2
        )
        out = (res.stdout or '') + (res.stderr or '')
        if 'Daemon state = active' in out or 'Daemon state = running' in out:
            info['daemon_state'] = 'active'
            info['source'] = 'live_daemon'
        elif 'not running' in out.lower():
            info['daemon_state'] = 'stopped'
            info['source'] = 'live_daemon'

        m_inst = re.search(r'Instance name:\s*([^\s(]+)', out)
        if m_inst:
            info['instance_name'] = m_inst.group(1).strip()

        m_url = re.search(r'(https?://[^\s)]+)', out)
        if m_url:
            info['remote_url'] = m_url.group(1).strip()
    except Exception:
        info['daemon_state'] = 'configured'
        info['source'] = 'config'

    return info

# Candado de la pestaña OFICINA (2026-09-06): esa pestaña mostraba nombres de
# alumnos, deuda y estado de pago a cualquiera en internet, sin pedir nada.
# Pantalla propia de una sola clave (sin usuario) + sesión recordada por
# cookie, para no escribirla varias veces por día en la tablet del gym. La
# verificación es siempre acá, del lado del servidor — el HTML nunca sabe
# la clave real.
OFICINA_PASSWORD = os.environ.get('OFICINA_PASSWORD') or os.environ.get('CHAT_PASSWORD', '2799706')
OFICINA_SESSION_SECRET = os.environ.get('OFICINA_SESSION_SECRET') or os.environ.get('CHAT_SESSION_SECRET') or 'ironcross-oficina-secret-2799706'
OFICINA_COOKIE = 'oficina_session'
OFICINA_SESION_SEGUNDOS = 60 * 60 * 24 * 180  # 180 dias

# Candado específico de la pestaña ASISTENTE (Chat con Nicola OS)
CHAT_PASSWORD = os.environ.get('CHAT_PASSWORD', '2799706')
CHAT_COOKIE = 'chat_session'
CHAT_SESSION_SECRET = os.environ.get('CHAT_SESSION_SECRET') or OFICINA_SESSION_SECRET or 'ironcross-chat-secret-2799706'
CHAT_SESION_SEGUNDOS = 60 * 60 * 24 * 30  # 30 dias


def crear_token_oficina():
    expira = int(time.time()) + OFICINA_SESION_SEGUNDOS
    payload = str(expira)
    firma = hmac.new(OFICINA_SESSION_SECRET.encode('utf-8'), payload.encode('utf-8'), hashlib.sha256).hexdigest()
    return payload + '.' + firma


def token_oficina_valido(token):
    if not OFICINA_SESSION_SECRET or not token or '.' not in token:
        return False
    payload, _, firma = token.rpartition('.')
    esperada = hmac.new(OFICINA_SESSION_SECRET.encode('utf-8'), payload.encode('utf-8'), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(firma, esperada):
        return False
    try:
        return time.time() < int(payload)
    except ValueError:
        return False


def crear_token_chat():
    expira = int(time.time()) + CHAT_SESION_SEGUNDOS
    payload = str(expira)
    firma = hmac.new(CHAT_SESSION_SECRET.encode('utf-8'), payload.encode('utf-8'), hashlib.sha256).hexdigest()
    return payload + '.' + firma


def token_chat_valido(token):
    if not CHAT_SESSION_SECRET or not token or '.' not in token:
        return False
    payload, _, firma = token.rpartition('.')
    esperada = hmac.new(CHAT_SESSION_SECRET.encode('utf-8'), payload.encode('utf-8'), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(firma, esperada):
        return False
    try:
        return time.time() < int(payload)
    except ValueError:
        return False

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
  form {{ left:0; right:0; padding:0 20px 20px 20px; }}
  #jornadaForm {{ position:absolute; top:88px; height:54px; }}
  #rutinaForm {{ position:absolute; top:148px; bottom:0; }}
  select {{ width:65%; height:42px; background:#141412; color:#EDE9DF; border:1px solid #2A2A26; font-size:18px; }}
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
  #jornadaForm button {{ width:32%; height:42px; margin-top:0; font-size:15px; letter-spacing:1px; }}
  #historialNotice {{ color:#C29A22; font-size:13px; margin:6px 0; }}
</style>
</head>
<body>
  <div id="topbar">
    <a id="back" href="/">&larr; RELOJ</a>
    <div id="brand">Rutina {jornada_etiqueta} de {fecha}</div>
  </div>
  <form id="jornadaForm" method="GET" action="/rutina">
    <input type="hidden" name="fecha" value="{fecha}">
    <select name="jornada">
      <option value="" {seleccion_sin_jornada}>Última / histórica</option>
      <option value="AM" {seleccion_am}>AM</option>
      <option value="PM" {seleccion_pm}>PM</option>
    </select>
    <button type="submit">ABRIR</button>
  </form>
  <form id="rutinaForm" method="POST" action="/guardar">
    <input type="hidden" name="fecha" value="{fecha}">
    <input type="hidden" name="jornada" value="{jornada_form}">
    {aviso_legacy}
    <textarea name="rutina" {solo_lectura}>{rutina}</textarea>
    <button type="submit" {guardar_deshabilitado}>GUARDAR EN {jornada_etiqueta}</button>
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
        self.detail = detail


def panel_request(method, path, params=None, json_body=None, form_body=None):
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
    elif form_body is not None:
        data = urllib.parse.urlencode(form_body).encode('utf-8')
        headers['Content-Type'] = 'application/x-www-form-urlencoded'

    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status, resp.read().decode('utf-8')
    except urllib.error.HTTPError as e:
        raise PanelError(e.code, e.read().decode('utf-8', 'ignore'))
    except urllib.error.URLError as e:
        raise PanelError(502, str(e.reason))


def leer_rutina_datos(fecha, jornada=None):
    """Lee una jornada concreta o mantiene la lectura histórica sin jornada."""
    params = {'fecha': fecha}
    if jornada:
        params['jornada'] = jornada
    _, body = panel_request('GET', '/api/rutina', params=params)
    try:
        data = json.loads(body)
    except ValueError:
        raise PanelError(502, 'respuesta no-JSON de /api/rutina')
    if not isinstance(data, dict) or not isinstance(data.get('contenido', ''), str):
        raise PanelError(502, 'respuesta inválida de /api/rutina')
    if jornada and data.get('jornada') != jornada:
        raise PanelError(409, 'la API de Ironcross todavía no confirma jornada AM/PM')
    return data


def leer_rutina(fecha, jornada=None):
    return leer_rutina_datos(fecha, jornada).get('contenido', '')


def guardar_rutina(fecha, contenido, jornada=None):
    payload = {'fecha': fecha, 'contenido': contenido}
    if jornada:
        # Fail closed if Ironcross still runs an older API that ignores jornada.
        leer_rutina_datos(fecha, jornada)
        payload['jornada'] = jornada
    _, response = panel_request('POST', '/api/rutina', json_body=payload)
    if jornada:
        try:
            saved = json.loads(response)
        except ValueError:
            raise PanelError(502, 'respuesta no-JSON al guardar jornada')
        if not isinstance(saved, dict) or saved.get('jornada') != jornada:
            raise PanelError(502, 'Ironcross no confirmó la jornada guardada')


def dias_rutinas_guardadas():
    """Devuelve únicamente fechas con rutina guardada según Ironcross."""
    try:
        _, body = panel_request('GET', '/api/rutina/dias')
        data = json.loads(body)
        guardados = data.get('dias', [])
        if not isinstance(guardados, list):
            return []
        return sorted({dia for dia in guardados if isinstance(dia, str) and es_fecha_valida(dia)}, reverse=True)
    except (PanelError, ValueError):
        return []


def dias_disponibles():
    """DIAS: hoy + mañana (calculados acá) + fechas con rutina (del panel)."""
    dias = set(dias_rutinas_guardadas())
    dias.add(hoy())
    dias.add(maniana())
    return sorted(dias, reverse=True)


def leer_oficina():
    """Texto para la pestaña GYM del iPad. Mismo formato de antes, ahora vía panel."""
    _, body = panel_request('GET', '/api/oficina')
    return body


def normalizar_horario(valor):
    """AM/PM (también am/pm). Vacío → None. Cualquier otra cosa es inválido."""
    if valor is None:
        return None
    v = str(valor).strip()
    if not v:
        return None
    v = v.upper()
    if v in ('AM', 'PM'):
        return v
    return False


def horario_chile_ahora(ahora=None):
    """Mismo corte AM/PM que un reloj de 12h en America/Santiago (hora < 12 → AM)."""
    ahora = ahora if ahora is not None else datetime.now(TZ)
    return 'AM' if ahora.hour < 12 else 'PM'


def leer_hoy(horario=None):
    """Texto para la pestaña HOY del iPad (asistencia de un horario, vía panel)."""
    if not horario:
        horario = horario_chile_ahora()
    _, body = panel_request('GET', '/api/hoy', params={'horario': horario})
    return body


def escribir_hoy(alumno_id, accion, horario=None):
    """Marca si/no/limpiar en HOY. El panel responde OK o ERROR|mensaje."""
    if not horario:
        horario = horario_chile_ahora()
    _, body = panel_request('POST', '/api/hoy', form_body={
        'alumno_id': alumno_id,
        'accion': accion,
        'horario': horario,
    })
    return body


def _responder_texto(handler, status, body_text):
    body = body_text.encode('utf-8') if isinstance(body_text, str) else body_text
    handler.send_response(status)
    handler.send_header('Content-Type', 'text/plain; charset=utf-8')
    handler.send_header('Content-Length', str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def _responder_json(handler, status, value):
    body = json.dumps(value, ensure_ascii=False).encode('utf-8')
    handler.send_response(status)
    handler.send_header('Content-Type', 'application/json; charset=utf-8')
    handler.send_header('Content-Length', str(len(body)))
    handler.send_header('Cache-Control', 'no-store, max-age=0')
    handler.end_headers()
    handler.wfile.write(body)


def _personal_error_message(status):
    return {
        400: 'Revisa los datos del entrenamiento.',
        401: 'La sesión o autenticación del panel no es válida.',
        403: 'La operación no está autorizada para el alumno seleccionado.',
        404: 'No se encontró el historial solicitado.',
        409: 'El alumno ya tiene una sesión abierta o hay un conflicto de edición.',
        413: 'La solicitud supera el tamaño permitido.',
        503: 'El servicio de entrenamiento no está disponible.',
    }.get(status, 'No se pudo completar la operación en el panel.')


def _hoy_post_invalido(alumno_id, accion):
    if not alumno_id or not alumno_id.isdigit():
        return 'ERROR|alumno_id invalido'
    if accion not in ('si', 'no', 'limpiar'):
        return 'ERROR|accion invalida'
    return None


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

    def _oficina_sesion_valida(self):
        cookie_header = self.headers.get('Cookie', '')
        for parte in cookie_header.split(';'):
            parte = parte.strip()
            if parte.startswith(OFICINA_COOKIE + '='):
                token = parte[len(OFICINA_COOKIE) + 1:]
                if token_oficina_valido(token):
                    return True
            if parte.startswith(CHAT_COOKIE + '='):
                token_c = parte[len(CHAT_COOKIE) + 1:]
                if token_chat_valido(token_c):
                    return True
        return False

    def _chat_sesion_valida(self):
        cookie_header = self.headers.get('Cookie', '')
        token = None
        for parte in cookie_header.split(';'):
            parte = parte.strip()
            if parte.startswith(CHAT_COOKIE + '='):
                token = parte[len(CHAT_COOKIE) + 1:]
                break
        return token_chat_valido(token)

    def do_HEAD(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path in ('/', '/index.html', '/oficina', '/oficina.html', '/rutina', '/rutina.html'):
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate, max-age=0')
            self.end_headers()
            return
        super().do_HEAD()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        qs = urllib.parse.parse_qs(parsed.query)

        if parsed.path in ('/', '/index.html'):
            ruta = os.path.join(DIRECTORY, 'index.html')
            try:
                with open(ruta, 'rb') as f:
                    body = f.read()
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.send_header('Content-Length', str(len(body)))
                self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate, max-age=0')
                self.send_header('Pragma', 'no-cache')
                self.send_header('Expires', '0')
                self.end_headers()
                self.wfile.write(body)
                return
            except Exception:
                pass

        if parsed.path in ('/oficina', '/oficina.html'):
            ruta = os.path.join(DIRECTORY, 'oficina.html')
            try:
                with open(ruta, 'rb') as f:
                    body = f.read()
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.send_header('Content-Length', str(len(body)))
                self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate, max-age=0')
                self.send_header('Pragma', 'no-cache')
                self.send_header('Expires', '0')
                self.end_headers()
                self.wfile.write(body)
                return
            except Exception:
                pass

        if parsed.path == '/rutina.html' or parsed.path == '/rutina':
            fecha = qs.get('fecha', [hoy()])[0]
            jornada = qs.get('jornada', [None])[0]
            if not es_fecha_valida(fecha):
                fecha = hoy()
            if jornada not in (None, 'AM', 'PM'):
                self.send_response(400)
                self.end_headers()
                return
            try:
                rutina = leer_rutina(fecha, jornada)
            except PanelError:
                self.send_response(502)
                self.end_headers()
                return
            jornada_label = jornada or 'HISTÓRICA'
            template_values = {
                'fecha': fecha,
                'rutina': html.escape(rutina),
                'jornada_etiqueta': jornada_label,
                'jornada_form': jornada or '',
                'seleccion_sin_jornada': 'selected' if jornada is None else '',
                'seleccion_am': 'selected' if jornada == 'AM' else '',
                'seleccion_pm': 'selected' if jornada == 'PM' else '',
                'aviso_legacy': '<div id="historialNotice">Vista histórica. Elige AM o PM y pulsa ABRIR antes de guardar.</div>' if jornada is None else '',
                'solo_lectura': 'readonly' if jornada is None else '',
                'guardar_deshabilitado': 'disabled' if jornada is None else '',
            }
            body = PAGE_TEMPLATE.format(**template_values).encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif parsed.path == '/api/rutina':
            fecha = qs.get('fecha', [hoy()])[0]
            jornada = qs.get('jornada', [None])[0]
            if not es_fecha_valida(fecha):
                self.send_response(400)
                self.end_headers()
                return
            if jornada not in (None, 'AM', 'PM', 'legacy'):
                self.send_response(400)
                self.end_headers()
                return
            try:
                datos = leer_rutina_datos(fecha, jornada)
                encontrada = bool(datos.get('encontrada', bool(datos.get('contenido', '').strip())))
                contenido = datos.get('contenido', '')
                if jornada == 'legacy' and not encontrada:
                    contenido = ''
                elif jornada in ('AM', 'PM') and not encontrada:
                    contenido = PLANTILLA_RUTINA
                body = contenido.encode('utf-8')
            except PanelError:
                self.send_response(502)
                self.end_headers()
                return
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.send_header('X-Rutina-Encontrada', '1' if encontrada else '0')
            self.send_header('X-Rutina-Jornada', jornada or 'compatibilidad')
            self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate, max-age=0')
            self.end_headers()
            self.wfile.write(body)
        elif parsed.path == '/api/rutina/dias':
            hoy_str = hoy()
            man_str = maniana()
            texto = 'HOY:' + hoy_str + '\n' + 'MANIANA:' + man_str + '\n' + 'DIAS:' + ','.join(dias_disponibles()) + '\n' + 'GUARDADOS:' + ','.join(dias_rutinas_guardadas())
            body = texto.encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif parsed.path == '/api/oficina':
            if not self._oficina_sesion_valida():
                self.send_response(401)
                self.end_headers()
                return
            try:
                body = leer_oficina().encode('utf-8')
            except PanelError:
                self.send_response(502)
                self.end_headers()
                return
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate, max-age=0')
            self.send_header('Pragma', 'no-cache')
            self.send_header('Expires', '0')
            self.end_headers()
            self.wfile.write(body)
        elif parsed.path == '/api/personalizados':
            if not self._oficina_sesion_valida():
                _responder_json(self, 401, {'ok': False, 'error': 'Sesión de Oficina requerida.'})
                return
            action = qs.get('action', ['alumnos'])[0]
            if action not in ('alumnos', 'historial'):
                _responder_json(self, 400, {'ok': False, 'error': 'Consulta no válida.'})
                return
            params = {'action': action}
            if action == 'historial':
                alumno_id = qs.get('alumnoId', [''])[0]
                if not alumno_id.isdigit() or int(alumno_id) < 1:
                    _responder_json(self, 400, {'ok': False, 'error': 'Alumno inválido.'})
                    return
                params['alumnoId'] = alumno_id
            try:
                status, response = panel_request('GET', '/api/ipad/entrenamiento', params=params)
                _responder_json(self, status, json.loads(response))
            except PanelError as e:
                status = e.status if 400 <= e.status < 600 else 502
                _responder_json(self, status, {'ok': False, 'error': _personal_error_message(status)})
            except (ValueError, TypeError):
                _responder_json(self, 502, {'ok': False, 'error': 'Respuesta inválida del panel.'})
        elif parsed.path == '/api/hoy':
            if not self._oficina_sesion_valida():
                self.send_response(401)
                self.end_headers()
                return
            horario_raw = qs.get('horario', [''])[0]
            horario = normalizar_horario(horario_raw)
            if horario is False:
                _responder_texto(self, 200, 'ERROR|horario invalido')
                return
            try:
                body = leer_hoy(horario).encode('utf-8')
            except PanelError:
                self.send_response(502)
                self.end_headers()
                return
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif parsed.path == '/api/chat-historial':
            if not self._chat_sesion_valida():
                self.send_response(401)
                self.end_headers()
                return
            body = nicola_historial_request().encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif parsed.path == '/api/antigravity-status':
            body = json.dumps(obtener_antigravity_status()).encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate, max-age=0')
            self.send_header('Pragma', 'no-cache')
            self.send_header('Expires', '0')
            self.end_headers()
            self.wfile.write(body)
        elif parsed.path == '/api/tasks':
            body = nicola_tasks_request().encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate, max-age=0')
            self.send_header('Pragma', 'no-cache')
            self.send_header('Expires', '0')
            self.end_headers()
            self.wfile.write(body)
        else:
            super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == '/guardar':
            length = int(self.headers.get('Content-Length', 0))
            raw = self.rfile.read(length).decode('utf-8')
            data = urllib.parse.parse_qs(raw)
            rutina = data.get('rutina', [''])[0]
            fecha = data.get('fecha', [hoy()])[0]
            jornada = data.get('jornada', [None])[0]
            if not es_fecha_valida(fecha):
                fecha = hoy()
            if jornada not in (None, 'AM', 'PM'):
                self.send_response(400)
                self.end_headers()
                return
            try:
                guardar_rutina(fecha, rutina, jornada)
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
                self.send_header('Location', '/rutina.html?fecha=' + fecha + ('&jornada=' + jornada if jornada else ''))
                self.end_headers()
        elif parsed.path == '/api/oficina-login':
            length = int(self.headers.get('Content-Length', 0))
            raw = self.rfile.read(length).decode('utf-8')
            data = urllib.parse.parse_qs(raw)
            password = data.get('password', [''])[0]
            es_valido_oficina = bool(OFICINA_PASSWORD and hmac.compare_digest(password, OFICINA_PASSWORD))
            es_valido_chat = bool(CHAT_PASSWORD and hmac.compare_digest(password, CHAT_PASSWORD))
            if es_valido_oficina or es_valido_chat:
                self.send_response(200)
                token_oficina = crear_token_oficina()
                cookie_oficina = '{}={}; Max-Age={}; Path=/; SameSite=Lax'.format(
                    OFICINA_COOKIE, token_oficina, OFICINA_SESION_SEGUNDOS
                )
                self.send_header('Set-Cookie', cookie_oficina)
                token_chat = crear_token_chat()
                cookie_chat = '{}={}; Max-Age={}; Path=/; SameSite=Lax'.format(
                    CHAT_COOKIE, token_chat, CHAT_SESION_SEGUNDOS
                )
                self.send_header('Set-Cookie', cookie_chat)
                self.send_header('Content-Length', '2')
                self.end_headers()
                self.wfile.write(b'ok')
            else:
                self.send_response(401)
                self.end_headers()
        elif parsed.path == '/api/oficina-logout':
            self.send_response(200)
            cookie_oficina = '{}=; Max-Age=0; Path=/; SameSite=Lax'.format(OFICINA_COOKIE)
            cookie_chat = '{}=; Max-Age=0; Path=/; SameSite=Lax'.format(CHAT_COOKIE)
            self.send_header('Set-Cookie', cookie_oficina)
            self.send_header('Set-Cookie', cookie_chat)
            self.send_header('Content-Length', '2')
            self.end_headers()
            self.wfile.write(b'ok')
        elif parsed.path == '/api/hoy':
            if not self._oficina_sesion_valida():
                length = int(self.headers.get('Content-Length', 0))
                if length > 0:
                    self.rfile.read(length)
                self.send_response(401)
                self.send_header('Content-Length', '0')
                self.end_headers()
                return
            length = int(self.headers.get('Content-Length', 0))
            raw = self.rfile.read(length).decode('utf-8')
            data = urllib.parse.parse_qs(raw)
            alumno_id = data.get('alumno_id', [''])[0]
            accion = data.get('accion', [''])[0]
            horario_raw = data.get('horario', [''])[0]
            horario = normalizar_horario(horario_raw)
            invalido = _hoy_post_invalido(alumno_id, accion)
            if invalido:
                _responder_texto(self, 200, invalido)
                return
            if horario is False:
                _responder_texto(self, 200, 'ERROR|horario invalido')
                return
            try:
                body = escribir_hoy(alumno_id, accion, horario)
            except PanelError as e:
                if e.detail.startswith('ERROR|'):
                    _responder_texto(self, 200, e.detail)
                else:
                    self.send_response(502)
                    self.end_headers()
                return
            _responder_texto(self, 200, body)
        elif parsed.path == '/api/personalizados':
            if not self._oficina_sesion_valida():
                length = int(self.headers.get('Content-Length', 0))
                if length > 0:
                    self.rfile.read(min(length, 128001))
                _responder_json(self, 401, {'ok': False, 'error': 'Sesión de Oficina requerida.'})
                return
            length = int(self.headers.get('Content-Length', 0))
            if length < 1 or length > 128000:
                if length > 0:
                    self.rfile.read(min(length, 128001))
                _responder_json(self, 413 if length > 128000 else 400,
                                {'ok': False, 'error': 'Tamaño de solicitud inválido.'})
                return
            try:
                payload = json.loads(self.rfile.read(length).decode('utf-8'))
            except (ValueError, UnicodeDecodeError):
                _responder_json(self, 400, {'ok': False, 'error': 'JSON inválido.'})
                return
            if not isinstance(payload, dict) or payload.get('action') not in (
                'crear_y_iniciar', 'iniciar_rutina', 'editar_ejercicios_sesion', 'registrar_serie', 'finalizar_sesion'
            ):
                _responder_json(self, 400, {'ok': False, 'error': 'Acción no válida.'})
                return
            try:
                status, response = panel_request('POST', '/api/ipad/entrenamiento', json_body=payload)
                _responder_json(self, status, json.loads(response))
            except PanelError as e:
                status = e.status if 400 <= e.status < 600 else 502
                _responder_json(self, status, {'ok': False, 'error': _personal_error_message(status)})
            except (ValueError, TypeError):
                _responder_json(self, 502, {'ok': False, 'error': 'Respuesta inválida del panel.'})
        elif parsed.path == '/api/chat-login':
            length = int(self.headers.get('Content-Length', 0))
            raw = self.rfile.read(length).decode('utf-8')
            data = urllib.parse.parse_qs(raw)
            password = data.get('password', [''])[0]
            if CHAT_PASSWORD and hmac.compare_digest(password, CHAT_PASSWORD):
                token = crear_token_chat()
                self.send_response(200)
                cookie = '{}={}; Max-Age={}; Path=/; SameSite=Lax'.format(
                    CHAT_COOKIE, token, CHAT_SESION_SEGUNDOS
                )
                self.send_header('Set-Cookie', cookie)
                self.send_header('Content-Length', '2')
                self.end_headers()
                self.wfile.write(b'ok')
            else:
                self.send_response(401)
                self.end_headers()
        elif parsed.path == '/api/chat-logout':
            self.send_response(200)
            cookie = '{}=; Max-Age=0; Path=/; SameSite=Lax'.format(CHAT_COOKIE)
            self.send_header('Set-Cookie', cookie)
            self.send_header('Content-Length', '2')
            self.end_headers()
            self.wfile.write(b'ok')
        elif parsed.path == '/api/chat':
            if not self._chat_sesion_valida():
                self.send_response(401)
                self.end_headers()
                return
            length = int(self.headers.get('Content-Length', 0))
            raw = self.rfile.read(length).decode('utf-8', errors='ignore')
            data = urllib.parse.parse_qs(raw)
            mensaje = data.get('mensaje', [''])[0].strip() or data.get('message', [''])[0].strip()
            if not mensaje and raw.strip().startswith('{'):
                try:
                    jdata = json.loads(raw)
                    mensaje = (jdata.get('mensaje') or jdata.get('message') or '').strip()
                except Exception:
                    pass
            if not mensaje:
                _responder_texto(self, 400, 'ERROR|mensaje requerido')
                return
            reply = nicola_chat_request(mensaje)
            _responder_texto(self, 200, reply)
        elif parsed.path == '/api/generar-rutina':
            length = int(self.headers.get('Content-Length', 0))
            raw = self.rfile.read(length).decode('utf-8', errors='ignore')
            data = urllib.parse.parse_qs(raw)
            fecha = data.get('fecha', [hoy()])[0]
            jornada = data.get('jornada', [None])[0]
            if not es_fecha_valida(fecha):
                fecha = hoy()
            if jornada not in (None, 'AM', 'PM'):
                self.send_response(400)
                self.end_headers()
                return

            # 1. Intentar generar vía API de ironcross-dashboard
            try:
                payload = {'fecha': fecha}
                if jornada:
                    payload['jornada'] = jornada
                status, body = panel_request('POST', '/api/rutina/generar', json_body=payload)
                if status == 200:
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json; charset=utf-8')
                    body_b = body.encode('utf-8')
                    self.send_header('Content-Length', str(len(body_b)))
                    self.end_headers()
                    self.wfile.write(body_b)
                    return
            except Exception:
                pass

            # 2. Fallback: solicitar a Nicola OS / IronBot
            prompt = f"IronBot, crea la rutina de la clase del {fecha}" + (f" jornada {jornada}" if jornada else "") + " basada en los entrenamientos registrados"
            reply = nicola_chat_request(prompt)
            try:
                rutina_guardada = leer_rutina(fecha, jornada)
                if rutina_guardada and 'CALENTAMIENTO' in rutina_guardada:
                    resp_json = json.dumps({'ok': True, 'rutina': rutina_guardada, 'fuente': 'Nicola OS / IronBot'})
                else:
                    resp_json = json.dumps({'ok': True, 'rutina': reply, 'fuente': 'Nicola OS / IronBot'})
            except Exception:
                resp_json = json.dumps({'ok': True, 'rutina': reply, 'fuente': 'Nicola OS / IronBot'})

            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            body_b = resp_json.encode('utf-8')
            self.send_header('Content-Length', str(len(body_b)))
            self.end_headers()
            self.wfile.write(body_b)
        elif parsed.path == '/api/tasks':
            length = int(self.headers.get('Content-Length', 0))
            raw = self.rfile.read(length)
            body = nicola_create_task_request(raw).encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate, max-age=0')
            self.end_headers()
            self.wfile.write(body)
        elif parsed.path.startswith('/api/tasks/') and parsed.path.endswith('/status'):
            partes = parsed.path.split('/')
            tarea_id = partes[3] if len(partes) >= 4 else ''
            length = int(self.headers.get('Content-Length', 0))
            raw = self.rfile.read(length).decode('utf-8', errors='ignore')
            nuevo_estado = 'En progreso'
            try:
                j = json.loads(raw)
                nuevo_estado = j.get('nuevo_estado', nuevo_estado)
            except Exception:
                pass
            body = nicola_update_task_status_request(tarea_id, nuevo_estado).encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate, max-age=0')
            self.end_headers()
            self.wfile.write(body)
        elif parsed.path.startswith('/api/tasks/') and parsed.path.endswith('/execute'):
            partes = parsed.path.split('/')
            tarea_id = partes[3] if len(partes) >= 4 else ''
            url = f"{NICOLA_DASHBOARD_URL}/api/tasks/{tarea_id}/execute"
            req = urllib.request.Request(url, data=b'{}', headers={'Content-Type': 'application/json'}, method='POST')
            try:
                with urllib.request.urlopen(req, timeout=20) as resp:
                    body = resp.read()
            except Exception as e:
                body = json.dumps({"status": "error", "error": str(e)}).encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate, max-age=0')
            self.end_headers()
            self.wfile.write(body)
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
