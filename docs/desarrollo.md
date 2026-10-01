# Directrices de desarrollo — Spain Compliance (`spain_compliance`)

Este documento es la referencia para ampliar la app. Si hay duda entre "inventar un componente" y "usar frappe-ui", **siempre gana frappe-ui**. Si hay duda entre "hardcodear un valor" y "ponerlo en un campo de Company", **siempre gana el campo**.

## Qué es esta app

App de **contabilidad y compliance español** sobre **ERPNext**, en dos capas:

- **Backend Frappe** (`spain_compliance/`): overrides de DocTypes ERPNext, Custom Fields, tareas programadas, parches de informes.
- **SPA** (`frontend/`): Vue 3 + **frappe-ui** (mismo lenguaje visual que Helpdesk y Frappe CRM), servida en `/contabilidad`.

Datos:

- **Nombre técnico:** `spain_compliance`
- **Título:** Spain Compliance (Apps screen: *Contabilidad*)
- **Ruta SPA:** `/contabilidad`
- **Rama:** `version-15` (Frappe/ERPNext 15)
- **Dependencias:** `frappe/erpnext`

No es Frappe Books (desktop + SQLite). No sustituye al Desk: los formularios de negocio siguen siendo los de ERPNext.

## Principio: instalable en cualquier sitio

La app se publica en el Marketplace de Frappe Cloud. Por tanto:

- **Cero referencias a un sitio concreto**: dominios, rutas de bench, nombres de compañía, abreviaturas, nombres de cuentas, series concretas.
- Todo lo que dependa de la empresa vive en **campos de `Company`** definidos en `spain_compliance/setup/custom_fields.py` (sección *Contabilidad España*).
- Los Custom Fields **no llevan prefijo `custom_`** (ese prefijo es de Customize Form). Se crean en `after_install` / `after_migrate` y se eliminan en `before_uninstall`.
- Las funciones que cambian datos en masa (p. ej. conversión al PGC) deben ser **idempotentes**, pedir confirmación en la UI y ejecutarse en segundo plano.
- Lo que cambie cómo se contabiliza en compañías existentes va **desactivado por defecto** (opt-in en Company).
- Las cadenas de usuario van con `_()` / `__()`.

## Arquitectura

```
Apps screen  →  /contabilidad
                 www/contabilidad.py  (login, permiso, boot Jinja)
                 www/contabilidad.html (generado por yarn build)
                 SPA Vue 3 + frappe-ui
                   Layout (Sidebar + header + slot)
                   ListViewBuilder / páginas
                   createListResource → DocTypes ERPNext

ERPNext Desk
  Sales Invoice  ← override (serie rectificativa, Dudoso Cobro / Pérdida) + public/js/sales_invoice.js
  Account        ← override (root_type propio en compañías PGC)
  Company        ← Custom Fields + public/js/company.js (conversión PGC, cuentas de tercero pendientes)
  Customer / Supplier / facturas ← doc_events: subcuenta 430/400 por tercero (cuentas_tercero.py)
  Informes financieros ← monkey_patches.py (Balance / PyG con árbol PGC)
```

| Capa | Dónde | Rol |
|------|--------|-----|
| Python Frappe | `spain_compliance/` | hooks, overrides, `www`, APIs, permisos, futuros DocTypes propios |
| SPA | `frontend/` | UI. Todo lo visual vive aquí |
| ERPNext | app requerida | Diario, cuentas, compañías, etc. No duplicar esos DocTypes |

## Mapa de ficheros

### Backend

