# Contexto: RelojIron

Carpeta oficial: esta carpeta.

Antes de trabajar, consulta `../INDICE_PROYECTOS.md` y `../INVENTARIO_COMPARTIDO.md` si el trabajo requiere datos compartidos.

Estado y próximo paso: pendiente de documentar en la próxima revisión del proyecto.
# Continuidad — entrenamientos personalizados (2026-10-30)

Se agregó una pestaña Personal para operar entrenamientos individuales usando el proxy autenticado `/api/personalizados` y el almacén/API existente de Ironcross. RelojIron no crea un historial local paralelo. La identidad proviene de la lista de alumnos con vínculo canónico explícito; una sesión y sus series se leen y escriben bajo el alumno seleccionado.

Pruebas añadidas en `test_personalizados_proxy.py`: autenticación de Oficina, acciones permitidas, validación del identificador y redacción de errores upstream. Validación actual: 33 pruebas Python aprobadas. La integración remota real no se ejecutó; el proxy se verifica con mocks. No hubo push, migración ni despliegue.

Worktree: `codex/personalized-training-e2e-20261030`. Sintaxis Python y las 33 pruebas locales pasaron. Checkpoint y commit local quedan por registrar. La conexión entre servicios productivos y publicación requieren autorización específica.
