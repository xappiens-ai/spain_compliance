# Series de facturas y facturas rectificativas

## Regla

En España la factura rectificativa (abono) debe emitirse en una **serie propia**, separada de la serie ordinaria (art. 6 del Reglamento de facturación, RD 1619/2012).

| Tipo | Serie recomendada | Ejemplo (compañía con abreviatura `ACME`, 2026) |
|------|-------------------|--------------------------------------------------|
| Factura ordinaria | `{company_abbr}.F.YY.{#####}` | `ACMEF2600028` |
| **Factura rectificativa** | `{company_abbr}.R.YY.{#####}` | `ACMER2600002` |

`{company_abbr}` es la abreviatura de la Company (`Company.abbr`). La app la rellena justo antes de nombrar la factura, así que se puede usar en las series sin crear un campo. El resto de comodines (`.YY.`, `.MM.`, `{#####}`…) son los estándar de Frappe.

## Configuración

1. **Customize Form → Sales Invoice → `naming_series`**: añade las series ordinaria y rectificativa a las opciones y marca la ordinaria como valor por defecto.
2. **Company → Contabilidad España → Serie de facturas rectificativas**: escribe la serie rectificativa (p. ej. `{company_abbr}.R.YY.{#####}`). Vacío = no se fuerza nada.

## Comportamiento

`make_sales_return` de ERPNext **copia** la `naming_series` de la factura original a la rectificativa. Con la serie configurada en la Company:

- **Servidor** (`spain_compliance.overrides.sales_invoice.SalesInvoice.before_naming`): si `is_return` y la serie actual está vacía, es la copiada de la factura rectificada (`return_against`) o es la serie ordinaria por defecto → se sustituye por la serie rectificativa **antes de asignar nombre**.
- **Formulario** (`public/js/sales_invoice.js`): mismo criterio al marcar *Is Return* o cambiar la compañía.

Si el usuario elige a mano otra serie distinta (p. ej. una serie rectificativa de un ejercicio anterior, `{company_abbr}.R.25.{#####}`), se respeta.

## Contadores (`tabSeries`)

Cada prefijo resuelto tiene su contador, p. ej. `ACMEF26` y `ACMER26`. **Cancelar** una factura **no** libera el número. Si una rectificativa se creó por error en la serie ordinaria:

1. Cancelar (si estaba validada).
2. Eliminar el documento cancelado.
3. Ajustar el contador del prefijo (`tabSeries.current`) al **mayor número que siga existiendo** en esa serie y ejercicio.

## No hacer

- Emitir rectificativas en la serie ordinaria.
- Reutilizar a mano un número ya emitido.
- Bajar un contador por debajo de un documento que **aún existe**.

## Correlatividad (serie + fecha)

Además de la serie propia de abonos, dentro de **cada** serie la numeración debe ser correlativa y cronológica. La app lo valida en servidor (sin interruptor). Detalle y patrón correcto con Auto Repeat: [correlatividad-facturas.md](correlatividad-facturas.md).
