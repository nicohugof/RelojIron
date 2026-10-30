"""Regresiones del proxy de rutinas AM/PM sin red ni datos reales."""
import http.client
import json
from pathlib import Path
import socketserver
import threading
import unittest
from unittest.mock import call
from unittest.mock import patch

import rutina_server


class ThreadingHTTPServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True


class RutinaAmPmTest(unittest.TestCase):
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

    def request(self, method, path, body=None):
        conn = http.client.HTTPConnection('127.0.0.1', self.port, timeout=3)
        headers = {}
        if body is not None:
            headers['Content-Type'] = 'application/x-www-form-urlencoded'
            headers['X-Requested-With'] = 'XMLHttpRequest'
        conn.request(method, path, body=body, headers=headers)
        response = conn.getresponse()
        result = response.status, response.read().decode('utf-8'), dict(response.getheaders())
        conn.close()
        return result

    @patch.object(rutina_server, 'panel_request')
    def test_get_jornada_seleccionada_se_delega_y_expone_si_existe(self, panel):
        panel.return_value = (200, json.dumps({
            'fecha': '2026-10-29', 'jornada': 'PM', 'contenido': 'RUTINA PM', 'encontrada': True
        }))

        status, body, headers = self.request('GET', '/api/rutina?fecha=2026-10-29&jornada=PM')

        self.assertEqual(status, 200)
        self.assertEqual(body, 'RUTINA PM')
        self.assertEqual(headers.get('X-Rutina-Encontrada'), '1')
        panel.assert_called_once_with('GET', '/api/rutina', params={
            'fecha': '2026-10-29', 'jornada': 'PM'
        })

    @patch.object(rutina_server, 'panel_request')
    def test_get_legacy_sin_jornada_no_se_presenta_como_am_o_pm(self, panel):
        panel.return_value = (200, json.dumps({
            'fecha': '2026-10-29', 'jornada': 'legacy', 'contenido': 'RUTINA LEGACY', 'encontrada': True
        }))

        status, body, headers = self.request('GET', '/api/rutina?fecha=2026-10-29&jornada=legacy')

        self.assertEqual(status, 200)
        self.assertEqual(body, 'RUTINA LEGACY')
        self.assertEqual(headers.get('X-Rutina-Encontrada'), '1')
        panel.assert_called_once_with('GET', '/api/rutina', params={
            'fecha': '2026-10-29', 'jornada': 'legacy'
        })

    @patch.object(rutina_server, 'panel_request')
    def test_get_no_clasifica_como_am_si_panel_ignora_el_parametro(self, panel):
        panel.return_value = (200, json.dumps({
            'fecha': '2026-10-29', 'contenido': 'rutina legacy de API antigua'
        }))

        status, _body, _headers = self.request('GET', '/api/rutina?fecha=2026-10-29&jornada=AM')

        self.assertEqual(status, 502)
        panel.assert_called_once_with('GET', '/api/rutina', params={
            'fecha': '2026-10-29', 'jornada': 'AM'
        })

    @patch.object(rutina_server, 'panel_request')
    def test_historial_vacio_no_devuelve_plantilla_como_si_existiera(self, panel):
        panel.return_value = (200, json.dumps({
            'fecha': '2026-10-29', 'jornada': 'legacy',
            'contenido': 'PREPARACION\n\nCALENTAMIENTO', 'encontrada': False,
        }))

        status, body, headers = self.request('GET', '/api/rutina?fecha=2026-10-29&jornada=legacy')

        self.assertEqual(status, 200)
        self.assertEqual(body, '')
        self.assertEqual(headers.get('X-Rutina-Encontrada'), '0')

    @patch.object(rutina_server, 'panel_request')
    def test_post_am_pm_persiste_la_jornada_explicita(self, panel):
        panel.side_effect = [
            (200, json.dumps({
                'fecha': '2026-10-29', 'jornada': 'PM', 'contenido': '', 'encontrada': False
            })),
            (200, '{"ok":true,"jornada":"PM"}'),
        ]

        status, body, _headers = self.request(
            'POST', '/guardar', 'fecha=2026-10-29&jornada=PM&rutina=RUTINA+PM'
        )

        self.assertEqual((status, body), (200, 'ok'))
        self.assertEqual(panel.call_args_list, [
            call('GET', '/api/rutina', params={'fecha': '2026-10-29', 'jornada': 'PM'}),
            call('POST', '/api/rutina', json_body={
                'fecha': '2026-10-29', 'contenido': 'RUTINA PM', 'jornada': 'PM'
            }),
        ])

    @patch.object(rutina_server, 'panel_request')
    def test_no_guarda_en_api_antigua_que_no_confirma_jornada(self, panel):
        panel.return_value = (200, json.dumps({'fecha': '2026-10-29', 'contenido': 'rutina histórica'}))

        status, _body, _headers = self.request(
            'POST', '/guardar', 'fecha=2026-10-29&jornada=AM&rutina=NO+CLASIFICAR'
        )

        self.assertEqual(status, 502)
        panel.assert_called_once_with('GET', '/api/rutina', params={
            'fecha': '2026-10-29', 'jornada': 'AM'
        })

    @patch.object(rutina_server, 'panel_request')
    def test_cliente_antiguo_sin_jornada_conserva_payload_legacy(self, panel):
        panel.return_value = (200, '{"ok":true}')

        status, body, _headers = self.request(
            'POST', '/guardar', 'fecha=2026-10-29&rutina=RUTINA+HISTORICA'
        )

        self.assertEqual((status, body), (200, 'ok'))
        panel.assert_called_once_with('POST', '/api/rutina', json_body={
            'fecha': '2026-10-29', 'contenido': 'RUTINA HISTORICA'
        })

    @patch.object(rutina_server, 'panel_request')
    def test_no_permite_guardar_historial_legacy_como_si_fuera_jornada(self, panel):
        status, _body, _headers = self.request(
            'POST', '/guardar', 'fecha=2026-10-29&jornada=legacy&rutina=RUTINA'
        )

        self.assertEqual(status, 400)
        panel.assert_not_called()

    def test_ui_simplifica_jornadas_y_recupera_legacy_desde_calendario(self):
        source = Path(rutina_server.DIRECTORY, 'index.html').read_text(encoding='utf-8')
        self.assertIn('id="rutinaJornadaAM"', source)
        self.assertIn('id="rutinaJornadaPM"', source)
        self.assertNotIn('id="rutinaJornadaLegacy"', source)
        self.assertNotIn('>HISTORIAL</div>', source)
        self.assertIn('MAR / JUE · 07:00', source)
        self.assertIn('LUN–VIE · 19:30', source)
        self.assertIn('function jornadaHabitualPorDia(dia, hora)', source)
        self.assertIn('if (dia === 2 || dia === 4)', source)
        self.assertIn('if (dia >= 1 && dia <= 5)', source)
        self.assertIn("'&jornada=' + encodeURIComponent(jornadaSeleccionada)", source)
        self.assertIn("'&jornada=legacy'", source)
        self.assertIn('function cargarRutinaAntigua(fecha)', source)
        self.assertIn('rutinaText.readOnly = rutinaViendoLegacy', source)
        self.assertIn('EDITAR COPIA AM', source)
        self.assertIn('EDITAR COPIA PM', source)


if __name__ == '__main__':
    unittest.main()
