# Copyright (c) 2026, Xappiens and contributors
# License: MIT

"""Custom Fields owned by Spain Compliance.

All fields are created on install / migrate and removed on uninstall.
Field names intentionally have no ``custom_`` prefix (that prefix is reserved
for fields created through Customize Form on a site).
"""

from __future__ import annotations

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

try:
	# Frappe ≤15
	from frappe.custom.doctype.custom_field.custom_field import delete_custom_fields
except ImportError:
	# Frappe 16+: helper removed; delete by DocType + fieldname.
	def delete_custom_fields(custom_fields: dict[str, list[str]]) -> None:
		for doctype, fieldnames in (custom_fields or {}).items():
			for fieldname in fieldnames:
				name = frappe.db.get_value(
					"Custom Field", {"dt": doctype, "fieldname": fieldname}, "name"
				)
				if name:
					frappe.delete_doc("Custom Field", name, force=True, ignore_permissions=True)

from spain_compliance.contabilidad.clasificacion import (
	CLAVE_IVA_OPTIONS,
	CLAVE_RETENCION_OPTIONS,
	DEDUCIBLE_OPTIONS,
	MODELO_CUENTAS_OPTIONS,
	PERIODICIDAD_303_OPTIONS,
	REGIMEN_IVA_OPTIONS,
	TIPO_IDENTIFICACION_OPTIONS,
	TIPO_IMPUESTO_OPTIONS,
)

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

COMPANY_PRORRATA_FIELDNAME = "prorrata_general"
COMPANY_EXIGIR_CLASIFICACION_FIELDNAME = "exigir_clasificacion_fiscal"

# Copiados de la plantilla a la fila de la factura cuando esta va vacía.
TAX_CLASSIFICATION_FIELDS = ("tipo_impuesto", "clave_iva", "deducible_iva", "clave_retencion")

DEFAULT_RETURN_SERIES = "{company_abbr}.R.YY.{#####}"

# Created by an early draft of this app. ERPNext already exposes
# ``company_abbr`` as a property on AccountsController, so a Custom Field
# with that name is rejected on a clean install.
LEGACY_FIELDS: dict[str, list[str]] = {
	"Sales Invoice": ["company_abbr"],
}


def _clasificacion_impuesto(insert_after: str) -> list[dict]:
	return [
		{
			"fieldname": "clasificacion_fiscal_section",
			"label": "Clasificación fiscal (España)",
			"fieldtype": "Section Break",
			"insert_after": insert_after,
			"collapsible": 1,
		},
		{
			"fieldname": "tipo_impuesto",
			"label": "Tipo de impuesto",
			"fieldtype": "Select",
			"options": TIPO_IMPUESTO_OPTIONS,
			"insert_after": "clasificacion_fiscal_section",
			"in_list_view": 1,
			"description": "IVA, recargo de equivalencia o retención. Vacío = pendiente de clasificar.",
		},
		{
			"fieldname": "clave_iva",
			"label": "Clave de IVA",
			"fieldtype": "Select",
			"options": CLAVE_IVA_OPTIONS,
			"insert_after": "tipo_impuesto",
			"in_list_view": 1,
			"description": "Calificación de la operación para el libro registro y el modelo 303.",
		},
		{
			"fieldname": "deducible_iva",
			"label": "Deducibilidad",
			"fieldtype": "Select",
			"options": DEDUCIBLE_OPTIONS,
			"insert_after": "clave_iva",
			"description": (
				"Solo compras. Corriente y bien de inversión aplican la prorrata de la compañía. "
				"No deducible deja la cuota deducible a cero."
			),
		},
		{
			"fieldname": "clave_retencion",
			"label": "Clave de retención",
			"fieldtype": "Select",
			"options": CLAVE_RETENCION_OPTIONS,
			"insert_after": "deducible_iva",
			"description": "Clave del perceptor para los modelos 111, 115, 190 y 180.",
		},
	]


