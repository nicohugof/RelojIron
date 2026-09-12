# RelojIron

Sistema de clase del **profesor** en un **iPad**, en el piso de **Ironcross Calistenia** (Nicolas Farias / nicohugof). El iPad lo usa el profesor durante la clase: reloj, cronómetros, rutina, oficina (quién debe) y HOY (quién viene).

Esto **no** es el panel Next.js (`panel.ironcross.cl`). Nico no usa ese panel para dar la clase; quiere ver esa información en esta página HTML, en el iPad.

Corre en un **iPad 1** (iOS 5.1.1, Safari viejo).

## Cómo se sirve

En el gym la app vive en **HTTP plano** (sin TLS):

```
http://146.181.44.106:8090
```

El iPad 1 no hace TLS moderno, por eso no se sirve por HTTPS. El servidor en el Oracle es Python (`SimpleHTTP` + handlers). `SimpleHTTP` sirve `index.html` en `/`.

El iPad 1 no tiene `fetch` ni flexbox: el HTML usa ES5, `XMLHttpRequest` y `display:table` / `table-cell`. **No modernizar** el JS/CSS.

## Pestañas (`index.html`)

1. **RELOJ** — hora a pantalla completa.
2. **CRONOMETROS** — cronómetros y temporizadores con beep al terminar la cuenta regresiva.
3. **RUTINA** — rutinas por fecha (carga/guarda contra la API del mismo host).
4. **GYM** — oficina: quién debe. Contadores **vencidos / por vencer / activos / sin plan** y listado (`tabGym`, `gymView`, `GET /api/oficina`).
5. **HOY** — quién viene hoy (espejo de `panel.ironcross.cl/hoy`, sin iframe: el iPad 1 no hace TLS moderno). Contadores **van / no / sin** y listado; toques grandes Sí / No / Limpiar en filas `R|` (`tabHoy`, `hoyView`, `GET/POST /api/hoy`). Misma clave/sesión que oficina (muestra nombres). Es pestaña propia, no un sub-tab de GYM, para marcar asistencia en el piso sin pasar por oficina/planes.

## Rutas de API (mismo host `:8090`)

El HTML llama a:

| Método | Ruta | Qué hace |
|--------|------|----------|
| GET | `/api/oficina` | Texto plano de la oficina (contadores + filas de alumnos) |
| GET | `/api/hoy` | Texto plano de asistencia de hoy (contadores + filas). Misma cookie que oficina. |
| POST | `/api/hoy` | Marca asistencia: `alumno_id=12&accion=si` (`si` / `no` / `limpiar`). Respuesta `OK` o `ERROR|mensaje`. |
| GET | `/api/rutina?fecha=YYYY-MM-DD` | Texto de la rutina de ese día |
| GET | `/api/rutina/dias` | Texto plano: `HOY:…` `MANIANA:…` `DIAS:…` |
| POST | `/guardar` | Guarda rutina (`fecha` + `rutina`, form-urlencoded) |

Formato de `GET /api/oficina` (una línea por registro, campos con `|`):

- Contadores: `C|activos|N`, `C|vencidos|N`, `C|por_vencer|N`, `C|sin_plan|N`
- Filas: `R|V|nombre|monto|dd/mm` (vencido) o `R|P|nombre|monto|dd/mm` (por vencer)

Formato de `GET /api/hoy` (una línea por registro, campos con `|`):

- Contadores: `C|si|N`, `C|no|N`, `C|sin|N`
- Filas tappeables: `R|alumno_id|nombre|si-o-no-o-vacio|origen` (respuesta vacía = sin respuesta)
- Filas solo lectura: `U|nombre_raw|si-o-no|origen` (sin `alumno_id`, no se pueden marcar)

`/api/hoy` y `/api/oficina` piden la misma cookie de oficina (`POST /api/oficina-login`). RelojIron proxea ambas al panel con `Authorization: Bearer $IPAD_API_TOKEN`.

