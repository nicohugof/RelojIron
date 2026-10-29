# Continuidad — publicación de rutinas AM/PM

Actualizado: 2026-10-29

## Estado

Implementación local lista para revisión/publicación coordinada; **no publicada**. RelojIron y la API local de Ironcross guardan por fecha+jornada. Las rutinas antiguas mantienen `jornada NULL`, no se reclasifican y se consultan como historial de solo lectura. Copiarlas a AM/PM es explícito.

## Diagnóstico de iPad y desfase

- El GET público del 2026-10-29 respondió HTTP 200. Su HTML SHA-256 fue `2bcda4e2d01a171d3d8bc815163f9dfc8a162f7001c24b500d67fd2d13e285b0`, igual al `origin/main` entonces en `3d1b799`.
- `codex/relojiron-am-pm-20261029` ahora parte del commit real `origin/main` `3d1b799` y está 1 commit por delante, 0 detrás. Commit AM/PM local: el commit AM/PM de esta rama (`feat: add independent AM PM routines`). No se publicó.
- Cambios previos que no son AM/PM se conservaron sin confirmar: `AGENTS.md`, el bloque de ingresos en `README.md` e `index.html`, y `test_oficina_income_sentinel.py`. No quedaron dentro del commit AM/PM.
- El servidor anuncia `Cache-Control: no-cache, no-store, must-revalidate, max-age=0`, `Pragma: no-cache` y `Expires: 0`; no se encontró manifest ni service worker PWA.
- `README.md` documenta un cron que ejecuta `deploy.sh` cada pocos minutos. El intervalo efectivo y crontab remoto no fueron consultados. `deploy.sh` hace fetch y fast-forward de `origin/main`, reinicia el servidor y tiene health check/rollback. Para impedir un despliegue accidental, mantener este cambio en la rama local: **no hacer push/merge a `main`**. Pausar el cron sería una operación de producción y requiere autorización aparte.
- La interfaz conserva JavaScript ES5 y XHR para el iPad 1/iOS 5.1.1; no hubo verificación física.

## Commits locales

- RelojIron: el commit AM/PM de esta rama — interfaz, proxy, compatibilidad, docs y regresiones AM/PM. Commit separado del trabajo previo.
- Ironcross: commit local AM/PM — migración y rollback, storage, endpoint AM/PM y pruebas. La rama `codex/ironbot-history-memory-20261027` conserva muchos cambios previos sin confirmar; el commit se preparó con selección parcial y no incluyó esos cambios.
- No se hizo push, merge, despliegue, llamada a `deploy.sh` ni migración real.

## Compatibilidad SQL y contratos

- `db/schema.sql` crea `public.rutinas(fecha date NOT NULL PRIMARY KEY, contenido text NOT NULL)`. La migración 001 agrega `id`, `creado_en` y cambia la PK a `id`; la 005 exige ese estado, agrega `jornada` nullable y su CHECK AM/PM. No asigna jornada a filas previas.
- Prueba aislada PGlite: tabla base equivalente a `schema.sql` + rutina histórica → migración 001 → migración 005. Pasó, comprobando columnas, PK `id` y preservación exacta de la rutina sin jornada. Esto valida compatibilidad del esquema modelado; no verifica el estado de PostgreSQL productivo ni que 001 esté aplicada allí. No hay cliente/servidor PostgreSQL real usado en esta ejecución.
- RelojIron manda `fecha` y `jornada`. El proxy requiere que GET y POST de Ironcross confirmen la misma jornada; ante API antigua falla cerrado. Clientes anteriores que omiten jornada siguen escribiendo legacy (`NULL`) y la lectura por fecha mantiene la semántica anterior.
- Ironcross down migration solo elimina la columna si no existen filas AM/PM. Después de guardar jornadas, rechaza rollback de esquema para proteger datos.

## Pruebas

- RelojIron: `python3 -m unittest discover -v` **31/31**, `py_compile`, `node --check` del script inline y `git diff --check` aprobados.
- Ironcross: `npm test` **113/113**, `npm run lint`, `npx tsc --noEmit`, `npm run build`, `git diff --check` aprobados. Hay una regresión nueva que reproduce base + 001 + 005.
- Total actual: **144 pruebas** (31 + 113). Pruebas locales, datos sintéticos/mock; no equivalen a prueba en iPad, PostgreSQL instalado o producción.

## Orden de despliegue propuesto

1. Confirmar por lectura autorizada que PostgreSQL está en el estado esperado por 001 y respaldar la base.
2. Aplicar 005 en staging aislado y validar lectura/escritura AM/PM y filas legacy.
3. Autorizar y desplegar la API Ironcross con soporte AM/PM.
4. Autorizar push/merge de RelojIron a `main`. Esto puede disparar el cron, que actualizaría Oracle; no ejecutar `deploy.sh` manualmente a la vez.
5. Verificar endpoint, hash servido, rutina AM, PM y legacy desde el iPad; luego comprobar edición independiente.

## Rollback

- **RelojIron:** el deploy script vuelve al commit anterior si falla su health check. Si se requiere rollback funcional, revertir el commit AM/PM de esta rama mediante un commit autorizado. La API y la columna nueva pueden permanecer; clientes antiguos omiten la jornada y escriben legacy.
- **API Ironcross:** revertir el código a la versión anterior con procedimiento autorizado. El cliente RelojIron falla cerrado frente a la API sin confirmación, por lo que publicar código fuera del orden indicado detendría los guardados AM/PM.
- **Migración 005:** usar el down únicamente antes de que exista cualquier fila AM/PM. Si ya hay jornadas guardadas, el down se niega deliberadamente; revertir aplicación conservando la columna para no perder/ocultar datos.
- Ningún rollback de producción fue ejecutado ni autorizado en esta fase.

## Bloqueos antes de publicar

1. Confirmar el estado real de PostgreSQL/001 y probar 005 en un PostgreSQL aislado o staging; la prueba disponible fue PGlite.
2. Autorización específica para aplicar la migración en producción y desplegar Ironcross.
3. Autorización específica para publicar RelojIron en `main` (puede activar cron/Oracle).
4. Verificación presencial en el iPad y evidencia de AM/PM/historial después del despliegue.

Checkpoint final recuperable guardado en `/Users/nigoku/Nicola OS/checkpoints/relojiron-ampm-publish-20261029-final-r4/`; el hash está en el manifiesto del checkpoint. Checkpoint previo de preparación en `/Users/nigoku/Nicola OS/checkpoints/relojiron-ampm-publish-20261029/`.
