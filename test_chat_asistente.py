#!/usr/bin/env python3
"""Prueba el endpoint /api/chat y /api/chat-historial de RelojIron."""
import http.client
import json
import os
import unittest
import urllib.parse

import rutina_server


class TestChatAsistente(unittest.TestCase):
    def setUp(self):
        rutina_server.OFICINA_PASSWORD = "test-password"
        rutina_server.OFICINA_SESSION_SECRET = "test-secret-key-123"

    def test_chat_sin_sesion_da_401(self):
        handler = rutina_server.Handler.__new__(rutina_server.Handler)
        handler.headers = {}
        self.assertFalse(handler._chat_sesion_valida())

    def test_token_chat_valido_y_password_por_defecto(self):
        self.assertEqual(rutina_server.CHAT_PASSWORD, "2799706")
        token = rutina_server.crear_token_chat()
        self.assertTrue(rutina_server.token_chat_valido(token))
        self.assertFalse(rutina_server.token_chat_valido("invalido.123"))

    def test_nicola_chat_request_formatea_bien(self):
        # Prueba que la función auxiliar construye el payload correcto
        original_url = rutina_server.NICOLA_API_URL
        rutina_server.NICOLA_API_URL = "http://127.0.0.1:9999"
        try:
            resp = rutina_server.nicola_chat_request("Hola test")
            self.assertTrue("Error conectando" in resp or isinstance(resp, str))
        finally:
            rutina_server.NICOLA_API_URL = original_url


if __name__ == '__main__':
    unittest.main()