**Verificar contra el panel** (cuando `nicohugof/ironcross-dashboard` #17 esté mergeado, o contra esa rama):

```
# Directo al panel (desde una máquina con TLS moderno; no desde el iPad 1)
curl -sS -H "Authorization: Bearer $IPAD_API_TOKEN" "$PANEL_API_URL/api/hoy"

# POST de prueba
curl -sS -H "Authorization: Bearer $IPAD_API_TOKEN" \
  -d "alumno_id=12&accion=si" "$PANEL_API_URL/api/hoy"

# Vía RelojIron (:8090), con la clave de oficina
curl -sS -c /tmp/ri.jar -d "password=$OFICINA_PASSWORD" http://127.0.0.1:8090/api/oficina-login
curl -sS -b /tmp/ri.jar http://127.0.0.1:8090/api/hoy
curl -sS -b /tmp/ri.jar -d "alumno_id=12&accion=si" http://127.0.0.1:8090/api/hoy
```

También existe **GET `/rutina`** (y `/rutina.html`): un HTML aparte (~1.5 KB, título `Ironcross - Rutina`) para editar y guardar con un form clásico a `POST /guardar`. Esa página la genera el backend (la fecha va rellena al pedirla). `rutina.html` en este repo es una captura de esa respuesta, no un archivo estático en el Oracle.

## Backend Python

El proceso que corre en el Oracle (`:8090`) es `rutina_server.py` (versionado en este repo), Python 3.12.3, banner `SimpleHTTP/0.6`. En esa máquina el archivo vive en `/home/ubuntu/rutina_server.py`.

**Ya no habla con Postgres.** Hasta el PR que agrega la API del panel (`nicohugof/ironcross-dashboard`), este servidor hacía `docker exec -i n8n-postgres-1 psql ...` directo contra la base para leer/guardar rutinas y armar la pestaña GYM — un segundo camino de acceso a la misma DB, en paralelo al panel. Ahora es un proxy delgado: cada ruta llama a la API del panel y devuelve la misma respuesta de siempre (el HTML/JS del iPad no cambió).

Variables de entorno que necesita el proceso en el Oracle:

| Variable | Qué es |
|---|---|
| `PANEL_API_URL` | Base de la API del panel. Default `https://panel.ironcross.cl` |
| `IPAD_API_TOKEN` | Mismo token que `IPAD_API_TOKEN` en el panel (`ironcross-dashboard`). Sin él, todo responde 500/502. |

Si el panel no responde, `/api/oficina`, `/api/hoy`, `/api/rutina` y `/guardar` devuelven `502` (antes hubieran colgado la conexión); `/api/rutina/dias` degrada a mostrar solo HOY/MAÑANA en vez de romper la pestaña RUTINA. Si el panel ya responde `ERROR|mensaje` en `POST /api/hoy`, RelojIron lo reenvía tal cual.

## Deploy

El servidor en el Oracle es un `git clone` de este repo en `/home/ubuntu/RelojIron` (no una copia a mano). `rutina_server.py` sirve `index.html`/`rutina.html` desde su propia carpeta (`DIRECTORY` = donde vive el script), así que un `git pull` alcanza para actualizar todo.

Para desplegar un cambio ya mergeado a `main`, desde `/home/ubuntu/RelojIron` en el servidor:

```
./deploy.sh
```

Hace `git fetch` + fast-forward, valida que `rutina_server.py` compile, reinicia el proceso y comprueba `GET /api/oficina` antes de darlo por bueno. Si algo falla, vuelve solo al commit anterior y reinicia con ese. Si el checkout tiene cambios sin commitear, aborta sin tocar nada — evita repetir el problema de ediciones hechas directo en el servidor que nunca vuelven a GitHub. `./deploy.sh --force` reinicia igual aunque no haya commits nuevos (útil después de tocar `RelojIron.env`).

Un cron en el servidor corre `./deploy.sh` cada pocos minutos, así que normalmente no hace falta correrlo a mano — mergear a `main` alcanza.

**Secretos:** `PANEL_API_URL` e `IPAD_API_TOKEN` viven en `/home/ubuntu/RelojIron.env`, fuera de este repo. Para rotar `IPAD_API_TOKEN`: generar uno nuevo, actualizarlo ahí y en `IPAD_API_TOKEN` del `docker-compose.yml` del panel (mismo valor en los dos lados), y `./deploy.sh --force`.
