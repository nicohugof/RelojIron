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

## Addendum — simplificación de jornadas y arquitectura (2026-10-30)

- La afirmación anterior de que AM/PM aún no estaba publicado quedó superada por el acta de publicación del 2026-10-30: Ironcross `81e2bc1` y RelojIron `ba7818f` están publicados. La migración 005 está aplicada; el cron de RelojIron se verificó activo cada cinco minutos y el servidor respondió HTTP 200. La validación física en iPad sigue pendiente.
- Architecture Preflight reconciliado con `ARCHITECTURE_REGISTRY.json`: RelojIron clasificado `VIGENTE`, checkout oficial `/Users/nigoku/Proyectos/RelojIron`, remoto `https://github.com/nicohugof/RelojIron.git`, HEAD `ba7818fd84ec7cbf98be9a82f4e918047ab9b419`, igual a `origin/main` y al commit de producción. La rama de trabajo local es `codex/relojiron-am-pm-20261029`; no se hizo push ni despliegue.
- La interfaz ya no ofrece una tercera pestaña/botón «Historial». Al seleccionar una fecha desde el calendario, AM/PM se consultan independientemente. Si no existe la jornada elegida pero hay un registro antiguo sin jornada, se muestra en solo lectura desde esa fecha; «EDITAR COPIA AM/PM» crea un borrador nuevo sin alterar el original. Las rutinas AM/PM anteriores se recuperan por fecha y jornada.
- Se muestran los horarios habituales: AM martes/jueves 07:00 y PM lunes a viernes 19:30. La selección inicial usa AM en martes/jueves antes del mediodía y PM en días hábiles; otros días/horas conservan una opción explícita de excepción desde calendario. No se añadieron columnas ni se cambiaron registros.
- Pruebas: `python3 -m unittest discover -v` **31/31 aprobadas**, incluida la regresión de UI y las pruebas de proxy AM/PM; `git diff --check` aprobado. Falta validar navegador/iPad físico.
- Checkpoints recuperables: previo `/Users/nigoku/Nicola OS/checkpoints/relojiron-simplification-20261030-pre/`; posterior `/Users/nigoku/Nicola OS/checkpoints/relojiron-simplification-20261030-post-final/`. Ambos incluyen manifiestos SHA-256 verificados.
- Próximo paso: inspección visual local si se requiere; después, que Nico pruebe en iPad la misma fecha con AM y PM, abra una rutina histórica, confirme aislamiento al editar AM y valide horarios. No autorizar publicación de estos cambios locales hasta esa revisión; el cron despliega desde `main` cada cinco minutos.

## RelojIron 2.0 — continuación local (2026-10-30)

### Arquitectura y límites

- Preflight: `RelojIron` sigue `VIGENTE`; checkout oficial `/Users/nigoku/Proyectos/RelojIron`, remoto `https://github.com/nicohugof/RelojIron.git`, rama `codex/relojiron-am-pm-20261029`, HEAD y `origin/main` `0a4fee3822250f41d22d785b12c23dee25fe16e3`. Ese commit está desplegado según la evidencia previa del registro. Esta tarea no hizo consultas ni cambios en producción.
- No se editaron Ironcross, IronBot ni el servicio de encuestas. La API vigente de asistencia solo recibe jornada, no fecha; por eso la pestaña declara HOY y no ofrece calendario histórico. El endpoint tampoco expone salud de la conexión WhatsApp: la interfaz dice cuando la API no devuelve respuestas, sin afirmar si el servicio está conectado.
- Las filas `U` sin ID canónico se cuentan, pero no se muestran ni asocian por nombre. La vista inicial solo incluye `si` con origen de encuesta WhatsApp; no presenta esas respuestas como asistencia efectiva. El padrón canónico se filtra solo después de buscar. Los botones PRESENTE/AUSENTE/LIMPIAR siguen siendo una acción manual.
- El registro de arquitectura previo reporta que el servicio de encuestas de WhatsApp estaba desconectado (`connected=false`) al verificarse. No se volvió a consultar ni se simuló una conexión en este trabajo.

### Cambios locales

