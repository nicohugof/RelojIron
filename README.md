# RelojIron

Sistema de entrenamiento con el que el **profesor** da la clase en un iPad, en el piso de **Ironcross Calistenia** (Nicolas Farias / nicohugof). El iPad lo usa el profesor durante la clase.

Corre en un **iPad 1** (iOS 5.1.1, Safari viejo).

## Cómo se sirve

En el gym la app vive en HTTP plano:

```
http://146.181.44.106:8090
```

El servidor en el Oracle es Python (`SimpleHTTP` + handlers de rutina). `SimpleHTTP` sirve `index.html` en `/`. El iPad 1 no tiene `fetch` ni flexbox: el HTML usa ES5, `XMLHttpRequest` y `display:table` / `table-cell`. No modernizar el JS/CSS.

## Pestañas (`index.html`)

1. **RELOJ** — hora a pantalla completa.
2. **CRONOMETROS** — cronómetros y temporizadores con beep al terminar la cuenta regresiva.
3. **RUTINA** — rutinas por fecha (carga/guarda contra la API del mismo host).

## Rutas de API (mismo host `:8090`)

El HTML llama a:

| Método | Ruta | Qué hace |
|--------|------|----------|
| GET | `/api/rutina?fecha=YYYY-MM-DD` | Texto de la rutina de ese día |
| GET | `/api/rutina/dias` | Texto plano: `HOY:…` `MANIANA:…` `DIAS:…` |
| POST | `/guardar` | Guarda rutina (`fecha` + `rutina`, form-urlencoded) |

También existe **GET `/rutina`** (y `/rutina.html`): un HTML aparte (~1.5 KB, título `Ironcross - Rutina`) para editar y guardar con un form clásico a `POST /guardar`. Esa página la genera el backend (la fecha va rellena al pedirla). `rutina.html` en este repo es una captura de esa respuesta, no un archivo estático en el Oracle.

## Backend Python

`rutina_server.py` vive en el servidor Oracle `:8090` y **no está versionado aquí**. No hay SSH a esa máquina desde este repo.
