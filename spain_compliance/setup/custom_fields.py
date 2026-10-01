# Copyright (c) 2026, Xappiens and contributors
# License: MIT

"""Custom Fields owned by Spain Compliance.

All fields are created on install / migrate and removed on uninstall.
Field names intentionally have no ``custom_`` prefix (that prefix is reserved
for fields created through Customize Form on a site).
"""

from __future__ import annotations

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields, delete_custom_fields

# Company -----------------------------------------------------------------
COMPANY_PGC_FIELDNAME = "pgc_espanol"
COMPANY_RETURN_SERIES_FIELDNAME = "serie_rectificativas"
COMPANY_DUDOSO_MONTHS_FIELDNAME = "meses_dudoso_cobro"

# Cuentas auxiliares por tercero (430 clientes / 400 proveedores)
COMPANY_CUSTOMER_AUTO_FIELDNAME = "crear_cuenta_cliente_auto"
COMPANY_CUSTOMER_PREFIX_FIELDNAME = "prefijo_cuenta_cliente"
COMPANY_CUSTOMER_DIGITS_FIELDNAME = "digitos_cuenta_cliente"
COMPANY_SUPPLIER_AUTO_FIELDNAME = "crear_cuenta_proveedor_auto"
COMPANY_SUPPLIER_PREFIX_FIELDNAME = "prefijo_cuenta_proveedor"
COMPANY_SUPPLIER_DIGITS_FIELDNAME = "digitos_cuenta_proveedor"

DEFAULT_CUSTOMER_PREFIX = "4300"
DEFAULT_SUPPLIER_PREFIX = "4000"
DEFAULT_ACCOUNT_DIGITS = 8

DEFAULT_RETURN_SERIES = "{company_abbr}.R.YY.{#####}"

# Created by an early draft of this app. ERPNext already exposes
# ``company_abbr`` as a property on AccountsController, so a Custom Field
# with that name is rejected on a clean install.
LEGACY_FIELDS: dict[str, list[str]] = {
	"Sales Invoice": ["company_abbr"],
}

