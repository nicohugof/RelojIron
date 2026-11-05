import unittest
from datetime import datetime
from unittest.mock import patch, MagicMock
from zoneinfo import ZoneInfo
import sys
from pathlib import Path

# Agregar scripts al path
SCRIPTS_DIR = Path(__file__).resolve().parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import cron_generar_rutinas

TZ = ZoneInfo("America/Santiago")


class TestCronGenerarRutinas(unittest.TestCase):
    def test_01_jornadas_por_defecto(self):
        # Lunes 2026-11-02 (weekday 0) -> PM
        lunes = datetime(2026, 11, 2, 10, 0, tzinfo=TZ)
        self.assertEqual(cron_generar_rutinas.jornadas_por_defecto(lunes), ["PM"])

        # Martes 2026-11-03 (weekday 1) -> AM, PM
        martes = datetime(2026, 11, 3, 10, 0, tzinfo=TZ)
        self.assertEqual(cron_generar_rutinas.jornadas_por_defecto(martes), ["AM", "PM"])

        # Miércoles 2026-11-04 (weekday 2) -> PM
        miercoles = datetime(2026, 11, 4, 10, 0, tzinfo=TZ)
        self.assertEqual(cron_generar_rutinas.jornadas_por_defecto(miercoles), ["PM"])

        # Jueves 2026-11-05 (weekday 3) -> AM, PM
        jueves = datetime(2026, 11, 5, 10, 0, tzinfo=TZ)
        self.assertEqual(cron_generar_rutinas.jornadas_por_defecto(jueves), ["AM", "PM"])

        # Viernes 2026-11-06 (weekday 4) -> PM
        viernes = datetime(2026, 11, 6, 10, 0, tzinfo=TZ)
        self.assertEqual(cron_generar_rutinas.jornadas_por_defecto(viernes), ["PM"])

        # Sábado 2026-11-07 (weekday 5) -> []
        sabado = datetime(2026, 11, 7, 10, 0, tzinfo=TZ)
        self.assertEqual(cron_generar_rutinas.jornadas_por_defecto(sabado), [])

    @patch("cron_generar_rutinas.rutina_server.leer_rutina_datos")
    @patch("cron_generar_rutinas.rutina_server.preparar_borrador_ironbot")
    @patch("cron_generar_rutinas.rutina_server.guardar_rutina")
    def test_02_preserva_rutina_si_ya_existe(self, mock_guardar, mock_ironbot, mock_leer):
        # Rutina ya guardada en la base de datos
        mock_leer.return_value = {
            "encontrada": True,
            "contenido": "PREPARACION\nMovilidad\nCALENTAMIENTO\nBurpees",
        }

        ok = cron_generar_rutinas.asegurar_rutina_jornada("2026-11-05", "PM", forzar=False)
        self.assertTrue(ok)
        mock_leer.assert_called_once_with("2026-11-05", "PM")
        # No debe llamar a IronBot ni guardar
        mock_ironbot.assert_not_called()
        mock_guardar.assert_not_called()

    @patch("cron_generar_rutinas.rutina_server.leer_rutina_datos")
    @patch("cron_generar_rutinas.rutina_server.preparar_borrador_ironbot")
    @patch("cron_generar_rutinas.rutina_server.guardar_rutina")
    def test_03_genera_y_guarda_si_no_existe(self, mock_guardar, mock_ironbot, mock_leer):
        # No encontrada (o plantilla en blanco)
        mock_leer.return_value = {
            "encontrada": False,
            "contenido": "",
        }
        mock_ironbot.return_value = {
            "ok": True,
            "rutina": "PREPARACION\nArticular\nCALENTAMIENTO\nSkipping",
        }
        mock_guardar.return_value = None

        ok = cron_generar_rutinas.asegurar_rutina_jornada("2026-11-05", "PM", forzar=False)
        self.assertTrue(ok)
        mock_leer.assert_called_once_with("2026-11-05", "PM")
        mock_ironbot.assert_called_once_with("2026-11-05", "PM")
        mock_guardar.assert_called_once_with("2026-11-05", "PREPARACION\nArticular\nCALENTAMIENTO\nSkipping", "PM")


if __name__ == "__main__":
    unittest.main()
