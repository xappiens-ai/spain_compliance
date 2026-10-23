# Registro fiscal de IVA

Al validar una factura de venta o de compra, Spain Compliance guarda su desglose fiscal en **Registro Fiscal IVA**: una fila por clave de operación y tipo impositivo. De aquí saldrán los libros registro y los modelos (303, 390, 349, 347, retenciones). Cancelar la factura no borra las filas: las marca como anuladas.

Solo ocurre en compañías con país **Spain** o con el Plan General Contable activo. El resto de compañías del sitio no se toca.

## Clasificación

En cada fila de impuesto (y en la plantilla, que es el mismo dato) sección *Clasificación fiscal (España)*:

| Campo | Uso |
|-------|-----|
| Tipo de impuesto | IVA, recargo de equivalencia, retención de IRPF, IGIC, IPSI u otro. |
| Clave de IVA | Sujeta, exenta (por artículo), no sujeta, inversión del sujeto pasivo, intracomunitaria, importación, exportación… El código (`S1`, `E1`, `AIB`) es lo que usarán los modelos. |
| Deducibilidad | Solo compras de IVA, recargo, IGIC o IPSI: corriente o bien de inversión (los dos aplican la prorrata de la compañía) o no deducible. |
| Clave de retención | Trabajo, actividades económicas, arrendamiento, capital mobiliario o premios. |

En **Item Tax Template**, *Clave de IVA* sustituye a la de la fila de impuesto para los artículos que usen esa plantilla. Sirve para una factura con operaciones de distinta clave (sujeta y exenta).

Si la fila de la factura está vacía y hay plantilla, al validar se copia la clasificación de la fila de plantilla con la misma cuenta y el mismo tipo. Lo ya informado en la factura no se pisa.

## Qué se guarda

Por cada fila de impuesto con tipo informado, o sin tipo pero con cuenta de tipo *Tax* (un cargo *Actual* que no sea impuesto no entra):

- Libro: expedidas o recibidas.
- Ejercicio, trimestre (`1T`…`4T`) y mes, por la fecha de contabilización.
- Tercero, con el NIF y el tipo de identificación tal como estaban al validar. País `ES` si el NIF es español; si es NIF-IVA, las dos letras del país.
- Tipo de factura `F1`, o `R1` si es rectificativa, con la factura rectificada.
- Base, tipo y cuota en moneda de la compañía. Una rectificativa queda en negativo, así que el trimestre cuadra al sumar.
- En compras de IVA, recargo, IGIC o IPSI, cuota deducible: cero si no es deducible; en corriente y en bien de inversión, la cuota por la prorrata general. La prorrata vacía cuenta como 100 %. La regularización de los bienes de inversión en años posteriores queda para el modelo 303.
- *Pendiente de clasificar* si falta el tipo, la clave o, en compras, la deducibilidad.

La base sale de la cuota y el tipo (`cuota × 100 / tipo`). Al 0 % se usa el neto de los artículos de esa clave.

## Aviso o bloqueo

Por defecto la factura se valida igual y las filas quedan pendientes de clasificar, con un aviso. **Exigir clasificación fiscal** en la compañía (sección *Fiscalidad*) impide validarla —el borrador se guarda— hasta que cada impuesto tenga tipo, clave (también IGIC e IPSI) y, en compras, deducibilidad.

## Identificación del tercero

En Cliente y Proveedor, *Tipo de identificación fiscal*. Al guardar se comprueba el dígito de control del NIF, NIE o CIF, y el NIF-IVA (si empieza por `ES`, el resto tiene que ser un NIF válido; otro país solo se comprueba el formato). Si no cuadra se avisa y el tercero se guarda igual. Pasaporte, documento oficial y certificado de residencia no se validan como NIF.

## Reconstruir facturas ya validadas

Company → **Contabilidad España** → *Reconstruir registro fiscal de IVA* (gestor de cuentas). Primero muestra una vista previa, sin escribir. Al confirmar, recalcula en segundo plano las facturas validadas de esa compañía y sustituye sus filas vigentes.

Las facturas antiguas no se modifican. Si su fila de impuesto no tiene clasificación, el registro usa la de la plantilla en ese momento. Clasifica las plantillas antes de reconstruir si quieres que el histórico quede bien.

No se lanza solo: ni al migrar ni al instalar.

## Lo que todavía no hace

No genera el libro registro ni el 303: solo deja el desglose. Los asientos (Journal Entry) no entran. Una misma fila de impuesto con artículos de distinta clave que además comparten código de artículo no se puede separar, porque ERPNext los agrupa; en ese caso manda la clave de la fila.