def _identificacion_tercero() -> list[dict]:
	return [
		{
			"fieldname": "tipo_identificacion_fiscal",
			"label": "Tipo de identificación fiscal",
			"fieldtype": "Select",
			"options": TIPO_IDENTIFICACION_OPTIONS,
			"insert_after": "tax_id",
			"description": (
				"NIF, NIE o CIF españoles y NIF-IVA se comprueban al guardar. Si no cuadra, se avisa "
				"y el tercero se guarda igual."
			),
		},
	]


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
		{
			"fieldname": "fiscalidad_section",
			"label": "Fiscalidad",
			"fieldtype": "Section Break",
			"insert_after": COMPANY_SUPPLIER_DIGITS_FIELDNAME,
			"collapsible": 1,
		},
		{
			"fieldname": "regimen_iva",
			"label": "Régimen de IVA",
			"fieldtype": "Select",
			"options": REGIMEN_IVA_OPTIONS,
			"insert_after": "fiscalidad_section",
			"default": "General",
			"description": "Se usará en el modelo 303. El registro de IVA ya distingue las claves de cada factura.",
		},
		{
			"fieldname": "periodicidad_modelo_303",
			"label": "Periodicidad del modelo 303",
			"fieldtype": "Select",
			"options": PERIODICIDAD_303_OPTIONS,
			"insert_after": "regimen_iva",
			"default": "Trimestral",
		},
		{
			"fieldname": "modelo_cuentas_anuales",
			"label": "Modelo de cuentas anuales",
			"fieldtype": "Select",
			"options": MODELO_CUENTAS_OPTIONS,
			"insert_after": "periodicidad_modelo_303",
			"default": "PYMES",
		},
		{
			"fieldname": "epigrafe_iae",
			"label": "Epígrafe IAE",
			"fieldtype": "Data",
			"insert_after": "modelo_cuentas_anuales",
			"description": "Código de actividad para los libros registro de IVA.",
		},
		{
			"fieldname": "fiscalidad_column",
			"fieldtype": "Column Break",
			"insert_after": "epigrafe_iae",
		},
		{
			"fieldname": COMPANY_PRORRATA_FIELDNAME,
			"label": "Prorrata general (%)",
			"fieldtype": "Percent",
			"insert_after": "fiscalidad_column",
			"default": "100",
			"description": (
				"Porcentaje de IVA soportado que se considera deducible al generar el registro, "
				"tanto en operaciones corrientes como en bienes de inversión. 100 es deducción completa."
			),
		},
		{
			"fieldname": "prorrata_especial",
			"label": "Prorrata especial",
			"fieldtype": "Check",
			"insert_after": COMPANY_PRORRATA_FIELDNAME,
			"default": "0",
			"description": (
				"La prorrata especial se calcula por operación. Hasta que cada factura lo indique, "
				"el registro aplica la prorrata general."
			),
		},
		{
			"fieldname": COMPANY_EXIGIR_CLASIFICACION_FIELDNAME,
			"label": "Exigir clasificación fiscal",
			"fieldtype": "Check",
			"insert_after": "prorrata_especial",
			"default": "0",
			"description": (
				"Impide validar la factura (el borrador se puede guardar) si hay impuestos sin tipo, "
				"clave o, en compras, deducibilidad. Desactivado: se valida y el registro queda "
				"pendiente de clasificar."
			),
		},
		{
			"fieldname": "contacto_aeat",
			"label": "Persona de contacto AEAT",
			"fieldtype": "Data",
			"insert_after": COMPANY_EXIGIR_CLASIFICACION_FIELDNAME,
		},
		{
			"fieldname": "telefono_aeat",
			"label": "Teléfono de contacto AEAT",
			"fieldtype": "Data",
			"insert_after": "contacto_aeat",
		},
	],
	"Sales Taxes and Charges": _clasificacion_impuesto("base_net_amount"),
	"Purchase Taxes and Charges": _clasificacion_impuesto("base_net_amount"),
	"Item Tax Template": [
		{
			"fieldname": "clave_iva",
			"label": "Clave de IVA",
			"fieldtype": "Select",
			"options": CLAVE_IVA_OPTIONS,
			"insert_after": "disabled",
			"description": (
				"Si se informa, sustituye a la clave de la fila de impuesto en los artículos que usen "
				"esta plantilla. Sirve para mezclar en una factura operaciones con distinta clave "
				"(por ejemplo, sujeta y exenta)."
			),
		},
	],
	"Customer": _identificacion_tercero(),
	"Supplier": _identificacion_tercero(),
}


def create_app_custom_fields(update: bool = True) -> None:
	create_custom_fields(CUSTOM_FIELDS, ignore_validate=frappe.flags.in_patch, update=update)


def delete_legacy_fields() -> None:
	delete_custom_fields(LEGACY_FIELDS)


def delete_app_custom_fields() -> None:
	delete_custom_fields({dt: [f["fieldname"] for f in fields] for dt, fields in CUSTOM_FIELDS.items()})
	delete_legacy_fields()