- Selector semanal de una sola semana, con AM solo martes/jueves y PM lunes-viernes; AM/PM aparecen sin subtítulos. Se conserva navegación a rutinas históricas y registros sin jornada en solo lectura. El calendario mensual habilita días habituales y fechas con rutinas históricas del endpoint actual.
- IronBot solicita confirmación antes de generar; usa hasta cinco rutinas guardadas previas obtenidas por GET y advierte que son planes, no sesiones realizadas. Se eliminó del flujo RelojIron la llamada a `/api/rutina/generar`, porque el código publicado previamente podía guardar sin AM/PM. El resultado se trata como borrador; GUARDAR pide confirmación si ya existe una rutina. El generador real de Nicola no fue invocado en pruebas.
- Temporizadores: controles táctiles mayores y cierre superior en cada tarjeta y en el selector. El reloj principal conserva su diseño y el logotipo tiene un barrido rojo CSS lento con fallback.
- No se alteró el modelo ni se borraron rutinas.

### Evidencias y pruebas

- Checkpoint previo: `/Users/nigoku/Nicola OS/checkpoints/relojiron-2-pre-20261030/`, hash del manifiesto verificado. Incluye parche y archivos locales que ya existían antes del trabajo; recuperar con el HEAD anotado `0a4fee3`.
- `python3 -m unittest discover -v`: **35/35 aprobadas** (incluye 4 regresiones IronBot, proxy de asistencia, AM/PM, auth y la prueba preexistente de ingresos). `python3 -m py_compile` aprobado; `node --check` del JavaScript inline aprobado; `git diff --check` aprobado.
- Revisión visual local aislada con datos ficticios: iPad 768×1024 y 1024×768. Se recorrieron calendario, padrón buscado, respuesta WhatsApp sintética y temporizador. Ningún endpoint de producción fue contactado desde la vista. No sustituye la comprobación en un iPad físico.
- IronBot no se conectó al servicio de generación; la prueba de su capa de servidor fue mockeada. No hay afirmación de calidad de respuesta de modelo ni de integración operativa.

### Riesgos y pendiente

- La API actual de asistencia no admite fecha y no informa estado de sincronización. Para asistencia de otra fecha o confirmar estado WhatsApp se requiere un contrato/API vigente en Ironcross, que deberá revisarse antes de tocar ese repo.
- Los orígenes de encuesta se aceptan solo si contienen `WHATSAPP`, `ENCUESTA` o `POLL`; otras etiquetas quedan fuera de confirmados hasta confirmar el contrato.
- Al generar, Nicola OS se invoca cuando el docente confirma; disponibilidad, salida y estilo real no se probaron sin llamar a un servicio externo.
- La validación del cron de Oracle e iPad físico sigue fuera del alcance. No hubo push, commit, merge, despliegue, migración ni modificación de servicio.
- Cambios ajenos preexistentes (`AGENTS.md`, `README.md`, el bloque de `index.html` para ingresos y `test_oficina_income_sentinel.py`) permanecen preservados y no deben entrar en commits de esta entrega.

### Próximo paso exacto

Revisar el diff de RelojIron 2.0 y sus pruebas; preparar commits locales solo con los archivos/hunks de esta entrega, dejando fuera los cambios previos señalados. No publicar. Resolver el endpoint de asistencia con fecha en una tarea separada con preflight de Ironcross antes de prometer historial/estado WhatsApp.

## Recuperación de mejoras pendientes — 2026-10-31

### Cambios recuperados e integrados localmente

