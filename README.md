# RelojIron

Sistema de clase del **profesor** en un **iPad**, en el piso de **Ironcross Calistenia** (Nicolas Farias / nicohugof). El iPad lo usa el profesor durante la clase: reloj, cronómetros, rutina y oficina (quién debe).

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

## Rutas de API (mismo host `:8090`)

El HTML llama a:

| Método | Ruta | Qué hace |
|--------|------|----------|
| GET | `/api/oficina` | Texto plano de la oficina (contadores + filas de alumnos) |
| GET | `/api/rutina?fecha=YYYY-MM-DD` | Texto de la rutina de ese día |
| GET | `/api/rutina/dias` | Texto plano: `HOY:…` `MANIANA:…` `DIAS:…` |
| POST | `/guardar` | Guarda rutina (`fecha` + `rutina`, form-urlencoded) |

Formato de `GET /api/oficina` (una línea por registro, campos con `|`):

- Contadores: `C|activos|N`, `C|vencidos|N`, `C|por_vencer|N`, `C|sin_plan|N`
- Filas: `R|V|nombre|monto|dd/mm` (vencido) o `R|P|nombre|monto|dd/mm` (por vencer)

También existe **GET `/rutina`** (y `/rutina.html`): un HTML aparte (~1.5 KB, título `Ironcross - Rutina`) para editar y guardar con un form clásico a `POST /guardar`. Esa página la genera el backend (la fecha va rellena al pedirla). `rutina.html` en este repo es una captura de esa respuesta, no un archivo estático en el Oracle.

## Backend Python

El proceso que corre hoy en el Oracle (`:8090`) es Python 3.12.3, banner `SimpleHTTP/0.6`. En esa máquina el archivo es `/home/ubuntu/rutina_server.py` (incluye `def leer_oficina` y la ruta `/api/oficina`).

**Este repo no versiona `rutina_server.py`.** Se intentó copiar el archivo que corre hoy y no se pudo:

- SSH a `ubuntu@146.181.44.106` y `opc@146.181.44.106`: `Permission denied (publickey)` (este entorno no tiene llave).
- HTTP `:8090` no sirve el `.py` (`GET /rutina_server.py` → 404). No hay listado de directorio.

No se reconstruyó ni inventó un Python a partir de la API. Si alguien con acceso al Oracle pega aquí el `rutina_server.py` vivo, se puede versionar en un PR siguiente.