| Fichero | Rol |
|---------|-----|
| `hooks.py` | `required_apps`, `add_to_apps_screen`, `website_route_rules`, overrides, `doctype_js`, scheduler |
| `install.py` | `after_install` / `after_migrate` / `before_uninstall`: Custom Fields y Property Setter de `Sales Invoice.status` |
| `setup/custom_fields.py` | Definición única de los Custom Fields de la app |
| `overrides/sales_invoice.py` | Serie rectificativa por Company; estados Dudoso Cobro / Pérdida; API `set_cobro_status` |
| `overrides/account.py` | `root_type` propio por cuenta en compañías PGC |
| `contabilidad/plan_contable.py` | Grupos/subgrupos PGC, `reestructurar_arbol`, API `convertir_plan_a_pgc` |
| `contabilidad/cuentas_tercero.py` | Subcuenta por cliente/proveedor con secuencia PGC; backfill `crear_cuentas_pendientes` ([cuentas-tercero.md](cuentas-tercero.md)) |
| `monkey_patches.py` | Parches de `erpnext.accounts.report.financial_statements` para el árbol PGC |
| `tasks.py` | Tarea diaria `auto_mark_dudoso_cobro` (por Company, `meses_dudoso_cobro`) |
| `www/contabilidad.py` | Contexto SPA: Guest → login, `has_app_permission`, `get_boot` |
| `api/permission.py` | Accounts User / Manager / System Manager / Administrator |
| `api/dashboard.py` | Métricas del tablero |
| `public/js/*.js` | Form scripts de Desk (Sales Invoice, Company) |
| `patches/` | Migraciones de datos (`patches.txt`) |
| `tests/` | Tests de integración (`FrappeTestCase`) |

### Frontend

| Fichero | Rol |
|---------|-----|
| `frontend/vite.config.js` | Plugin `frappe-ui/vite`: `frappeProxy`, `lucideIcons`, `jinjaBootData`, `outDir` + `indexHtmlPath` |
| `frontend/src/main.js` | `FrappeUI`, `spritePlugin`, Pinia, router, boot en DEV |
| `frontend/src/App.vue` | `FrappeUIProvider` + layout desktop/móvil |
| `frontend/src/router.js` | `createWebHistory('/contabilidad')` |
| `frontend/src/navigation.js` | Secciones e ítems del sidebar |
| `frontend/src/components/Layouts/*` | Shell |
| `frontend/src/components/ListViewBuilder.vue` | Listas |
| `frontend/src/pages/*` | Páginas |

## Referencia de UI (no negociable)

Plantilla de chrome: **Helpdesk**. Librería: **frappe-ui `1.0.0-beta.29`**.

Usar **componentes originales** de `frappe-ui`. Está prohibido:

- Recrear Sidebar, Dialog, Button, List, Badge, Dropdown, Breadcrumbs, ScrollArea, etc. con HTML/CSS propio "parecido".
- `FeatherIcon` / `feather-icons` en UI nueva.
- CSS de producto (sombras, paletas, cards de marketing). Solo tokens de frappe-ui: `text-ink-*`, `bg-surface-*`, `border-outline-*`.

### Chrome (layout)

| Pieza | Componente frappe-ui |
|-------|----------------------|
| Columna lateral | `Sidebar` + `v-model:collapsed` |
| Ítems / secciones | `SidebarItem`, `SidebarLabel` |
| Scroll del menú | `ScrollArea` |
| Contraer | `SidebarCollapseToggle` |
| Menú usuario | `Dropdown` |
| Cabecera de página | `LayoutHeader` (teleport a `#app-header`) + `Breadcrumbs` |
| Acciones | `Button` (`variant`, `theme`, `icon="lucide-..."`) |

Iconos: **Lucide**. Vite tiene `lucideIcons: true`:

```js
import LucideFileText from '~icons/lucide/file-text'
```

### Listas

Un único **`ListViewBuilder`** sobre las primitivas `ListView`, `ListHeader`, `ListHeaderItem`, `ListRows`, `ListRow`, `ListRowItem`, `ListSelectBanner`, `ListFooter`, `LoadingIndicator`. Datos: `createListResource` contra el DocType. Conteos: `frappe.client.get_count`.

**No** copiar el patrón CRM de un `*ListView.vue` por DocType. **No** sustituir el slot por defecto de `ListRows` y esperar que itere filas: en frappe-ui 1.0.0-beta.29 ese slot **reemplaza** el `v-for`. Iterar `ListRow` a mano (como hace el builder). Celdas en el slot `#cell` de `ListRowItem`.

### Vacío / "próximamente"

`EmptyState` (`frontend/src/components/EmptyState.vue`) con tokens frappe-ui.

