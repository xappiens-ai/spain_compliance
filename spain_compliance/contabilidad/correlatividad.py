# Copyright (c) 2026, Xappiens and contributors
# License: MIT

"""Correlatividad de facturas de venta (serie + fecha).

Reglamento de facturación (RD 1619/2012, art. 6): dentro de cada serie la
numeración debe ser correlativa. En la práctica española eso implica además
orden cronológico: un número mayor no puede llevar fecha de expedición anterior
a un número menor de la misma serie.

El ``name`` se asigna como en ERPNext (serie oficial al insertar el borrador).
La correlatividad se comprueba al guardar y al validar, sobre ese nombre.

La identidad de serie se deduce del **nombre** del documento (prefijo del
contador en ``tabSeries``), no del texto de ``naming_series``. Dos plantillas
distintas que resuelven al mismo contador son la misma serie legal.
``before_validate`` se ejecuta aunque el llamador pase ``ignore_validate``.
"""

from __future__ import annotations

import re

import frappe
from frappe import _
from frappe.utils import getdate, today

_HASH_RUN = re.compile(r"#+")
_AMEND_SUFFIX = re.compile(r"^(.+)-(\d+)$")


def validate_sales_invoice_correlatividad(doc, method=None):
	"""Hook / método de validate para Sales Invoice."""
	if frappe.flags.in_install or frappe.flags.in_migrate or frappe.flags.in_patch:
		return
	if not doc.get("name") or doc.name.startswith("new-"):
		return
	if not doc.get("posting_date"):
		return
	if not doc.company:
		return

	_validate_posting_date_not_future(doc)
	_validate_series_chronology(doc)


def get_counter_digits(naming_series: str | None) -> int:
	"""Width of the numeric counter in the naming series (default 5)."""
	matches = _HASH_RUN.findall(naming_series or "")
	if matches:
		return len(matches[-1])
	return 5


def series_prefix_from_name(name: str | None, digits: int) -> str | None:
	"""Return the Series counter prefix for an invoice name.

	``XAPF2600060`` + 5 → ``XAPF26``; amended ``XAPF2600016-1`` → ``XAPF26``.
	"""
	if not name or name.startswith("new-"):
		return None

	base = name
	amend = _AMEND_SUFFIX.fullmatch(name)
	if amend:
		candidate = amend.group(1)
		if len(candidate) >= digits and candidate[-digits:].isdigit():
			base = candidate

	if len(base) < digits or not base[-digits:].isdigit():
		return None
	return base[:-digits]


def _validate_posting_date_not_future(doc):
	"""No guardar ni emitir factura con fecha de expedición futura."""
	if getdate(doc.posting_date) <= getdate(today()):
		return

	frappe.throw(
		_(
			"No se puede guardar ni emitir la factura {0} con fecha {1}: la fecha de "
			"expedición no puede ser posterior a hoy ({2}). Una fecha futura dejaría "
			"la serie desordenada respecto a facturas del periodo intermedio."
		).format(frappe.bold(doc.name), frappe.bold(str(getdate(doc.posting_date))), frappe.bold(today())),
		title=_("Correlatividad de facturas"),
	)


def _validate_series_chronology(doc):
	"""Dentro de la misma compañía y serie (prefijo del nombre), name↑ ⇒ posting_date↑."""
	digits = get_counter_digits(doc.get("naming_series"))
	prefix = series_prefix_from_name(doc.name, digits)
	if not prefix:
		return

	posting = getdate(doc.posting_date)
	peers = _peers_in_series(doc.company, doc.name, prefix, digits)
	if not peers:
		return

	prev = None
	nxt = None
	for peer in peers:
		if peer.name < doc.name:
			if prev is None or peer.name > prev.name:
				prev = peer
		elif peer.name > doc.name:
			if nxt is None or peer.name < nxt.name:
				nxt = peer

	if prev and getdate(prev.posting_date) > posting:
		frappe.throw(
			_(
				"La factura {0} (fecha {1}) rompe la correlatividad de la serie: "
				"la factura anterior {2} tiene fecha posterior ({3}). Dentro de la "
				"misma serie, un número mayor no puede tener fecha de expedición "
				"anterior a un número menor."
			).format(
				frappe.bold(doc.name),
				frappe.bold(str(posting)),
				frappe.bold(prev.name),
				frappe.bold(str(getdate(prev.posting_date))),
			),
			title=_("Correlatividad de facturas"),
		)

	if nxt and getdate(nxt.posting_date) < posting:
		frappe.throw(
			_(
				"La factura {0} (fecha {1}) rompe la correlatividad de la serie: "
				"la factura posterior {2} tiene fecha anterior ({3}). Dentro de la "
				"misma serie, un número mayor no puede tener fecha de expedición "
				"anterior a un número menor."
			).format(
				frappe.bold(doc.name),
				frappe.bold(str(posting)),
				frappe.bold(nxt.name),
				frappe.bold(str(getdate(nxt.posting_date))),
			),
			title=_("Correlatividad de facturas"),
		)


def _peers_in_series(company: str, name: str, prefix: str, digits: int) -> list:
	"""Other Sales Invoices that share the same Series counter prefix."""
	rows = frappe.db.sql(
		"""
		SELECT name, posting_date
		FROM `tabSales Invoice`
		WHERE company = %s
			AND name LIKE %s
			AND name != %s
			AND posting_date IS NOT NULL
		""",
		(company, f"{prefix}%", name),
		as_dict=True,
	)
	return [row for row in rows if series_prefix_from_name(row.name, digits) == prefix]
