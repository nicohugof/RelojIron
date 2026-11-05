#!/usr/bin/env python3
"""
Generación automática diaria de rutinas Ironcross con IronBot.

Se ejecuta mediante cron para asegurar que cada jornada de clase (AM/PM) tenga
su rutina lista antes de iniciar los entrenamientos, sin depender de carga manual.

Reglas de jornada:
- Martes y Jueves: AM (07:00 hrs) y PM (19:30 hrs).
- Lunes, Miércoles y Viernes: PM (19:30 hrs).
- Idempotencia: Si ya existe una rutina guardada para la fecha y jornada, se preserva.
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

# Asegurar import de rutina_server desde la raíz de RelojIron
ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

import rutina_server

TZ_CHILE = ZoneInfo("America/Santiago")


def jornadas_por_defecto(dt: datetime) -> list[str]:
    """Retorna las jornadas que corresponden según el día de la semana en Chile."""
    weekday = dt.weekday()  # 0=Lunes, 1=Martes, ..., 6=Domingo
    if weekday in (1, 3):  # Martes o Jueves
        return ["AM", "PM"]
    elif weekday in (0, 2, 4):  # Lunes, Miércoles o Viernes
        return ["PM"]
    return []


def asegurar_rutina_jornada(
    fecha: str,
    jornada: str,
    forzar: bool = False,
) -> bool:
    """
    Verifica si existe rutina para la fecha y jornada; si no existe, la genera y guarda.
    Retorna True si generó/guardó o ya existía, False si hubo error.
    """
    try:
        if not forzar:
            datos = rutina_server.leer_rutina_datos(fecha, jornada)
            contenido_existente = datos.get("contenido", "").strip()
            # Si ya existe y no es la plantilla en blanco
            if datos.get("encontrada") and contenido_existente and contenido_existente != rutina_server.PLANTILLA_RUTINA.strip():
                print(f"[PRESERVADA] Ya existe rutina guardada para {fecha} {jornada} ({len(contenido_existente)} bytes).")
                return True

        print(f"[GENERANDO] IronBot analizando sesiones anteriores para {fecha} {jornada}...")
        resultado = rutina_server.preparar_borrador_ironbot(fecha, jornada)
        if not resultado.get("ok") or not resultado.get("rutina"):
            print(f"[ERROR] IronBot no devolvió una rutina válida: {resultado}", file=sys.stderr)
            return False

        rutina_texto = resultado["rutina"].strip()
        print(f"[GUARDANDO] Persistiendo rutina en la base de datos para {fecha} {jornada}...")
        rutina_server.guardar_rutina(fecha, rutina_texto, jornada)
        print(f"[ÉXITO] Rutina creada y guardada para {fecha} {jornada}.")
        return True

    except Exception as exc:
        print(f"[EXCEPCIÓN] Error procesando rutina para {fecha} {jornada}: {exc}", file=sys.stderr)
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--fecha",
        type=str,
        default="",
        help="Fecha YYYY-MM-DD (por defecto hoy en Chile)",
    )
    parser.add_argument(
        "--jornada",
        type=str,
        choices=["AM", "PM", "todas"],
        default="",
        help="Jornada a generar (por defecto según día de semana)",
    )
    parser.add_argument(
        "--forzar",
        action="store_true",
        help="Sobrescribir incluso si ya existe una rutina guardada",
    )
    args = parser.parse_args()

    ahora = datetime.now(TZ_CHILE)
    fecha = args.fecha.strip() if args.fecha.strip() else ahora.strftime("%Y-%m-%d")

    if args.jornada == "todas":
        jornadas = ["AM", "PM"]
    elif args.jornada in ("AM", "PM"):
        jornadas = [args.jornada]
    else:
        # Calcular fecha objeto para evaluar día de la semana
        try:
            dt_objetivo = datetime.strptime(fecha, "%Y-%m-%d").replace(tzinfo=TZ_CHILE)
        except ValueError:
            print(f"[ERROR] Formato de fecha inválido: {fecha}. Use YYYY-MM-DD", file=sys.stderr)
            return 2
        jornadas = jornadas_por_defecto(dt_objetivo)
        if not jornadas:
            print(f"[INFO] No hay jornadas regulares programadas para {fecha} (fin de semana). Use --jornada para forzar.")
            return 0

    print(f"=== GENERADOR DIARIO DE RUTINAS IRONCROSS ===")
    print(f"Fecha: {fecha} | Jornadas a revisar: {', '.join(jornadas)} | Forzar: {args.forzar}")

    exito_total = True
    for j in jornadas:
        ok = asegurar_rutina_jornada(fecha, j, forzar=args.forzar)
        if not ok:
            exito_total = False

    return 0 if exito_total else 1


if __name__ == "__main__":
    raise SystemExit(main())