- Arquitectura vigente registrada: RelojIron `main` publicado en `5b3395702384d4ff4bf269036c5b6a9a2651bd96`. El trabajo se aisló en `codex/relojiron-personalizado-10x-20261031`, inicialmente limpio sobre ese commit; no se consultó el runtime durante esta tarea.
- Recuperada selectivamente la interfaz del commit existente `2864174097303d6140cbbddc7c123bd7a91d2de0` y la generación segura de borradores del commit `68cd2baac821f608e94e8a3c4796e5dc3dab1b91`. No se restauró el HTML completo antiguo.
- Se mantienen semana y calendario AM/PM, días habituales (AM martes/jueves; PM lunes-viernes), excepciones mediante fechas con rutinas guardadas e historial sin jornada en solo lectura. El calendario no crea rutinas para fechas sin clase ni registro previo.
- Se recuperó el filtro de Asistencia: inicialmente solo respuestas afirmativas cuyo origen identifica encuesta/WhatsApp; AM y PM usan el contrato vigente `/api/hoy?horario=...`. La respuesta se etiqueta como confirmación, no asistencia efectiva. La búsqueda manual conserva PRESENTE/AUSENTE/LIMPIAR como acciones explícitas. Los no vinculados no se asocian por nombre.
- IronBot consulta con GET hasta cinco rutinas anteriores de la API, no usa la ruta de generación que podía guardar directamente, informa si falta historial y devuelve un borrador. La pantalla solicita confirmación antes de generar y antes de reemplazar una rutina existente.
- Se recuperó el logo IRONCROSS de mayor tamaño con barrido rojo lento y reloj superior de 20 px. Se agregó respeto a `prefers-reduced-motion`.
- Cronómetro y temporizador conservan su estado al navegar. Pausa/reinicio tienen objetivos táctiles de 56 px, cierre X de 48×44 px en cada tarjeta y cierre superior de 48×44 px en el selector. Se ajustó la tipografía de los botones de Asistencia para evitar solapamiento en iPad.
- Personalizado 10X permanece en la misma pestaña, con selección de alumno, texto libre, Guardar sesión y Ver última sesión. No se modificaron su API ni su persistencia.

### Verificación

- `python3 -m unittest discover -v`: **41/41 aprobadas**. Incluye regresiones de AM/PM, historial, Asistencia, confirmación de IronBot, consulta solo GET y Personalizado.
- `python3 -m py_compile rutina_server.py test_ironbot_draft.py test_rutina_ampm.py`, `node --check` del JavaScript inline y `git diff --check`: aprobados.
- Navegador local aislado con API sintética y viewport iPad 768×1024: comprobados días AM/PM y excepción guardada, cierre del temporizador, pausa/reanudación/reinicio, conservación al cambiar de pestaña, botones táctiles, marca reducida de movimiento, respuesta afirmativa sintética, estado vacío PM y búsqueda manual. Sin errores JS, overflow horizontal ni solicitudes POST.
- Las imágenes y el reporte de este recorrido se guardan en `checkpoints/relojiron-recovery-20261031/`.
- No se conectó a producción, PostgreSQL, WhatsApp ni al proveedor de IronBot. La respuesta real del modelo no se evaluó. La persistencia de Personalizado ya estaba respaldada por la validación PostgreSQL aislada anterior y este cambio no toca esa ruta.

### Riesgos y límites pendientes

- La API de Asistencia actual consulta el día de hoy y jornada; no ofrece selección histórica de fecha ni una señal directa de salud de WhatsApp. No se amplió el contrato ni se modificó Ironcross.
- El recorrido de Asistencia verificó el formato de origen del contrato local de Ironcross y mocks, no el runtime productivo ni la conexión efectiva de WhatsApp. El registro de arquitectura conserva evidencia anterior de servicio desconectado.
- La generación de IronBot quedó cubierta con mocks; no se invocó proveedor externo y no se afirma calidad de generación real.
- La validación visual fue simulada en Chrome con contenido sintético; falta confirmar el comportamiento en el iPad físico.
- Base de producción documentada: Personalizado 10X `5b33957`. Esta rama contiene commits locales únicamente; no hubo push, merge, despliegue, migraciones, escrituras ni cambios en Ironcross/IronBot.

### Continuidad

- Checkpoint previo recuperable: `checkpoints/relojiron-recovery-20261031-pre/relojiron.bundle`, verificado con `git bundle verify` y SHA-256.
- Checkpoint final y hashes: `checkpoints/relojiron-recovery-20261031/`.
- Próximo paso: revisión manual en iPad físico. La publicación requiere autorización posterior para push/merge; no forma parte de esta entrega.
