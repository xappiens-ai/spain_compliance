# Cuentas contables por cliente y proveedor (PGC)

En el PGC cada cliente tiene su subcuenta de la 430 y cada proveedor la suya de la 400 (o 410). ERPNext, por defecto, contabiliza a todos los terceros contra la cuenta por cobrar / pagar de la compañía. Esta funcionalidad crea la subcuenta del tercero automáticamente, con el siguiente número libre de la secuencia, y la deja asignada en su ficha (tabla *Cuentas* del Cliente / Proveedor).

## Configuración

Company → *Contabilidad España* → **Cuentas de clientes y proveedores** (solo visible con *Plan General Contable* activo):

| Campo | Por defecto | Uso |
|-------|-------------|-----|
| Crear cuenta contable al dar de alta clientes | No | Activa la creación automática para clientes. |
| Prefijo de las cuentas de clientes | `4300` | Las cuentas nuevas empiezan por este prefijo. |
| Dígitos de las cuentas de clientes | `8` | Longitud total del número de cuenta. |
| Crear cuenta contable al dar de alta proveedores | No | Igual para proveedores. |
| Prefijo de las cuentas de proveedores | `4000` | Usar `4100` si los terceros son acreedores por prestación de servicios. |
| Dígitos de las cuentas de proveedores | `8` | |

Al guardar la compañía se valida que el prefijo sea numérico (al menos 3 dígitos), que los dígitos sean más que la longitud del prefijo y que exista una cuenta de grupo con los 3 primeros dígitos del prefijo (`430`, `400`, `410`…), que es donde se crean las subcuentas.

Está desactivado por defecto: en una compañía con datos, activarlo cambia la cuenta con la que se contabilizan las facturas nuevas.

## Comportamiento

**Numeración.** Siguiente número tras el mayor existente con ese prefijo y esa longitud (`43000001`, `43000002`…). No se reutilizan huecos de cuentas borradas. Las cuentas con otro prefijo (`4350…`, `4009…`) no afectan a la secuencia. La numeración bloquea la cuenta de grupo mientras se crea la subcuenta, así que dos altas simultáneas no obtienen el mismo número.

**Cuenta creada.** Hija del grupo de 3 dígitos, con el nombre del tercero (recortado si hace falta), tipo *Receivable* / *Payable*, `root_type` *Asset* / *Liability* y la moneda del tercero (o la de la compañía).

**Cuándo se crea.**

- Al dar de alta el cliente o proveedor, en cada compañía PGC con la opción activa.
- Al guardar una factura de venta o compra de un tercero que todavía no la tiene (terceros anteriores a la activación). Si la factura apuntaba a la cuenta por defecto de la compañía, o a una cuenta deshabilitada, pasa a la subcuenta del tercero. Si se eligió otra cuenta a mano, se respeta. No se tocan facturas ya validadas, devoluciones ni facturas de apertura.

**Cuándo no se crea.**

- El tercero ya tiene cuenta para esa compañía (incluida la indicada a mano en el alta).
- Cliente / proveedor interno que representa a la propia compañía.
- Compañía sin PGC o con la opción desactivada.

Si la creación falla (p. ej. falta el grupo), el alta del tercero **no** se bloquea: se muestra un aviso y queda registrado en *Error Log*.

## Terceros existentes sin cuenta

Company → *Contabilidad España* → **Crear cuentas de clientes pendientes** / **Crear cuentas de proveedores pendientes**. Crea, en segundo plano y por orden de alta, la cuenta de los terceros activos sin cuenta que tienen movimientos (asientos o documentos). No modifica asientos ni facturas ya contabilizados.

Desde consola, con simulación previa:

```python
from spain_compliance.contabilidad.cuentas_tercero import crear_cuentas_pendientes
crear_cuentas_pendientes("Mi Empresa SL", "Customer", solo_con_movimientos=1, dry_run=1)
crear_cuentas_pendientes("Mi Empresa SL", "Customer", solo_con_movimientos=1, dry_run=0)
```

## Código

- `spain_compliance/contabilidad/cuentas_tercero.py`
- Hooks: `Company.validate`, `Customer.after_insert`, `Supplier.after_insert`, `Sales Invoice.before_validate`, `Purchase Invoice.before_validate`.
- Tests: `spain_compliance/tests/test_cuentas_tercero.py`.
