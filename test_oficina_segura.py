import http.client
import json
import os
import time
import unittest
from unittest.mock import patch
import rutina_server


class TestOficinaSegura(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Iniciar servidor de prueba en puerto efímero
        rutina_server.OFICINA_PASSWORD = 'clave-secreta-oficina-123'
        rutina_server.OFICINA_SESSION_SECRET = 'secreto-seguro-oficina-test-456'
        cls.server = http.server.HTTPServer(('127.0.0.1', 0), rutina_server.Handler)
        cls.port = cls.server.server_address[1]

        import threading
        cls.thread = threading.Thread(target=cls.server.serve_forever)
        cls.thread.daemon = True
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def test_01_sin_sesion_da_401_en_cobranzas(self):
        conn = http.client.HTTPConnection('127.0.0.1', self.port)
        conn.request('GET', '/api/cobranzas')
        resp = conn.getresponse()
        resp.read()
        self.assertEqual(resp.status, 401)

    def test_02_oficina_check_indica_no_autenticado_sin_cookie(self):
        conn = http.client.HTTPConnection('127.0.0.1', self.port)
        conn.request('GET', '/api/oficina-check')
        resp = conn.getresponse()
        data = json.loads(resp.read().decode('utf-8'))
        self.assertEqual(resp.status, 200)
        self.assertEqual(data.get('autenticado'), False)

    def test_03_login_con_clave_incorrecta_rechaza_401(self):
        conn = http.client.HTTPConnection('127.0.0.1', self.port)
        headers = {'Content-Type': 'application/json'}
        conn.request('POST', '/api/oficina-login', json.dumps({'password': 'clave-falsa'}), headers)
        resp = conn.getresponse()
        self.assertEqual(resp.status, 401)

    def test_04_login_correcto_emite_cookies_httponly_y_desbloquea(self):
        conn = http.client.HTTPConnection('127.0.0.1', self.port)
        headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}
        conn.request('POST', '/api/oficina-login', json.dumps({'password': 'clave-secreta-oficina-123'}), headers)
        resp = conn.getresponse()
        body = json.loads(resp.read().decode('utf-8'))
        self.assertEqual(resp.status, 200)
        self.assertEqual(body.get('ok'), True)

        # Verificar cookies HttpOnly
        set_cookies = resp.headers.get_all('Set-Cookie') if hasattr(resp.headers, 'get_all') else [resp.headers.get('Set-Cookie')]
        all_cookies = ' '.join(set_cookies)
        self.assertIn('oficina_session=', all_cookies)
        self.assertIn('HttpOnly', all_cookies)
        self.assertIn('SameSite=Lax', all_cookies)

        # Extraer cookie
        cookie_header = ''
        for sc in set_cookies:
            if 'oficina_session=' in sc:
                cookie_header = sc.split(';')[0]
                break
        self.assertTrue(bool(cookie_header))

        # Verificar oficina-check con cookie
        conn.request('GET', '/api/oficina-check', headers={'Cookie': cookie_header})
        check_resp = conn.getresponse()
        check_data = json.loads(check_resp.read().decode('utf-8'))
        self.assertEqual(check_data.get('autenticado'), True)

        # Mock de respuesta del dashboard para /api/cobranzas
        with patch('rutina_server.leer_cobranzas', return_value=(200, '{"ok":true,"kpis":{},"alumnos":[]}')):
            conn.request('GET', '/api/cobranzas', headers={'Cookie': cookie_header})
            cob_resp = conn.getresponse()
            cob_data = json.loads(cob_resp.read().decode('utf-8'))
            self.assertEqual(cob_resp.status, 200)
            self.assertEqual(cob_data.get('ok'), True)

    def test_05_logout_revoca_sesion_inmediatamente(self):
        conn = http.client.HTTPConnection('127.0.0.1', self.port)
        # Login
        conn.request('POST', '/api/oficina-login', 'password=clave-secreta-oficina-123',
                     {'Content-Type': 'application/x-www-form-urlencoded'})
        login_resp = conn.getresponse()
        sc = login_resp.headers.get('Set-Cookie', '')
        cookie_str = sc.split(';')[0]
        login_resp.read()

        # Logout
        conn.request('POST', '/api/oficina-logout', '', {'Cookie': cookie_str})
        logout_resp = conn.getresponse()
        logout_resp.read()
        self.assertEqual(logout_resp.status, 200)

        # Verificar revocación de cookies
        del_cookies = logout_resp.headers.get('Set-Cookie', '')
        self.assertIn('Max-Age=0', del_cookies)

        # Ya no puede acceder
        conn.request('GET', '/api/oficina-check')
        c_resp = conn.getresponse()
        c_data = json.loads(c_resp.read().decode('utf-8'))
        self.assertEqual(c_data.get('autenticado'), False)


if __name__ == '__main__':
    unittest.main()
