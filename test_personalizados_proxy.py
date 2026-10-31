"""Contratos de solo servidor para el puente autenticado de rutinas personales."""
import http.client
import json
import socketserver
import threading
import unittest
from unittest.mock import patch

import rutina_server


class ThreadingHTTPServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True


class PersonalizadosProxyTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), rutina_server.Handler)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def request(self, method, path, body=None, authenticated=False):
        connection = http.client.HTTPConnection('127.0.0.1', self.port, timeout=3)
        headers = {}
        if authenticated:
            headers['Cookie'] = '{}={}'.format(rutina_server.OFICINA_COOKIE, rutina_server.crear_token_oficina())
        if body is not None:
            headers['Content-Type'] = 'application/json'
        connection.request(method, path, body=body, headers=headers)
        response = connection.getresponse()
        result = response.status, response.read().decode('utf-8'), dict(response.getheaders())
        connection.close()
        return result

    @patch.object(rutina_server, 'panel_request')
    def test_get_de_alumnos_requiere_sesion_y_usa_proxy_secreto(self, panel):
        panel.return_value = (200, '{"ok":true,"alumnos":[{"id":7001,"nombre":"Fixture"}]}')
        status, _body, _headers = self.request('GET', '/api/personalizados?action=alumnos')
        self.assertEqual(status, 401)
        panel.assert_not_called()

        status, body, headers = self.request('GET', '/api/personalizados?action=alumnos', authenticated=True)
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)['alumnos'][0]['id'], 7001)
        self.assertEqual(headers.get('Cache-Control'), 'no-store, max-age=0')
        panel.assert_called_once_with('GET', '/api/ipad/entrenamiento', params={'action': 'alumnos'})

    @patch.object(rutina_server, 'panel_request')
    def test_post_solo_reenvia_acciones_permitidas_y_no_filtra_error_remoto(self, panel):
        payload = {'action': 'registrar_serie', 'alumnoId': 7001, 'sesionId': 'synthetic-session'}
        panel.return_value = (200, '{"ok":true,"sesion":{"id":"synthetic-session"}}')
        status, body, _headers = self.request('POST', '/api/personalizados', json.dumps(payload), authenticated=True)
        self.assertEqual(status, 200)
        self.assertTrue(json.loads(body)['ok'])
        panel.assert_called_once_with('POST', '/api/ipad/entrenamiento', json_body=payload)

        panel.reset_mock()
        bad = {'action': 'arbitrary_admin_action', 'secret': 'must-not-forward'}
        status, _body, _headers = self.request('POST', '/api/personalizados', json.dumps(bad), authenticated=True)
        self.assertEqual(status, 400)
        panel.assert_not_called()

    @patch.object(rutina_server, 'panel_request')
    def test_post_sin_sesion_no_escribe_y_errores_remotos_salen_redactados(self, panel):
        payload = {'action': 'crear_y_iniciar', 'alumnoId': 7001, 'titulo': 'Fixture'}
        status, _body, _headers = self.request('POST', '/api/personalizados', json.dumps(payload))
        self.assertEqual(status, 401)
        panel.assert_not_called()

        panel.side_effect = rutina_server.PanelError(409, '{"error":"mensaje privado que no se debe devolver"}')
        status, body, _headers = self.request('POST', '/api/personalizados', json.dumps(payload), authenticated=True)
        self.assertEqual(status, 409)
        self.assertNotIn('mensaje privado', body)
        self.assertEqual(json.loads(body)['error'], 'El alumno ya tiene una sesión abierta o hay un conflicto de edición.')

    @patch.object(rutina_server, 'panel_request')
    def test_get_historial_valida_identificador_antes_de_consultar_panel(self, panel):
        status, _body, _headers = self.request(
            'GET', '/api/personalizados?action=historial&alumnoId=../otro', authenticated=True
        )
        self.assertEqual(status, 400)
        panel.assert_not_called()


if __name__ == '__main__':
    unittest.main()
