# Estado actual — RelojIron

**Actualizado:** 2026-09-09

## Función

Sistema liviano para el iPad del gimnasio: reloj, cronómetros, rutinas y vista de oficina.

## Evidencia actual

- La copia activa está limpia y coincide con GitHub en `b8b4ce5`.
- El último cambio confirmado incorporó una pantalla propia de clave para la pestaña OFICINA con sesión recordada.
- El cliente conserva compatibilidad con iPad 1 y depende de la API del panel, no de acceso directo a Postgres.

## Dependencias

- `ironcross-dashboard` expone la API usada por RelojIron.
- Oracle sirve este proyecto y requiere sus variables de entorno fuera de Git.

## Próximo control

Verificar desde el iPad que las vistas de rutina y oficina respondan correctamente después de cambios en el dashboard.
