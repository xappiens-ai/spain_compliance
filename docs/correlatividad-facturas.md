# Correlatividad de facturas (serie + fecha)

## Regla (RD 1619/2012, art. 6)

Dentro de cada **serie**, la numeración de las facturas debe ser **correlativa**. En la práctica de facturación española eso implica también **orden cronológico**:

1. Un número mayor no puede tener fecha de expedición **anterior** a un número menor de la misma serie.
2. La fecha de expedición no puede ser **posterior a hoy** al guardar: en ERPNext el nombre (número) se asigna al **guardar el borrador**, no al validar. Reservar un número con fecha futura es el anti-patrón que deja huecos cronológicos cuando luego se emiten facturas del periodo intermedio.

La app lo aplica **siempre** en `Sales Invoice.validate` (`spain_compliance.contabilidad.correlatividad`). No hay interruptor en Company: es compliance, no configuración.

Entran en el orden **borradores, validadas y canceladas** de la misma compañía y `naming_series` (cancelar no libera el número ni borra su fecha del criterio).

## Qué bloquea el ERP

| Acción | Resultado |
|--------|-----------|
| Guardar SI con `posting_date` > hoy | Error |
| Guardar SI cuyo nombre es mayor que otra de la misma serie con fecha **posterior** | Error |
| Guardar SI cuyo nombre es menor que otra de la misma serie con fecha **anterior** | Error |
| Varias facturas el mismo día | Permitido |

## Anti-patrón (cuotas / Auto Repeat)

**Incorrecto:** crear en septiembre un borrador de la cuota de noviembre (fecha futura) “para colgarle” el Auto Repeat. Ese borrador **ya consume** un número de serie. Si después sale una factura de octubre, serie y fechas quedan desordenadas.

**Correcto:**

1. Emitir (validar) la factura del **periodo real** con la fecha de ese periodo.
2. Crear el **Auto Repeat** sobre esa factura, con `start_date` = fecha de esa factura (o el día de recurrencia del ciclo) y frecuencia mensual. El `next_schedule_date` queda en el mes siguiente.
3. El planificador de Frappe genera la siguiente SI **el día** `next_schedule_date` (copia el documento, pone las fechas obligatorias a esa fecha, y avanza el siguiente ciclo). Opcionalmente `submit_on_creation`.

No hace falta (ni se debe) materializar con antelación el borrador del mes que viene.

## Auto Repeat (cómo funciona en Frappe)

- DocType **Auto Repeat**: apunta a un documento de referencia (`reference_doctype` + `reference_document`).
- Campos clave: `frequency`, `start_date`, `next_schedule_date`, `end_date`, `submit_on_creation`, `disabled`.
- Al guardar el AR, Frappe enlaza `Sales Invoice.auto_repeat` al nombre del AR.
- El job diario `make_auto_repeat_entry` busca AR activos con `next_schedule_date <= hoy` y, si la fecha programada es **hoy**, llama a `create_documents()`:
  - Copia la factura de referencia.
  - Pone `set_posting_time = 1` y las fechas obligatorias (p. ej. `posting_date`) a `next_schedule_date`.
  - `insert` (y `submit` si está marcado).
  - Calcula el siguiente `next_schedule_date`.
- Si la generación falla, el AR se desactiva y se registra el error.

Por eso la factura de referencia debe ser la del periodo **ya emitido**, no un borrador futuro.

## Relación con rectificativas

Las facturas de abono van en su **propia serie** (ver [series-facturas-abono.md](series-facturas-abono.md)). La correlatividad se comprueba **dentro de cada** `naming_series`, así que la serie ordinaria y la de rectificativas no se mezclan.
