# Copyright (c) 2026, Xappiens and contributors
# License: MIT

"""Install / migrate / uninstall hooks for Spain Compliance."""

from __future__ import annotations

import frappe
from frappe.custom.doctype.property_setter.property_setter import make_property_setter

from spain_compliance.overrides.sales_invoice import LOSS_STATUSES
from spain_compliance.setup.custom_fields import (
	create_app_custom_fields,
	delete_app_custom_fields,
	delete_legacy_fields,
)

STATUS_PROPERTY_SETTER = "Sales Invoice-status-options-spain_compliance"


def after_install():
	delete_legacy_fields()
	create_app_custom_fields()
	setup_sales_invoice_status()


def after_migrate():
	delete_legacy_fields()
	create_app_custom_fields()
	setup_sales_invoice_status()


def before_uninstall():
	remove_sales_invoice_status()
	delete_app_custom_fields()


# Sales Invoice.status -----------------------------------------------------
#
# ``Dudoso Cobro`` and ``Pérdida`` are added to the *native* ``status`` Select
# through a Property Setter (no extra column) so list views, filters and
# reports keep working with a single status field.


def setup_sales_invoice_status():
	_ensure_status_options()
	frappe.clear_cache(doctype="Sales Invoice")


def remove_sales_invoice_status():
	for name in frappe.get_all(
		"Property Setter",
		filters={"doc_type": "Sales Invoice", "field_name": "status", "property": "options"},
		pluck="name",
	):
		if name == STATUS_PROPERTY_SETTER:
			frappe.delete_doc("Property Setter", name, force=True)
			continue
		# Another app also customised the options: only drop ours.
		value = frappe.db.get_value("Property Setter", name, "value") or ""
		options = [o for o in value.split("\n") if o not in LOSS_STATUSES]
		frappe.db.set_value("Property Setter", name, "value", "\n".join(options))
	frappe.clear_cache(doctype="Sales Invoice")


def _native_status_options() -> list[str]:
	"""Current Select options (standard + other apps' Property Setters)."""
	df = frappe.get_meta("Sales Invoice").get_field("status")
	return (df.options or "").split("\n") if df else []


def _ensure_status_options():
	existing = frappe.db.get_value(
		"Property Setter",
		{"doc_type": "Sales Invoice", "field_name": "status", "property": "options"},
		["name", "value"],
		as_dict=True,
	)

	if existing:
		options = (existing.value or "").split("\n")
		missing = [s for s in sorted(LOSS_STATUSES) if s not in options]
		if missing:
			frappe.db.set_value("Property Setter", existing.name, "value", "\n".join([*options, *missing]))
		return

	options = _native_status_options()
	options += [s for s in sorted(LOSS_STATUSES) if s not in options]
	make_property_setter(
		"Sales Invoice",
		"status",
		"options",
		"\n".join(options),
		"Text",
		validate_fields_for_doctype=False,
	)
	name = frappe.db.get_value(
		"Property Setter",
		{"doc_type": "Sales Invoice", "field_name": "status", "property": "options"},
	)
	if name and name != STATUS_PROPERTY_SETTER:
		frappe.rename_doc("Property Setter", name, STATUS_PROPERTY_SETTER, force=True)
