# RelojIron — calendario AM/PM

## Alcance de este release

- Los botones de jornada muestran solo AM y PM.
- Vista semanal limitada a jornadas habituales: AM martes/jueves; PM lunes a viernes.
- Navegación por semanas y calendario mensual para fechas históricas o excepcionales.
- Las rutinas antiguas sin jornada siguen siendo de solo lectura y recuperables desde el calendario.
- Se conserva el contrato existente de `/api/rutina/dias` y se agrega `GUARDADOS:` para distinguir fechas con registros, incluso si coinciden con hoy o mañana. Clientes anteriores ignoran esa línea adicional.
- No incluye cambios de IronBot, asistencia, cronómetros, logo, finanzas ni otros repositorios.

## Verificación local

- `python3 -m unittest discover -q`: 29 pruebas aprobadas.
- `python3 -m unittest test_rutina_ampm -v`: 10 pruebas aprobadas.
- `python3 -m py_compile rutina_server.py test_rutina_ampm.py`: aprobado.
- `node --check /tmp/relojiron_calendar_inline.js`: aprobado.
- `git diff --check`: aprobado.

No se realizaron cambios de producción. La publicación sigue pendiente de la integración aprobada a `main` y la actualización del cron. La verificación física en iPad requiere confirmación del usuario.
