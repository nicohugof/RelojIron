# Contexto: RelojIron

Carpeta oficial: esta carpeta.

Antes de trabajar, consulta `../INDICE_PROYECTOS.md` y `../INVENTARIO_COMPARTIDO.md` si el trabajo requiere datos compartidos.

Estado: integración de entrenamientos personales local y validada en staging PostgreSQL TCP.
# Continuidad — entrenamientos personalizados (2026-10-30)

La pestaña Personal opera sobre el almacén/API existente de Ironcross mediante el proxy autenticado `/api/personalizados`; RelojIron no crea un historial local paralelo. El padrón canónico incluye alumnos con y sin vínculo. Al seleccionar uno sin vínculo, Ironcross crea un historial individual nuevo y vínculo explícito 1:1 en una sola transacción. No se asocian historiales antiguos automáticamente.

Pruebas en `test_personalizados_proxy.py`: autenticación de Oficina, acciones permitidas, preparación de alumno y redacción de errores upstream. RelojIron: 34 pruebas aprobadas. En staging PostgreSQL TCP se creó vínculo al seleccionar fixture sintético, RelojIron creó sesión, Dashboard la leyó/editó y RelojIron vio la edición; reintentos y conservación de históricos antiguos sin vínculo pasaron. Dashboard: 107 pruebas, lint, TypeScript y build aprobados. No hubo conexiones/escrituras productivas, push, merge ni despliegue.

Worktree: `codex/personalized-training-e2e-20261030`, commit de integración `eafe1de57acdebdf96ed784937c57208e6c83c30`. Checkpoint y evidencia E2E: `/Users/nigoku/Nicola OS/checkpoints/training-integration-e2e-20261030`. La conexión a producción y publicación requieren autorización específica.


## Selección y vínculo de alumno — 2026-10-31

Al abrir Personal se consulta el padrón canónico. El profesor selecciona un alumno; el proxy autentica la petición y Dashboard resuelve la identidad canónica. Si ya existe vínculo, reutiliza el historial. Si no existe, crea uno vacío y lo enlaza 1:1 de forma transaccional. Las sesiones antiguas sin vínculo se conservan sin asignar. Un retry de selección devuelve el mismo perfil y no crea duplicados.

Validación HTTP local sobre PostgreSQL 16 TCP aislado: selección de alumno sin vínculo, creación de sesión desde RelojIron, lectura y edición desde Dashboard, lectura inversa desde RelojIron, vínculo único, sesión única y conteo de perfiles antiguos sin vínculo sin cambios. Evidencia redactada: `/Users/nigoku/Nicola OS/checkpoints/training-integration-e2e-20261030/postgres-staging-e2e-report.json`. No se publicó.

## Personalizado 10X — sesión de texto libre (2026-10-31)

- La pestaña Personalizado conserva únicamente selección/búsqueda de alumno, texto libre, Guardar sesión y Ver última sesión. La identidad se prepara mediante el proxy autenticado; el padrón siempre viene de la API canónica. El botón de acceso abre el modal actual de Oficina y, después de autenticarse, vuelve a cargar el padrón.
- Cada sesión recibe un ID estable para reintentos, fecha Chile y jornada AM/PM disponible. Guardar de nuevo edita la sesión actual; Nueva sesión asigna otro ID. El historial anterior no se modifica. Textarea soporta el evento `input` de teclados táctiles.
- Dashboard guarda `contenidoLibre` y jornada dentro de `rutina_snapshot_json`, conservando las tablas, snapshots y series estructuradas existentes. No se creó migración, tabla paralela ni llamada a IronBot. Dashboard permite consultar y editar la misma sesión.
- E2E HTTP con PostgreSQL 16 aislado y dos alumnos sintéticos: padrón → vínculo explícito → crear desde RelojIron → retry idempotente → edición desde Dashboard → lectura inversa → rechazo de escritura cruzada → reinicio de ambos servicios → persistencia confirmada. Solo quedó una sesión de texto para el alumno principal y cero para el segundo. UI verificada a 768×1024: sin overflow horizontal; botones 58 px y área de texto 250 px. Guardado y recuperación de última sesión validados desde el navegador.
- Pruebas: RelojIron 36/36, Python compile y sintaxis JavaScript; Dashboard 108/108, lint, TypeScript y build. Evidencia y bundles locales: `/Users/nigoku/Nicola OS/checkpoints/personalizado-10x-20261031/`.
- Estado: implementación local lista para revisión/publicación; no hubo acceso productivo, push ni despliegue.
