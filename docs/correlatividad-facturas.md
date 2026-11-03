# Correlatividad de facturas (serie + fecha)

## Regla (RD 1619/2012, art. 6)

Dentro de cada **serie**, la numeración de las facturas debe ser **correlativa**. En la práctica de facturación española eso implica también **orden cronológico**:

1. Un número mayor no puede tener fecha de expedición **anterior** a un número menor de la misma serie.
2. La fecha de expedición no puede ser **posterior a hoy**.

## Cuándo se asigna el número

El número de factura es el de ERPNext: se asigna al **insertar** el documento (borrador o validada) según `naming_series`.

| Estado | Nombre del documento |
|--------|----------------------|
| Borrador / validada / cancelada | Serie oficial (`…F26…`, `…R26…`, …) |

La correlatividad se comprueba al **guardar** y al **validar**, sobre ese `name`.

La app lo aplica **siempre**. No hay interruptor en Company.

La **serie legal** se identifica por el prefijo del número del documento (el mismo que usa `tabSeries`, p. ej. `ACMEF26` en `ACMEF2600060`), no por el texto literal del campo `naming_series`. Plantillas distintas que resuelven al mismo contador se validan juntas.

Entran en el orden todos los documentos de la serie con ese prefijo (validadas, canceladas y borradores). Las enmiendas (`…-1`) siguen el esquema de ERPNext y cuentan en la misma serie.

`before_validate` sigue ejecutándose con `ignore_validate=True` (API / scripts).

## Qué bloquea el ERP

| Acción | Resultado |
|--------|-----------|
| Guardar / validar SI con `posting_date` > hoy | Error |
| Guardar / validar SI cuya fecha rompe el orden respecto a números ya existentes de la serie | Error |
| Misma serie con `naming_series` distinto en el campo (sinónimo / resuelto) | Se valida igual |
| Varias facturas el mismo día | Permitido |

## Auto Repeat

1. Emitir (validar) la factura del **periodo real** con la fecha de ese periodo.
2. Crear el **Auto Repeat** sobre esa factura.
3. El planificador genera la siguiente SI el día `next_schedule_date` (idealmente con `submit_on_creation`).

No crear de antemano borradores con fechas futuras: el ERP los rechazará.

## Relación con rectificativas

Las facturas de abono van en su **propia serie** (ver [series-facturas-abono.md](series-facturas-abono.md)). La correlatividad se comprueba **dentro de cada prefijo de contador**, así que la serie ordinaria (`…F26…`) y la de rectificativas (`…R26…`) no se mezclan.
