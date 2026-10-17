#!/usr/bin/env python3
"""Prueba el endpoint /api/antigravity-status de RelojIron."""
import json
import unittest
import rutina_server


class TestAntigravityStatus(unittest.TestCase):
    def test_obtener_antigravity_status_estructura(self):
        info = rutina_server.obtener_antigravity_status()
        self.assertIsInstance(info, dict)
        self.assertTrue(info.get('ok'))
        self.assertIn('daemon_state', info)
        self.assertIn('instance_name', info)
        self.assertIn('remote_url', info)
        self.assertEqual(info['remote_url'], 'https://antigravity.google.com')
        self.assertTrue(len(info['instance_name']) > 0)


if __name__ == '__main__':
    unittest.main()
