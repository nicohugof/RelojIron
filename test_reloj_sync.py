import json
import unittest
from unittest.mock import patch
import rutina_server


class TestRelojSync(unittest.TestCase):

    def test_leer_reloj_estado_llama_al_panel(self):
        mock_body = json.dumps({
            "ok": True,
            "state": {
                "id": "piso_ironcross",
                "modo": "cronometro",
                "estado": "running",
                "version": 4,
            },
            "serverTime": 1730000000,
        })
        with patch.object(rutina_server, 'panel_request', return_value=(200, mock_body)) as mock_p:
            body = rutina_server.leer_reloj_estado()
            mock_p.assert_called_once_with('GET', '/api/reloj/estado')
            data = json.loads(body)
            self.assertTrue(data['ok'])
            self.assertEqual(data['state']['estado'], 'running')

    def test_enviar_reloj_comando_llama_al_panel(self):
        mock_body = json.dumps({
            "ok": True,
            "state": {
                "id": "piso_ironcross",
                "modo": "temporizador",
                "estado": "paused",
                "version": 5,
            },
            "serverTime": 1730000005,
        })
        payload = {"accion": "pausar"}
        with patch.object(rutina_server, 'panel_request', return_value=(200, mock_body)) as mock_p:
            body = rutina_server.enviar_reloj_comando(payload)
            mock_p.assert_called_once_with('POST', '/api/reloj/estado', json_body=payload)
            data = json.loads(body)
            self.assertTrue(data['ok'])
            self.assertEqual(data['state']['estado'], 'paused')

    def test_panel_error_se_propaga_correctamente(self):
        with patch.object(rutina_server, 'panel_request', side_effect=rutina_server.PanelError(502, 'sin conexión')):
            with self.assertRaises(rutina_server.PanelError) as ctx:
                rutina_server.leer_reloj_estado()
            self.assertEqual(ctx.exception.status, 502)


if __name__ == '__main__':
    unittest.main()
