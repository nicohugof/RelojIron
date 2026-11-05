"""Regresión local de generación IronBot: lecturas históricas y borrador sin persistencia."""
import json
import unittest
from unittest.mock import patch

import rutina_server


class IronBotDraftTests(unittest.TestCase):
    def _panel(self, method, path, params=None, json_body=None, form_body=None):
        if path == '/api/rutina/dias':
            return 200, json.dumps({'dias': [
                '2026-10-29', '2026-10-28', '2026-10-27', '2026-10-26',
                '2026-10-25', '2026-10-24', '2026-10-23', '2026-10-30',
            ]})
        if path == '/api/rutina':
            fecha = params['fecha']
            jornada = params['jornada']
            contenido = 'Rutina {0} {1}'.format(fecha, jornada)
            return 200, json.dumps({'fecha': fecha, 'jornada': jornada, 'encontrada': True, 'contenido': contenido})
        raise AssertionError('Ruta o método inesperado: {0} {1}'.format(method, path))

    def test_consulta_solo_anteriores_y_solo_lectura_y_genera_borrador(self):
        requests = []

        def panel(*args, **kwargs):
            requests.append((args, kwargs))
            return self._panel(*args, **kwargs)

        with patch.object(rutina_server, 'panel_request', side_effect=panel), \
             patch.object(rutina_server, 'nicola_chat_request', return_value='CALENTAMIENTO\nCardio dinámico') as chat:
            result = rutina_server.preparar_borrador_ironbot('2026-10-30', 'AM')

        self.assertEqual(result['rutinas_revisadas'], 5)
        self.assertIn('Rutina 2026-10-29 AM', chat.call_args.args[0])
        self.assertIn('no confirma que la clase se haya realizado', chat.call_args.args[0])
        self.assertIn('cardio dinámico', chat.call_args.args[0].lower())
        self.assertTrue(all(args[0] == 'GET' for args, _ in requests))
        self.assertFalse(any(args[0] == 'POST' for args, _ in requests))

    def test_sin_historial_no_inventa_antecedentes(self):
        def panel(method, path, params=None, json_body=None, form_body=None):
            if path == '/api/rutina/dias':
                return 200, json.dumps({'dias': ['2026-10-30', '2026-10-31']})
            raise AssertionError('No debe leer rutinas futuras')

        with patch.object(rutina_server, 'panel_request', side_effect=panel), \
             patch.object(rutina_server, 'nicola_chat_request', return_value='Propuesta nueva') as chat:
            result = rutina_server.preparar_borrador_ironbot('2026-10-30', 'PM')

        self.assertEqual(result['rutinas_revisadas'], 0)
        self.assertIn('Sin historial guardado verificable', result['historial'])
        self.assertIn('No inventes antecedentes', chat.call_args.args[0])

    def test_api_historial_no_disponible_detiene_generacion(self):
        with patch.object(rutina_server, 'panel_request', side_effect=rutina_server.PanelError(502, 'sin conexión')), \
             patch.object(rutina_server, 'nicola_chat_request') as chat:
            with self.assertRaises(rutina_server.PanelError):
                rutina_server.preparar_borrador_ironbot('2026-10-30', 'AM')
        chat.assert_not_called()

    def test_historial_que_no_confirma_jornada_falla_cerrado(self):
        def panel(method, path, params=None, json_body=None, form_body=None):
            if path == '/api/rutina/dias':
                return 200, json.dumps({'dias': ['2026-10-29']})
            return 200, json.dumps({'fecha': params['fecha'], 'contenido': 'rutina sin jornada'})

        with patch.object(rutina_server, 'panel_request', side_effect=panel), \
             patch.object(rutina_server, 'nicola_chat_request') as chat:
            with self.assertRaises(rutina_server.PanelError):
                rutina_server.preparar_borrador_ironbot('2026-10-30', 'AM')
        chat.assert_not_called()

    def test_interfaz_confirma_y_indica_que_es_borrador(self):
        from pathlib import Path
        html = Path(rutina_server.DIRECTORY, 'index.html').read_text(encoding='utf-8')
        self.assertIn('window.confirm(\'IronBot consultará hasta cinco rutinas guardadas anteriores', html)
        self.assertIn('Ya existe una rutina guardada para', html)
        self.assertIn('rutinaGuardadaExiste && rutinaBorradorExterno && !window.confirm', html)
        self.assertIn("xhr.open('POST', '/api/generar-rutina'", html)
        self.assertIn('CONFIRMÓ WHATSAPP', html)
        self.assertIn('tabHoy" class="tab">ASISTENCIA', html)
        self.assertIn('hoyPintarFilaR(fila.parts, encuesta)', html)
        self.assertIn('Toca PRESENTE para marcar asistencia', html)
        self.assertIn("'PRESENTE', 'si', resp === 'si'", html)
        self.assertIn('tabStopwatch" class="tab">TEMPORIZADOR', html)
        self.assertIn('tabPersonalizados" class="tab">PERSONALIZADO', html)
        self.assertIn('rutinaDiaConClase', html)
        self.assertIn('rutinaCalendarGrid', html)
        self.assertIn('rutinaWeekPrev', html)
        self.assertIn('presetCloseBtn', html)
        self.assertIn('ironcrossLogoSweep', html)
        self.assertIn('prefers-reduced-motion: reduce', html)
        self.assertIn('.swRow .swBtn:not(.swRemove)', html)
        self.assertIn('tabPersonalizados', html)
        self.assertIn('personalText', html)
        self.assertIn('font-size: 14px;\n    letter-spacing: 0.5px;\n    white-space: nowrap;', html)


if __name__ == '__main__':
    unittest.main()
