# Correlatividad de facturas (serie + fecha)

## Regla (RD 1619/2012, art. 6)

Dentro de cada **serie**, la numeración de las facturas debe ser **correlativa**. En la práctica de facturación española eso implica también **orden cronológico**:

1. Un número mayor no puede tener fecha de expedición **anterior** a un número menor de la misma serie.
2. La fecha de expedición no puede ser **posterior a hoy** al emitir (validar) la factura.

## Cuándo se asigna el número

El número **oficial** de factura se asigna al **validar** (submit), no al guardar el borrador.

| Estado | Nombre del documento | Serie legal |
|--------|----------------------|-------------|
| Borrador nuevo | Provisional (`SCBOR-…`) | Aún no consume contador |
| Validada / cancelada | Serie oficial (`…F26…`, `…R26…`) | Sí |

El campo `naming_series` del borrador guarda la **serie oficial prevista** (ordinaria o rectificativa). Al validar, el documento se renombra al siguiente número de esa serie y entonces se comprueba la correlatividad.

Así se evita el anti-patrón de ERPNext (reservar número al guardar) que dejaba borradores atrapados o huecos al validar.

La app lo aplica **siempre**. No hay interruptor en Company.

La **serie legal** se identifica por el prefijo del número del documento (el mismo que usa `tabSeries`, p. ej. `ACMEF26` en `ACMEF2600060`), no por el texto literal del campo `naming_series`. Plantillas distintas que resuelven al mismo contador se validan juntas.

Entran en el orden facturas con **número oficial** (validadas, canceladas y borradores legados que ya lo tuvieran). Los `SCBOR-…` no cuentan. Las enmiendas (`…-1`) siguen el esquema de ERPNext y cuentan en la misma serie.

`before_validate` sigue ejecutándose con `ignore_validate=True` (API / scripts).

## Qué bloquea el ERP

| Acción | Resultado |
|--------|-----------|
| Guardar borrador (nombre provisional) | OK; no consume serie oficial |
| Validar SI con `posting_date` > hoy | Error (antes de fijar el número o al comprobar) |
| Validar SI cuya fecha rompe el orden respecto a números ya oficiales | Error |
| Misma serie con `naming_series` distinto en el campo (sinónimo / resuelto) | Se valida igual |
| Varias facturas el mismo día | Permitido |

## Anti-patrón (cuotas / Auto Repeat)

**Incorrecto (antes):** crear en septiembre un borrador de la cuota de noviembre con número oficial ya reservado.

**Ahora:** se puede guardar un borrador con fecha futura (nombre `SCBOR-…`); **no** se puede **validar** hasta que la fecha sea ≤ hoy. Lo habitual sigue siendo:

1. Emitir (validar) la factura del **periodo real** con la fecha de ese periodo.
2. Crear el **Auto Repeat** sobre esa factura.
3. El planificador genera la siguiente SI el día `next_schedule_date` (idealmente con `submit_on_creation`).

## Auto Repeat (cómo funciona en Frappe)

- DocType **Auto Repeat**: apunta a un documento de referencia (`reference_doctype` + `reference_document`).
- Al generar: copia, pone fechas a `next_schedule_date`, `insert` (nombre provisional) y `submit` si está marcado (ahí recibe el número oficial).
- Si la generación falla, el AR se desactiva y se registra el error.

## Relación con rectificativas

Las facturas de abono van en su **propia serie** (ver [series-facturas-abono.md](series-facturas-abono.md)). La correlatividad se comprueba **dentro de cada prefijo de contador**, así que la serie ordinaria (`…F26…`) y la de rectificativas (`…R26…`) no se mezclan.
