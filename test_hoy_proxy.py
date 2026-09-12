#!/usr/bin/env python3
"""Prueba el proxy /api/hoy contra un panel falso (sin red, sin iPad)."""
import http.client
import http.server
import json
import os
import socketserver
import threading
import time
import unittest
import urllib.parse

import rutina_server


SAMPLE_HOY = '\n'.join([
    'C|si|1',
    'C|no|1',
    'C|sin|1',
    'R|12|Ana Perez|si|whatsapp',
    'R|13|Bruno Soto||-',
    'U|Invitado|no|lista',
]) + '\n'


class MockPanel(http.server.BaseHTTPRequestHandler):
    store = {'body': SAMPLE_HOY, 'last_post': None, 'auth': None, 'post_status': 200, 'post_body': 'OK'}

    def log_message(self, format, *args):
        pass

    def _check_auth(self):
        auth = self.headers.get('Authorization', '')
        self.store['auth'] = auth
        if auth != 'Bearer test-token':
            self.send_response(401)
            self.end_headers()
            self.wfile.write(b'unauthorized')
            return False
        return True

    def do_GET(self):
        if not self._check_auth():
            return
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path != '/api/hoy':
            self.send_response(404)
            self.end_headers()
            return
        body = self.store['body'].encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'text/plain; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if not self._check_auth():
            return
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path != '/api/hoy':
            self.send_response(404)
            self.end_headers()
            return
        length = int(self.headers.get('Content-Length', 0))
        raw = self.rfile.read(length).decode('utf-8')
        self.store['last_post'] = {
            'raw': raw,
            'ctype': self.headers.get('Content-Type', ''),
            'data': urllib.parse.parse_qs(raw),
        }
        body = self.store['post_body'].encode('utf-8')
        self.send_response(self.store['post_status'])
        self.send_header('Content-Type', 'text/plain; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class ThreadingHTTPServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True


class HoyProxyTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.panel = ThreadingHTTPServer(('127.0.0.1', 0), MockPanel)
        cls.panel_port = cls.panel.server_address[1]
        cls.panel_thread = threading.Thread(target=cls.panel.serve_forever, daemon=True)
        cls.panel_thread.start()

        rutina_server.PANEL_API_URL = 'http://127.0.0.1:{}'.format(cls.panel_port)
        rutina_server.IPAD_API_TOKEN = 'test-token'
        rutina_server.OFICINA_PASSWORD = 'clave-test'
        rutina_server.OFICINA_SESSION_SECRET = 'secret-test-secret-test'

        cls.app = ThreadingHTTPServer(('127.0.0.1', 0), rutina_server.Handler)
        cls.app_port = cls.app.server_address[1]
        cls.app_thread = threading.Thread(target=cls.app.serve_forever, daemon=True)
        cls.app_thread.start()
        time.sleep(0.1)

    @classmethod
    def tearDownClass(cls):
        cls.app.shutdown()
        cls.panel.shutdown()

    def setUp(self):
        MockPanel.store['body'] = SAMPLE_HOY
        MockPanel.store['last_post'] = None
        MockPanel.store['post_status'] = 200
        MockPanel.store['post_body'] = 'OK'

    def _req(self, method, path, body=None, headers=None, cookie=None):
        conn = http.client.HTTPConnection('127.0.0.1', self.app_port, timeout=5)
        hdrs = headers or {}
        if cookie:
            hdrs['Cookie'] = cookie
        if body is not None:
            hdrs.setdefault('Content-Type', 'application/x-www-form-urlencoded')
            payload = body.encode('utf-8')
            hdrs['Content-Length'] = str(len(payload))
            conn.request(method, path, payload, hdrs)
        else:
            conn.request(method, path, headers=hdrs)
        resp = conn.getresponse()
        data = resp.read().decode('utf-8')
        set_cookie = resp.getheader('Set-Cookie')
        conn.close()
        return resp.status, data, set_cookie

    def _login(self):
        status, body, set_cookie = self._req('POST', '/api/oficina-login', 'password=clave-test')
        self.assertEqual(status, 200, body)
        self.assertTrue(set_cookie)
        token = set_cookie.split(';')[0]
        return token

    def test_hoy_get_sin_sesion_es_401(self):
        status, _, _ = self._req('GET', '/api/hoy')
        self.assertEqual(status, 401)

    def test_hoy_post_sin_sesion_es_401(self):
        status, _, _ = self._req('POST', '/api/hoy', 'alumno_id=12&accion=si')
        self.assertEqual(status, 401)

    def test_hoy_get_proxea_texto_y_bearer(self):
        cookie = self._login()
        status, body, _ = self._req('GET', '/api/hoy', cookie=cookie)
        self.assertEqual(status, 200)
        self.assertIn('C|si|1', body)
        self.assertIn('R|12|Ana Perez|si|whatsapp', body)
        self.assertIn('U|Invitado|no|lista', body)
        self.assertEqual(MockPanel.store['auth'], 'Bearer test-token')

    def test_hoy_post_form_urlencoded_ok(self):
        cookie = self._login()
        status, body, _ = self._req('POST', '/api/hoy', 'alumno_id=12&accion=si', cookie=cookie)
        self.assertEqual(status, 200)
        self.assertEqual(body, 'OK')
        last = MockPanel.store['last_post']
        self.assertIsNotNone(last)
        self.assertIn('application/x-www-form-urlencoded', last['ctype'])
        self.assertEqual(last['data'].get('alumno_id'), ['12'])
        self.assertEqual(last['data'].get('accion'), ['si'])

    def test_hoy_post_limpia_y_rechaza_accion_rara(self):
        cookie = self._login()
        status, body, _ = self._req('POST', '/api/hoy', 'alumno_id=12&accion=limpiar', cookie=cookie)
        self.assertEqual(status, 200)
        self.assertEqual(body, 'OK')
        MockPanel.store['last_post'] = None
        status, body, _ = self._req('POST', '/api/hoy', 'alumno_id=12&accion=talvez', cookie=cookie)
        self.assertEqual(status, 200)
        self.assertEqual(body, 'ERROR|accion invalida')
        self.assertIsNone(MockPanel.store['last_post'])

    def test_hoy_post_reenvia_error_del_panel(self):
        cookie = self._login()
        MockPanel.store['post_status'] = 400
        MockPanel.store['post_body'] = 'ERROR|alumno no encontrado'
        status, body, _ = self._req('POST', '/api/hoy', 'alumno_id=99&accion=no', cookie=cookie)
        self.assertEqual(status, 200)
        self.assertEqual(body, 'ERROR|alumno no encontrado')

    def test_index_tiene_tab_hoy_es5(self):
        here = os.path.dirname(os.path.abspath(__file__))
        with open(os.path.join(here, 'index.html'), encoding='utf-8') as fh:
            html = fh.read()
        self.assertIn('id="tabHoy"', html)
        self.assertIn('id="hoyView"', html)
        self.assertIn("xhr.open('GET', '/api/hoy'", html)
        self.assertIn("xhr.open('POST', '/api/hoy'", html)
        self.assertNotIn('fetch(', html.split('hoy / asistencia')[1].split('---------- rutina')[0])
        self.assertNotIn('flex', html.lower().split('hoy / asistencia view')[1].split('stopwatch view')[0])


if __name__ == '__main__':
    unittest.main()
