# Copyright (c) 2026, Xappiens and contributors
# License: MIT

"""Correlatividad de facturas de venta (serie + fecha).

Reglamento de facturación (RD 1619/2012, art. 6): dentro de cada serie la
numeración debe ser correlativa. En la práctica española eso implica además
orden cronológico: un número mayor no puede llevar fecha de expedición anterior
a un número menor de la misma serie.

ERPNext asigna el nombre (número) al guardar el borrador, no al validar. Por
eso la comprobación corre en cada ``validate`` una vez existe nombre: impedir
reservar un número con fecha futura o romper el orden frente a facturas ya
existentes (borrador, validadas o canceladas).
"""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import getdate, today


def validate_sales_invoice_correlatividad(doc, method=None):
	"""Hook / método de validate para Sales Invoice."""
	if frappe.flags.in_install or frappe.flags.in_migrate or frappe.flags.in_patch:
		return
	if not doc.get("name") or doc.name.startswith("new-"):
		return
	if not doc.get("posting_date"):
		return

	_validate_posting_date_not_future(doc)
	_validate_series_chronology(doc)


def _validate_posting_date_not_future(doc):
	"""No reservar número de factura con fecha de expedición futura."""
	if getdate(doc.posting_date) <= getdate(today()):
		return

	frappe.throw(
		_(
			"No se puede emitir ni guardar la factura {0} con fecha {1}: la fecha de "
			"expedición no puede ser posterior a hoy ({2}). El número de serie se "
			"asigna al guardar; reservar un borrador con fecha futura rompe la "
			"correlatividad cuando se emitan facturas intermedias. Para cuotas "
			"periódicas, emita la factura del periodo actual y configure Auto Repeat "
			"sobre esa factura (el ERP generará la siguiente cuando toque)."
		).format(frappe.bold(doc.name), frappe.bold(str(getdate(doc.posting_date))), frappe.bold(today())),
		title=_("Correlatividad de facturas"),
	)


def _validate_series_chronology(doc):
	"""Dentro de la misma compañía y naming_series, name↑ ⇒ posting_date↑."""
	naming_series = (doc.get("naming_series") or "").strip()
	if not naming_series or not doc.company:
		return

	posting = getdate(doc.posting_date)

	prev = frappe.db.sql(
		"""
		SELECT name, posting_date
		FROM `tabSales Invoice`
		WHERE company = %s
			AND naming_series = %s
			AND name < %s
			AND posting_date > %s
		ORDER BY name DESC
		LIMIT 1
		""",
		(doc.company, naming_series, doc.name, posting),
		as_dict=True,
	)
	if prev:
		frappe.throw(
			_(
				"La factura {0} (fecha {1}) rompe la correlatividad de la serie: "
				"la factura anterior {2} tiene fecha posterior ({3}). Dentro de la "
				"misma serie, un número mayor no puede tener fecha de expedición "
				"anterior a un número menor."
			).format(
				frappe.bold(doc.name),
				frappe.bold(str(posting)),
				frappe.bold(prev[0].name),
				frappe.bold(str(getdate(prev[0].posting_date))),
			),
			title=_("Correlatividad de facturas"),
		)

	nxt = frappe.db.sql(
		"""
		SELECT name, posting_date
		FROM `tabSales Invoice`
		WHERE company = %s
			AND naming_series = %s
			AND name > %s
			AND posting_date < %s
		ORDER BY name ASC
		LIMIT 1
		""",
		(doc.company, naming_series, doc.name, posting),
		as_dict=True,
	)
	if nxt:
		frappe.throw(
			_(
				"La factura {0} (fecha {1}) rompe la correlatividad de la serie: "
				"la factura posterior {2} tiene fecha anterior ({3}). Dentro de la "
				"misma serie, un número mayor no puede tener fecha de expedición "
				"anterior a un número menor."
			).format(
				frappe.bold(doc.name),
				frappe.bold(str(posting)),
				frappe.bold(nxt[0].name),
				frappe.bold(str(getdate(nxt[0].posting_date))),
			),
			title=_("Correlatividad de facturas"),
		)
