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