CUSTOM_FIELDS: dict[str, list[dict]] = {
	"Company": [
		{
			"fieldname": "spain_compliance_section",
			"label": "Contabilidad España",
			"fieldtype": "Section Break",
			"insert_after": "country",
			"collapsible": 1,
		},
		{
			"fieldname": COMPANY_PGC_FIELDNAME,
			"label": "Plan General Contable (árbol de 9 grupos)",
			"fieldtype": "Check",
			"insert_after": "spain_compliance_section",
			"description": (
				"Cada cuenta conserva su propio tipo raíz (activo, pasivo, ...) aunque el grupo "
				"padre tenga otro. Necesario para el PGC, donde un mismo grupo mezcla cuentas de "
				"activo y pasivo (430 Clientes / 438 Anticipos de clientes, 470 / 475 Hacienda ...)."
			),
		},
		{
			"fieldname": COMPANY_RETURN_SERIES_FIELDNAME,
			"label": "Serie de facturas rectificativas",
			"fieldtype": "Data",
			"insert_after": COMPANY_PGC_FIELDNAME,
			"description": (
				"Serie que se fuerza en las facturas de venta de abono (rectificativas) de esta "
				"compañía. Dejar vacío para no forzar ninguna. Ejemplo: "
				"<code>{company_abbr}.R.YY.{#####}</code>. <code>{company_abbr}</code> es la "
				"abreviatura de la compañía; el resto de comodines son los de Frappe."
			),
		},
		{
			"fieldname": "spain_compliance_column",
			"fieldtype": "Column Break",
			"insert_after": COMPANY_RETURN_SERIES_FIELDNAME,
		},
		{
			"fieldname": COMPANY_DUDOSO_MONTHS_FIELDNAME,
			"label": "Meses hasta Dudoso Cobro",
			"fieldtype": "Int",
			"insert_after": "spain_compliance_column",
			"default": "0",
			"description": (
				"Meses desde el vencimiento tras los que una factura de venta impagada pasa "
				"automáticamente a estado <b>Dudoso Cobro</b> (tarea diaria). 0 desactiva la "
				"automatización. El artículo 13 de la Ley del Impuesto sobre Sociedades usa 6 meses."
			),
		},
		{
			"fieldname": "cuentas_tercero_section",
			"label": "Cuentas de clientes y proveedores",
			"fieldtype": "Section Break",
			"insert_after": COMPANY_DUDOSO_MONTHS_FIELDNAME,
			"collapsible": 1,
			"depends_on": f"eval:doc.{COMPANY_PGC_FIELDNAME}",
			"description": (
				"Al dar de alta un cliente o proveedor se crea su cuenta auxiliar con el siguiente "
				"número libre de la secuencia (p. ej. 43000001, 43000002 ...) y se asigna al tercero. "
				"Los terceros sin cuenta la reciben al guardar su primera factura."
			),
		},
		{
			"fieldname": COMPANY_CUSTOMER_AUTO_FIELDNAME,
			"label": "Crear cuenta de cliente automáticamente",
			"fieldtype": "Check",
			"insert_after": "cuentas_tercero_section",
			"default": "0",
		},
		{
			"fieldname": COMPANY_CUSTOMER_PREFIX_FIELDNAME,
			"label": "Prefijo de cuentas de cliente",
			"fieldtype": "Data",
			"insert_after": COMPANY_CUSTOMER_AUTO_FIELDNAME,
			"default": DEFAULT_CUSTOMER_PREFIX,
			"depends_on": f"eval:doc.{COMPANY_CUSTOMER_AUTO_FIELDNAME}",
			"mandatory_depends_on": f"eval:doc.{COMPANY_CUSTOMER_AUTO_FIELDNAME}",
			"description": (
				"Inicio común de los números de cuenta. Las tres primeras cifras indican el grupo "
				"padre (430 Clientes), que debe existir en el árbol."
			),
		},
		{
			"fieldname": COMPANY_CUSTOMER_DIGITS_FIELDNAME,
			"label": "Dígitos de cuentas de cliente",
			"fieldtype": "Int",
			"insert_after": COMPANY_CUSTOMER_PREFIX_FIELDNAME,
			"default": str(DEFAULT_ACCOUNT_DIGITS),
			"depends_on": f"eval:doc.{COMPANY_CUSTOMER_AUTO_FIELDNAME}",
			"mandatory_depends_on": f"eval:doc.{COMPANY_CUSTOMER_AUTO_FIELDNAME}",
			"description": "Longitud total del número de cuenta (prefijo incluido).",
		},
		{
			"fieldname": "cuentas_tercero_column",
			"fieldtype": "Column Break",
			"insert_after": COMPANY_CUSTOMER_DIGITS_FIELDNAME,
		},
		{
			"fieldname": COMPANY_SUPPLIER_AUTO_FIELDNAME,
			"label": "Crear cuenta de proveedor automáticamente",
			"fieldtype": "Check",
			"insert_after": "cuentas_tercero_column",
			"default": "0",
		},
		{
			"fieldname": COMPANY_SUPPLIER_PREFIX_FIELDNAME,
			"label": "Prefijo de cuentas de proveedor",
			"fieldtype": "Data",
			"insert_after": COMPANY_SUPPLIER_AUTO_FIELDNAME,
			"default": DEFAULT_SUPPLIER_PREFIX,
			"depends_on": f"eval:doc.{COMPANY_SUPPLIER_AUTO_FIELDNAME}",
			"mandatory_depends_on": f"eval:doc.{COMPANY_SUPPLIER_AUTO_FIELDNAME}",
			"description": (
				"Inicio común de los números de cuenta. Las tres primeras cifras indican el grupo "
				"padre (400 Proveedores, 410 Acreedores), que debe existir en el árbol."
			),
		},
		{
			"fieldname": COMPANY_SUPPLIER_DIGITS_FIELDNAME,
			"label": "Dígitos de cuentas de proveedor",
			"fieldtype": "Int",
			"insert_after": COMPANY_SUPPLIER_PREFIX_FIELDNAME,
			"default": str(DEFAULT_ACCOUNT_DIGITS),
			"depends_on": f"eval:doc.{COMPANY_SUPPLIER_AUTO_FIELDNAME}",
			"mandatory_depends_on": f"eval:doc.{COMPANY_SUPPLIER_AUTO_FIELDNAME}",
			"description": "Longitud total del número de cuenta (prefijo incluido).",
		},
	],
}


def create_app_custom_fields(update: bool = True) -> None:
	create_custom_fields(CUSTOM_FIELDS, ignore_validate=frappe.flags.in_patch, update=update)


def delete_legacy_fields() -> None:
	delete_custom_fields(LEGACY_FIELDS)


def delete_app_custom_fields() -> None:
	delete_custom_fields({dt: [f["fieldname"] for f in fields] for dt, fields in CUSTOM_FIELDS.items()})
	delete_legacy_fields()
