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
	],
}


def create_app_custom_fields(update: bool = True) -> None:
	create_custom_fields(CUSTOM_FIELDS, ignore_validate=frappe.flags.in_patch, update=update)


def delete_legacy_fields() -> None:
	delete_custom_fields(LEGACY_FIELDS)


def delete_app_custom_fields() -> None:
	delete_custom_fields({dt: [f["fieldname"] for f in fields] for dt, fields in CUSTOM_FIELDS.items()})
	delete_legacy_fields()
