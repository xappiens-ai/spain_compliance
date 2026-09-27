# Copyright (c) 2026, Xappiens and contributors
# License: MIT

"""Scheduled tasks."""

from __future__ import annotations

import frappe
from frappe.utils import add_months, cint, flt, getdate, today

from spain_compliance.overrides.sales_invoice import LOSS_STATUSES
from spain_compliance.setup.custom_fields import COMPANY_DUDOSO_MONTHS_FIELDNAME


def auto_mark_dudoso_cobro() -> dict:
	"""Mark overdue Sales Invoices as ``Dudoso Cobro``.

	Runs daily. For every Company with ``meses_dudoso_cobro`` > 0, submitted
	non-return invoices with outstanding amount whose due date is older than
	that many months are moved to ``Dudoso Cobro``. Invoices already in
	``Dudoso Cobro`` / ``Pérdida`` are left untouched.
	"""
	if not frappe.db.has_column("Company", COMPANY_DUDOSO_MONTHS_FIELDNAME):
		return {"marked": 0}

	companies = frappe.get_all(
		"Company",
		filters={COMPANY_DUDOSO_MONTHS_FIELDNAME: [">", 0]},
		fields=["name", COMPANY_DUDOSO_MONTHS_FIELDNAME],
	)
	if not companies:
		return {"marked": 0}

	marked: list[str] = []
	for company in companies:
		cutoff = getdate(add_months(today(), -cint(company.get(COMPANY_DUDOSO_MONTHS_FIELDNAME))))
		names = frappe.get_all(
			"Sales Invoice",
			filters={
				"company": company.name,
				"docstatus": 1,
				"is_return": 0,
				"outstanding_amount": [">", 0.01],
				"due_date": ["<=", cutoff],
				"status": ["not in", [*LOSS_STATUSES, "Cancelled", "Paid"]],
			},
			pluck="name",
		)
		for name in names:
			si = frappe.get_doc("Sales Invoice", name)
			if flt(si.outstanding_amount) <= 0.01 or si.status in LOSS_STATUSES:
				continue
			si.set_status(update=True, status="Dudoso Cobro")
			marked.append(name)

	if marked:
		frappe.logger("spain_compliance").info(
			"auto_mark_dudoso_cobro: %s invoices → Dudoso Cobro", len(marked)
		)

	return {"marked": len(marked), "names": marked}
