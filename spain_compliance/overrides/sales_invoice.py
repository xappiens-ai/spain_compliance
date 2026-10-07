# Copyright (c) 2026, Xappiens and contributors
# License: MIT

"""Sales Invoice extensions.

1. Collection statuses ``Dudoso Cobro`` / ``Pérdida`` on the native ``status``
   field (options are added by a Property Setter on install), preserved across
   ERPNext's automatic status recalculation while the invoice is outstanding.
2. Dedicated naming series for credit notes (facturas rectificativas): Spanish
   invoicing rules require a separate series for rectifying invoices. When a
   Company defines ``serie_rectificativas``, returns created from the ordinary
   series are moved to it before naming.
3. Correlatividad de serie y fecha (RD 1619/2012): no fechas futuras al guardar
   (el número se reserva entonces) y orden cronológico dentro de la serie.
"""

from __future__ import annotations

import frappe
from erpnext.accounts.doctype.sales_invoice.sales_invoice import (
	SalesInvoice as ERPNextSalesInvoice,
)
from frappe import _
from frappe.utils import flt

from spain_compliance.contabilidad.correlatividad import validate_sales_invoice_correlatividad
from spain_compliance.setup.custom_fields import COMPANY_RETURN_SERIES_FIELDNAME

LOSS_STATUSES = frozenset({"Dudoso Cobro", "Pérdida"})

# Statuses that must never be replaced by a preserved loss status.
FINAL_STATUSES = frozenset({"Cancelled", "Paid", "Credit Note Issued", "Return", "Internal Transfer"})


def get_return_naming_series(company: str | None) -> str | None:
	"""Naming series configured for credit notes of ``company`` (or None)."""
	if not company:
		return None
	try:
		series = frappe.get_cached_value("Company", company, COMPANY_RETURN_SERIES_FIELDNAME)
	except Exception:
		return None
	return (series or "").strip() or None


def get_default_naming_series() -> str | None:
	"""Default ordinary Sales Invoice series (Property Setter default or first option)."""
	df = frappe.get_meta("Sales Invoice").get_field("naming_series")
	if not df:
		return None
	if df.default:
		return df.default
	options = [o for o in (df.options or "").split("\n") if o]
	return options[0] if options else None


class SalesInvoice(ERPNextSalesInvoice):
	def before_naming(self):
		# ERPNext's SalesInvoice defines no before_naming; frappe.model.naming calls this hook.
		self._ensure_company_abbr()
		self._apply_return_naming_series()

	def validate(self):
		super().validate()
		validate_sales_invoice_correlatividad(self)

	# Naming series for credit notes ----------------------------------------

	def _ensure_company_abbr(self):
		"""Put the company abbreviation where naming series can read it.

		``{company_abbr}`` in a series is resolved with ``doc.get()``, which only
		sees values stored on the document. ERPNext already has ``company_abbr``
		as a property on the accounts controller, so this must not be a Custom
		Field: Frappe rejects that name. Setting it here is enough for naming
		and is not persisted.
		"""
		if not self.company or self.get("company_abbr"):
			return
		abbr = frappe.get_cached_value("Company", self.company, "abbr")
		if abbr:
			self.set("company_abbr", abbr)

	def _apply_return_naming_series(self):
		if not self.is_return:
			return
		target = get_return_naming_series(self.company)
		if not target:
			return

		current = (self.naming_series or "").strip()
		if current == target:
			return

		# Only override series that were clearly not chosen for a credit note:
		# empty, copied from the invoice being rectified, or the ordinary default.
		copied_from_original = None
		if self.return_against:
			copied_from_original = frappe.db.get_value("Sales Invoice", self.return_against, "naming_series")

		if not current or current == copied_from_original or current == get_default_naming_series():
			self.naming_series = target

	# Collection status -------------------------------------------------------

	def set_status(self, update=False, status=None, update_modified=True):
		if status in LOSS_STATUSES:
			self.status = status
			if update:
				self.db_set("status", self.status, update_modified=update_modified)
			return

		preserve = self.get("status") if self.get("status") in LOSS_STATUSES else None

		super().set_status(update=False, status=None, update_modified=update_modified)

		if (
			preserve
			and self.docstatus == 1
			and flt(self.outstanding_amount) > 0.01
			and self.status not in FINAL_STATUSES
		):
			self.status = preserve

		if update:
			self.db_set("status", self.status, update_modified=update_modified)


@frappe.whitelist()
def set_cobro_status(name: str, status: str | None = None):
	"""Set or clear ``Dudoso Cobro`` / ``Pérdida`` on a submitted Sales Invoice.

	Pass an empty status (or ``clear``) to restore the regular ERPNext status
	computed from outstanding amount and due date.
	"""
	si = frappe.get_doc("Sales Invoice", name)
	si.check_permission("write")

	if si.docstatus != 1:
		frappe.throw(_("Only submitted Sales Invoices can use this status"))

	if si.is_return:
		frappe.throw(_("Return invoices cannot be marked as Dudoso Cobro / Pérdida"))

	status = (status or "").strip()
	if status in ("", "clear"):
		si.status = "Unpaid"
		si.set_status(update=True)
		return {"name": si.name, "status": si.status}

	if status not in LOSS_STATUSES:
		frappe.throw(_("Invalid status: {0}").format(status))

	if flt(si.outstanding_amount) <= 0.01:
		frappe.throw(_("Invoice has no outstanding amount"))

	si.set_status(update=True, status=status)
	return {"name": si.name, "status": si.status}