### Formularios y diálogos

`Dialog`, `FormControl`, `TextInput`, `Autocomplete`, `Select` de frappe-ui. Documentos ERPNext: `createDocumentResource` / APIs Frappe.

## Cómo añadir una pantalla

1. Ruta en `frontend/src/router.js` (nombre estable, kebab-case en path).
2. Ítem en `frontend/src/navigation.js` (icono Lucide con `markRaw`).
3. Página con `LayoutHeader`. Si es lista → `ListViewBuilder` sobre un DocType ERPNext (o propio, cuando exista).
4. Permiso: si no basta Accounts*, ampliar `has_app_permission` y, si aplica, `has_permission` del DocType.
5. Cadenas con `__()`.
6. `yarn build` para producción; `yarn dev` para iterar.

## Python / Frappe

- APIs whitelistadas en `spain_compliance/api/` o junto al dominio (`contabilidad/`, `overrides/`). Siempre con comprobación de permisos explícita.
- DocTypes propios solo cuando ERPNext no cubra el concepto (SII, Verifactu, modelos Hacienda). Diario y cuentas: DocTypes ERPNext.
- CSRF en `get_boot`: solo si existe `frappe.local.session_obj`.
- Los overrides de clase (`override_doctype_class`) son exclusivos por DocType en Frappe: si otra app también sobrescribe `Sales Invoice` o `Account`, documentarlo en el README.
- Tras cambiar Python, hooks o traducciones:

```bash
bench --site <sitio> migrate
bench --site <sitio> clear-cache
bench restart
```

## Tests

Tests de integración en `spain_compliance/tests/`, con `FrappeTestCase` (cada test se deshace al terminar). Crean sus propias compañías `_Test SC …` con árbol PGC, así que no dependen de datos del sitio.

- **Nunca en un sitio con datos reales**: usar un sitio desechable con ERPNext y la app, y `allow_tests`.
- Toda funcionalidad nueva con efectos en BD lleva sus tests: casos normales, configuración inválida, idempotencia y compañías sin PGC (no debe hacer nada).
- Los fixtures que necesitan grupos de cliente / proveedor / artículo crean los suyos (no hay datos de demo en un sitio limpio).

```bash
bench new-site <test-site> --install-app erpnext --install-app spain_compliance
bench --site <test-site> set-config allow_tests true
bench --site <test-site> run-tests --app spain_compliance
bench --site <test-site> run-tests --module spain_compliance.tests.test_cuentas_tercero
```

## Build, assets y Git

- **Node ≥ 20.11** (recomendado 22, `.nvmrc`) para `yarn` / `yarn build`. Con Node 18 falla la carga de `vite.config.js`.
- Root `package.json` delega `build`/`dev` a `frontend/`; `bench build` lo invoca automáticamente.
- Assets gitignored: `spain_compliance/public/frontend` y `www/contabilidad.html`. Un clone o CI **debe** ejecutar `yarn build` o `/contabilidad` queda roto.
- Los `/assets` se sirven por nginx en producción, no por el puerto de gunicorn.

```bash
cd apps/spain_compliance/frontend
yarn
yarn dev    # desarrollo (proxy Frappe)
yarn build  # producción → public/frontend + www/contabilidad.html
```

## Git

- Rama pública: `version-15` (GitHub). El repositorio canónico es el GitLab interno de Xappiens; GitHub recibe el mismo código en cada publicación. Detalle: [publicacion.md](publicacion.md).
- La app se prueba en un ERPNext **en producción**: patches idempotentes y nada de escrituras masivas sin confirmación.
- No mezclar cambios de Frappe 16 en esta rama.
- Sin secretos, sin dumps, sin configuración de sitios concretos en el repo.

## Hoja de ruta (pendiente de decidir)

- Plantilla de plan de cuentas PGC completa (con `account_number` y `root_type` por cuenta) para compañías nuevas.
- Modelos de Hacienda (303, 390, 347, 349, 111, 115, 190…), SII, Verifactu.
- Formulario de asiento y árbol de cuentas en la SPA.
- Rama `version-16`.
