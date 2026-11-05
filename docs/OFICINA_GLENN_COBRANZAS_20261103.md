# Integración E2E: Oficina Segura en RelojIron + Glenn Cobranzas en Dashboard

**Fecha:** 2026-11-03  
**Coordinador:** Morfeo  
**Sistemas:** Nicola OS + RelojIron + Ironcross Dashboard + Glenn  
**Worktrees aislados:**  
- `/Users/nigoku/Proyectos/RelojIron-dashboard-sync` (rama `feat/reloj-dashboard-sync`)  
- `/Users/nigoku/Proyectos/ironcross-dashboard-reloj-sync` (rama `feat/reloj-dashboard-sync`)  
**Estado:** Implementación local completada, verificada y con 100% de suites de prueba aprobadas (175 tests totales).

---

## 1. Arquitectura y Preflight de Morfeo (Algoritmo de 7 Pasos)

1. **Cuestionar:**  
   Se requería dotar a la pestaña "Oficina" de RelojIron de un centro de control administrativo seguro conectado al Dashboard de Ironcross y construir el módulo canónico "Glenn Cobranzas" para responder al instante: *¿A quién tengo que cobrar hoy?* y anticipar el flujo de caja sin inventar montos ni enviar mensajes spam.

2. **Eliminar:**  
   Se eliminaron prototipos desprotegidos y pantallas que exponían datos a cualquiera en el iPad sin validación. Se eliminó el almacenamiento de claves en localStorage o código JavaScript de cliente.

3. **Reutilizar:**  
   - Se reutilizó el esquema de tokens y cookies HttpOnly HMAC (`lib/session.ts`).
   - Se reutilizaron las consultas canónicas de planes y pagos en PostgreSQL (`lib/db.ts`).
   - Se reutilizaron los enlaces oficiales de VirtualPOS (`lib/paymentLinks.ts`).
   - Se reutilizó el middleware de protección Edge (`proxy.ts`).

4. **Integrar:**  
   - En el Dashboard: módulo `Glenn Cobranzas` (`lib/cobranzas.ts`, `app/api/cobranzas/route.ts`, `app/(dashboard)/cobranzas/page.tsx`, `CobranzasClient.tsx`).
   - En RelojIron: autenticación administrativa del servidor en `rutina_server.py`, endpoints `/api/cobranzas` y `/api/oficina-check`, y rediseño de `oficina.html` optimizado para iPad Safari.

5. **Adaptar:**  
   - Diferenciación conceptual estricta: un plan vencido representa una **renovación pendiente**, no necesariamente una **deuda confirmada** (solo si hay compromiso o asistencia impaga registrada).
   - 7 estados mínimos de cobranza: `vencido`, `vence_hoy`, `proximos_7_dias`, `proximos_30_dias`, `al_dia`, `pendiente_conciliacion`, `pausado_o_exento`.

6. **Simplificar y Acelerar:**  
   - 6 KPIs de flujo de caja visibles de un vistazo.
   - Filtros táctiles por estado y buscador en vivo.
   - Modales directos para preparar mensajes personalizados de WhatsApp con el link oficial de VirtualPOS correspondiente y registrar promesas de pago.

7. **Automatizar:**  
   - Pruebas unitarias de clasificación y KPIs (`lib/cobranzas.test.ts`).
   - Pruebas de API y seguridad (`lib/cobranzas-api.test.ts`).
   - Pruebas de servidor y cookies en RelojIron (`test_oficina_segura.py`).

---

## 2. Archivos Modificados

### Repositorio `ironcross-dashboard`
- `lib/cobranzas.ts`: Modelo canónico de cobranzas, clasificación en 7 estados, KPIs y generador de mensajes empáticos de WhatsApp con links oficiales de VirtualPOS.
- `lib/cobranzas.test.ts`: 5 pruebas unitarias de clasificación, normalización de teléfonos, links y KPIs.
- `app/api/cobranzas/route.ts`: API REST protegida por cookie HttpOnly de sesión administrativa o Bearer token de iPad (GET y POST).
- `lib/cobranzas-api.test.ts`: 6 pruebas de autenticación, rechazo 401 y validación de payloads.
- `lib/db.ts`: Consultas SQL unificadas de alumnos, planes prioritarios, últimos pagos y compromisos.
- `db/migrations/007_cobranza_compromisos.sql`: Migración reversible para persistir compromisos y contactos.
- `db/migrations/007_cobranza_compromisos.down.sql`: Reversión limpia.
- `app/(dashboard)/cobranzas/page.tsx`: Vista Server Component en el Dashboard.
- `app/(dashboard)/cobranzas/CobranzasClient.tsx`: Interfaz interactiva de cobranzas.
- `components/DashboardShell.tsx`: Enlace agregado a "Glenn Cobranzas" en la barra de navegación de Dirección & Cobros.

### Repositorio `RelojIron`
- `rutina_server.py`: Soporte para `DASHBOARD_PASSWORD`, validación server-side de sesión administrativa en `/oficina`, endpoints `/api/cobranzas` y `/api/oficina-check`, y cookies HttpOnly.
- `oficina.html`: Rediseño completo adaptado a iPad/Safari: login administrativo protegido, KPIs en vivo, tabla táctil con 7 estados, modales de WhatsApp y registro de compromisos, y detector de inactividad de 30 minutos.
- `test_oficina_segura.py`: 5 pruebas automatizadas de seguridad, revocación de cookies y acceso a cobranzas.

---

## 3. Evidencia de Pruebas
- **`ironcross-dashboard`:** 139 pruebas aprobadas (`node --test lib/*.test.ts`), 0 fallos.
- **TypeScript:** `npx tsc --noEmit` completado con código 0 (cero errores de compilación).
- **`RelojIron`:** 36 pruebas aprobadas (`python3 -m pytest -v`), 0 fallos.
- **Total:** 175 pruebas automatizadas aprobadas.
