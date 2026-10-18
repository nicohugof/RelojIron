"""
Test de resiliencia de autenticación unificada en RelojIron.
Verifica que el servidor no quede en loop de 401 ni expulse al iPad.
"""
import unittest
from unittest.mock import patch
import os
import http.client
import threading
import time
import socketserver
import rutina_server


class TestOficinaAuthResilience(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.port = 18092
        # Forzar un servidor de pruebas en puerto local
        class TCPServerReuse(socketserver.TCPServer):
            allow_reuse_address = True

        cls.httpd = TCPServerReuse(('127.0.0.1', cls.port), rutina_server.Handler)
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()
        time.sleep(0.1)

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()

    def test_login_emits_both_cookies_and_unlocks_oficina(self):
        conn = http.client.HTTPConnection('127.0.0.1', self.port)
        # 1. Sin cookie da 401
        conn.request('GET', '/api/oficina')
        resp = conn.getresponse()
        resp.read()
        self.assertEqual(resp.status, 401)

        # 2. Login con clave
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        conn.request('POST', '/api/oficina-login', 'password=2799706', headers)
        login_resp = conn.getresponse()
        body = login_resp.read().decode('utf-8')
        self.assertEqual(login_resp.status, 200)
        self.assertEqual(body, 'ok')

        # Verificar que Set-Cookie contiene ambas cookies
        cookie_headers = [v for k, v in login_resp.getheaders() if k.lower() == 'set-cookie']
        all_cookies = '; '.join(cookie_headers)
        self.assertIn('oficina_session=', all_cookies)
        self.assertIn('chat_session=', all_cookies)

        # 3. Con la cookie de oficina, /api/oficina ya no responde 401
        # Mockeamos leer_oficina para no requerir conexion a Postgres
        with patch.object(rutina_server, 'leer_oficina', return_value='C|activos|10\nR|V|Test|1000|18/10'):
            conn.request('GET', '/api/oficina', headers={'Cookie': all_cookies})
            oficina_resp = conn.getresponse()
            content = oficina_resp.read().decode('utf-8')
            self.assertEqual(oficina_resp.status, 200)
            self.assertIn('Test', content)


if __name__ == '__main__':
    unittest.main()
