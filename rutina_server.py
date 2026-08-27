#!/usr/bin/env python3
import http.server
import socketserver
import os
import html
import subprocess
import urllib.parse
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

PORT = 8090
DIRECTORY = '/home/ubuntu/reloj'
TZ = ZoneInfo('America/Santiago')
PSQL = ['docker', 'exec', '-i', 'n8n-postgres-1', 'psql', '-U', 'ironcross', '-d', 'ironcross',
        '-v', 'ON_ERROR_STOP=1', '-t', '-A']

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


def psql_query(sql, variables):
    args = list(PSQL)
    for k, v in variables.items():
        args += ['-v', '{}={}'.format(k, v)]
    result = subprocess.run(args, input=sql, capture_output=True, text=True, timeout=10)
    if result.returncode != 0:
        raise RuntimeError(result.stderr)
    return result.stdout


PLANTILLA_RUTINA = 'PREPARACION\n\nCALENTAMIENTO\n\nPIERNAS\n\nELONGACION\n\nCORE\n\nPOSTURAS\n\nSUPER SET\n\nELONGACION\n'


def leer_rutina(fecha):
    sql = "SELECT contenido FROM rutinas WHERE fecha = :'fecha';"
    out = psql_query(sql, {'fecha': fecha})
    if out.endswith('\n'):
        out = out[:-1]
    if not out.strip():
        return PLANTILLA_RUTINA
    return out


def guardar_rutina(fecha, contenido):
    sql = ("INSERT INTO rutinas (fecha, contenido) VALUES (:'fecha', :'contenido') "
           "ON CONFLICT (fecha) DO UPDATE SET contenido = EXCLUDED.contenido;")
    psql_query(sql, {'fecha': fecha, 'contenido': contenido})


def listar_dias():
    sql = "SELECT to_char(fecha, 'YYYY-MM-DD') FROM rutinas ORDER BY fecha DESC LIMIT 30;"
    out = psql_query(sql, {})
    return [line for line in out.split('\n') if line.strip()]



def leer_oficina():
    """Text protocol for the iPad GYM tab. Skip canje (never show those in cobranza)."""
    sql_counts = """
WITH ranked AS (
  SELECT pa.alumno_id, p.estado, p.medio_pago,
    row_number() OVER (
      PARTITION BY pa.alumno_id
      ORDER BY CASE p.estado
        WHEN 'vencido' THEN 1 WHEN 'por_vencer' THEN 2 WHEN 'perdido' THEN 3 WHEN 'activo' THEN 4 END
    ) AS rn
  FROM plan_alumnos pa
  JOIN planes p ON p.id = pa.plan_id
  WHERE coalesce(p.medio_pago, '') <> 'canje'
)
SELECT
  (SELECT count(DISTINCT alumno_id) FROM ranked WHERE rn = 1 AND estado IN ('activo','por_vencer')) AS activos,
  (SELECT count(DISTINCT alumno_id) FROM ranked WHERE rn = 1 AND estado = 'vencido') AS vencidos,
  (SELECT count(DISTINCT alumno_id) FROM ranked WHERE rn = 1 AND estado = 'por_vencer') AS por_vencer,
  (SELECT count(*) FROM alumnos a WHERE NOT EXISTS (SELECT 1 FROM plan_alumnos pa WHERE pa.alumno_id = a.id)) AS sin_plan;
"""
    sql_rows = """
WITH ranked AS (
  SELECT pa.alumno_id, p.estado, p.monto_plan, p.fecha_vencimiento,
    row_number() OVER (
      PARTITION BY pa.alumno_id
      ORDER BY CASE p.estado
        WHEN 'vencido' THEN 1 WHEN 'por_vencer' THEN 2 WHEN 'perdido' THEN 3 WHEN 'activo' THEN 4 END
    ) AS rn
  FROM plan_alumnos pa
  JOIN planes p ON p.id = pa.plan_id
  WHERE coalesce(p.medio_pago, '') <> 'canje'
)
SELECT a.nombre,
       r.estado,
       coalesce(to_char(r.monto_plan, 'FM999999990'), ''),
       coalesce(to_char(r.fecha_vencimiento, 'DD/MM'), '')
FROM alumnos a
JOIN ranked r ON r.alumno_id = a.id AND r.rn = 1
WHERE r.estado IN ('vencido', 'por_vencer')
ORDER BY CASE r.estado WHEN 'vencido' THEN 1 ELSE 2 END, a.nombre;
"""
    counts_out = psql_query(sql_counts, {}).strip()
    # activos|vencidos|por_vencer|sin_plan
    parts = counts_out.split('|') if counts_out else ['0','0','0','0']
    while len(parts) < 4:
        parts.append('0')
    lines = [
        'C|activos|' + parts[0],
        'C|vencidos|' + parts[1],
        'C|por_vencer|' + parts[2],
        'C|sin_plan|' + parts[3],
    ]
    rows_out = psql_query(sql_rows, {}).strip()
    if rows_out:
        for line in rows_out.split('\n'):
            cols = line.split('|')
            if len(cols) < 2:
                continue
            nombre = cols[0]
            estado = cols[1]
            monto = cols[2] if len(cols) > 2 else ''
            vence = cols[3] if len(cols) > 3 else ''
            tag = 'V' if estado == 'vencido' else 'P'
            lines.append('R|' + tag + '|' + nombre + '|' + monto + '|' + vence)
    return '\n'.join(lines)


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
            body = PAGE_TEMPLATE.format(
                fecha=fecha,
                rutina=html.escape(leer_rutina(fecha))
            ).encode('utf-8')
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
            body = leer_rutina(fecha).encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif parsed.path == '/api/rutina/dias':
            hoy_str = hoy()
            man_str = maniana()
            dias = set(listar_dias())
            dias.add(hoy_str)
            dias.add(man_str)
            dias = sorted(dias, reverse=True)
            texto = 'HOY:' + hoy_str + '\n' + 'MANIANA:' + man_str + '\n' + 'DIAS:' + ','.join(dias)
            body = texto.encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif parsed.path == '/api/oficina':
            try:
                body = leer_oficina().encode('utf-8')
            except Exception:
                self.send_response(500)
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
            guardar_rutina(fecha, rutina)
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
    with Server(('0.0.0.0', PORT), Handler) as httpd:
        print('Serving on port', PORT)
        httpd.serve_forever()
