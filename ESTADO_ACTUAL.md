# Estado actual — RelojIron

**Actualizado:** 2026-10-29

## iPad y publicación

- La vista pública consultada por GET respondió HTTP 200 y coincidió con `origin/main` commit `3d1b799` (SHA-256 del HTML: `2bcda4e2d01a171d3d8bc815163f9dfc8a162f7001c24b500d67fd2d13e285b0`).
- `codex/relojiron-am-pm-20261029` parte de `origin/main` `3d1b799` y está un commit local por delante, cero detrás. El commit AM/PM está preparado localmente, sin publicar. Cambios previos ajenos a AM/PM permanecen sin confirmar.
- El servidor documenta un cron automático cada pocos minutos, con intervalo no especificado en Git. No se ejecutó ni se consultó el crontab remoto. Los headers desactivan caché HTTP. No hay PWA/service worker detectado.
- No hacer push/merge antes de una autorización de publicación; el cron puede desplegar automáticamente `main`.

## Rutinas AM/PM

- La interfaz local ofrece AM, PM e HISTORIAL. La jornada forma parte del GET/POST hacia la API de Ironcross.
- Las rutinas anteriores sin jornada siguen como registros legacy sin reasignación. HISTORIAL es de solo lectura; copiarlas a AM o PM requiere una acción explícita.
- El proxy falla cerrado ante una API de Ironcross antigua que no confirme la jornada.
- Ironcross requiere primero su migración local `005_rutinas_jornada.sql` (posterior a `001_historial_rutinas.sql`) y la publicación de la API compatible. Ninguna migración real se ejecutó.

## Pruebas y continuidad

La actualización completa de pruebas y checkpoints está en [CONTINUIDAD_RUTINAS_AM_PM_20261029.md](CONTINUIDAD_RUTINAS_AM_PM_20261029.md).
