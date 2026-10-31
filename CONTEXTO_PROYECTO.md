# Contexto: RelojIron

Carpeta oficial: esta carpeta.

Antes de trabajar, consulta `../INDICE_PROYECTOS.md` y `../INVENTARIO_COMPARTIDO.md` si el trabajo requiere datos compartidos.

Estado y próximo paso: pendiente de documentar en la próxima revisión del proyecto.
# Continuidad — entrenamientos personalizados (2026-10-30)

Se agregó una pestaña Personal para operar entrenamientos individuales usando el proxy autenticado `/api/personalizados` y el almacén/API existente de Ironcross. RelojIron no crea un historial local paralelo. La identidad proviene de la lista de alumnos con vínculo canónico explícito; una sesión y sus series se leen y escriben bajo el alumno seleccionado.

Pruebas añadidas en `test_personalizados_proxy.py`: autenticación de Oficina, acciones permitidas, validación del identificador y redacción de errores upstream. Validación: 33 pruebas Python aprobadas y recorrido HTTP local E2E aprobado. La sesión creada desde RelojIron fue leída/editada en Dashboard y el cambio persistió al reiniciar ambos servicios; aislamiento, idempotencia y recuperación ante caída temporal también pasaron. Se usó SQLite temporal y un padrón canónico sintético; no hubo PostgreSQL local ni conexión productiva. No hubo push, migración ni despliegue.

Worktree: `codex/personalized-training-e2e-20261030`, commit de integración `eafe1de57acdebdf96ed784937c57208e6c83c30`. Checkpoint y evidencia E2E: `/Users/nigoku/Nicola OS/checkpoints/training-integration-e2e-20261030`. La conexión a producción y publicación requieren autorización específica.
