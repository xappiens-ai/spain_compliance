# Copyright (c) 2026, Xappiens and contributors
# License: MIT

"""Numeración oficial de facturas de venta al validar (submit).

En ERPNext el ``name`` se asigna al insertar el borrador. Para facturación
española eso es el anti-patrón: el número legal quedaría reservado antes de
emitir la factura y la correlatividad fallaría (o se saltaría) al validar.

Flujo Spain Compliance:

1. Al **guardar** un borrador nuevo se nombra con una serie provisional
   (``SCBOR-…``). El campo ``naming_series`` sigue siendo la serie oficial
   elegida / de rectificativas.
2. Al **validar** (submit), en ``before_validate`` (antes de ``validate``), se
   renombra al siguiente número de la serie oficial y entonces se aplica la
   correlatividad.

Las enmiendas (``amended_from``) conservan el esquema ``original-1`` de ERPNext.
Los borradores que ya tienen nombre oficial (históricos) no se renombran; solo
se comprueba correlatividad.
"""

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.naming import make_autoname
from frappe.model.rename_doc import rename_doc

# Provisional draft series. Not shown as a user option; swapped in before_naming.
PROVISIONAL_SERIES = "SCBOR-.YY.-"
PROVISIONAL_NAME_PREFIX = "SCBOR"


def is_provisional_series(series: str | None) -> bool:
	return (series or "").strip().startswith("SCBOR")


def is_provisional_name(name: str | None) -> bool:
	return bool(name) and name.startswith(PROVISIONAL_NAME_PREFIX)


def use_provisional_name_on_insert(doc) -> None:
	"""Swap naming_series to provisional for new drafts (not amendments).

	Call from ``before_naming``. Restores the intended official series via
	``restore_intended_naming_series`` on the first ``before_validate``.
	"""
	if frappe.flags.in_install or frappe.flags.in_migrate or frappe.flags.in_patch:
		return
	if doc.amended_from:
		return
	if doc.flags.get("spain_compliance_assigning_official_name"):
		return
	if not doc.is_new():
		return

	intended = (doc.get("naming_series") or "").strip()
	if not intended or is_provisional_series(intended):
		return

	doc.flags.spain_compliance_intended_series = intended
	doc.naming_series = PROVISIONAL_SERIES


def restore_intended_naming_series(doc) -> None:
	"""Put the official series back on the document after provisional naming."""
	intended = doc.flags.get("spain_compliance_intended_series")
	if not intended:
		return
	doc.naming_series = intended
	doc.flags.pop("spain_compliance_intended_series", None)


def assign_official_name_on_submit(doc) -> None:
	"""Rename provisional draft → next official series number when submitting.

	Must run in ``before_validate`` on submit (Frappe runs ``validate`` before
	``before_submit``, so the official name has to exist before correlativity).
	"""
	if frappe.flags.in_install or frappe.flags.in_migrate or frappe.flags.in_patch:
		return
	if getattr(doc, "_action", None) != "submit":
		return
	if not is_provisional_name(doc.name):
		return

	from spain_compliance.overrides.sales_invoice import ensure_company_abbr, apply_return_naming_series

	restore_intended_naming_series(doc)
	ensure_company_abbr(doc)
	apply_return_naming_series(doc)

	official = (doc.get("naming_series") or "").strip()
	if not official or is_provisional_series(official):
		frappe.throw(
			_("No se puede validar la factura: falta la serie oficial de numeración."),
			title=_("Numeración de facturas"),
		)

	doc.flags.spain_compliance_assigning_official_name = True
	# Same path as frappe.model.naming.set_name_by_naming_series
	new_name = make_autoname(official + ".#####", "", doc)
	old_name = doc.name

	rename_doc(
		doctype=doc.doctype,
		old=old_name,
		new=new_name,
		force=True,
		ignore_permissions=True,
		show_alert=False,
		rebuild_search=False,
		validate=False,
	)
	doc.name = new_name
	# Desk savedocs → send_updated_docs copies this so the client renames locals.
	doc.localname = old_name
	# Parent rows / children already renamed in DB; keep in-memory links coherent.
	for child in doc.get_all_children():
		if child.parent == old_name:
			child.parent = new_name
	_sync_timestamp_after_rename(doc)


def sync_modified_from_db(doc) -> None:
	"""Keep in-memory ``modified`` aligned after rename / chained hooks."""
	modified = frappe.db.get_value(doc.doctype, doc.name, "modified")
	if modified:
		doc.modified = modified


def _sync_timestamp_after_rename(doc) -> None:
	sync_modified_from_db(doc)
	before = getattr(doc, "_doc_before_save", None)
	if before:
		before.name = doc.name
		before.modified = doc.modified


def on_submit_sync_modified(doc, method=None):
	"""After on_submit side-effects, align timestamp for chained cancel/API calls."""
	sync_modified_from_db(doc)
