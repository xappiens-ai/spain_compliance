# Copyright (c) 2026, Xappiens and contributors
# For license information, please see license.txt

from __future__ import annotations

from datetime import date, timedelta

import frappe
from frappe import _
from frappe.utils import add_months, get_first_day, getdate, today

from spain_compliance.api.permission import has_app_permission

PERIODS = {
	"this_month": _("Este mes"),
	"this_quarter": _("Este trimestre"),
	"this_year": _("Este año"),
}


def _period_start(period: str) -> date:
	today_date = getdate(today())
	if period == "this_month":
		return getdate(get_first_day(today_date))
	if period == "this_quarter":
		quarter = (today_date.month - 1) // 3
		return date(today_date.year, quarter * 3 + 1, 1)
	return date(today_date.year, 1, 1)


def _default_company() -> str | None:
	return frappe.defaults.get_user_default("Company") or frappe.db.get_single_value(
		"Global Defaults", "default_company"
	)


def _currency(company: str | None) -> str:
	if company:
		return frappe.get_cached_value("Company", company, "default_currency") or "EUR"
	return "EUR"


def _empty_invoice_totals() -> dict:
	return {
		"billed": 0.0,
		"paid": 0.0,
		"outstanding": 0.0,
		"count": 0,
		"period_count": 0,
	}


def _invoice_totals(doctype: str, company: str | None, start: date, end: date) -> dict:
	conditions = ["docstatus = 1", "posting_date between %(start)s and %(end)s"]
	params: dict = {"start": start, "end": end}
	if company:
		conditions.append("company = %(company)s")
		params["company"] = company

	where = " and ".join(conditions)
	row = frappe.db.sql(
		f"""
		select
			coalesce(sum(grand_total), 0) as billed,
			coalesce(sum(outstanding_amount), 0) as outstanding_in_period,
			count(*) as count
		from `tab{doctype}`
		where {where}
		""",
		params,
		as_dict=True,
	)[0]

	open_conditions = ["docstatus = 1", "outstanding_amount > 0"]
	open_params: dict = {}
	if company:
		open_conditions.append("company = %(company)s")
		open_params["company"] = company

	open_where = " and ".join(open_conditions)
	open_row = frappe.db.sql(
		f"""
		select
			coalesce(sum(outstanding_amount), 0) as outstanding,
			count(*) as count
		from `tab{doctype}`
		where {open_where}
		""",
		open_params,
		as_dict=True,
	)[0]

	billed = float(row.billed or 0)
	outstanding_open = float(open_row.outstanding or 0)
	paid = max(billed - float(row.outstanding_in_period or 0), 0)

	return {
		"billed": billed,
		"paid": paid,
		"outstanding": outstanding_open,
		"count": int(open_row.count or 0),
		"period_count": int(row.count or 0),
	}


def _journal_stats(company: str | None, start: date, end: date) -> dict:
	filters = {"docstatus": ["<", 2], "posting_date": ["between", [start, end]]}
	if company:
		filters["company"] = company

	total = frappe.db.count("Journal Entry", filters)
	draft_filters = {**filters, "docstatus": 0}
	draft = frappe.db.count("Journal Entry", draft_filters)
	return {"count": int(total or 0), "draft": int(draft or 0)}


def _recent_invoices(doctype: str, company: str | None, party_field: str, limit: int = 5):
	fields = [
		"name",
		party_field,
		"posting_date",
		"grand_total",
		"outstanding_amount",
		"status",
	]
	filters = {"docstatus": ["<", 2]}
	if company:
		filters["company"] = company

	return frappe.get_list(
		doctype,
		filters=filters,
		fields=fields,
		order_by="posting_date desc, modified desc",
		limit_page_length=limit,
		ignore_permissions=False,
	)


def _month_buckets(start: date, end: date) -> list[date]:
	cursor = date(start.year, start.month, 1)
	last = date(end.year, end.month, 1)
	buckets: list[date] = []
	while cursor <= last:
		buckets.append(cursor)
		cursor = add_months(cursor, 1)
	return buckets


def _day_buckets(start: date, end: date) -> list[date]:
	buckets: list[date] = []
	cursor = start
	while cursor <= end:
		buckets.append(cursor)
		cursor += timedelta(days=1)
	return buckets


def _aggregate_doctype(
	doctype: str,
	amount_field: str,
	company: str | None,
	start: date,
	end: date,
	grain: str,
	extra_conditions: str = "",
	extra_params: dict | None = None,
) -> dict[str, float]:
	if grain == "day":
		select_key = "date(posting_date)"
		key_fmt = "%Y-%m-%d"
	else:
		select_key = "date_format(posting_date, '%%Y-%%m-01')"
		key_fmt = "%Y-%m-%d"

	conditions = [
		"docstatus = 1",
		"posting_date between %(start)s and %(end)s",
	]
	params: dict = {"start": start, "end": end}
	if company:
		conditions.append("company = %(company)s")
		params["company"] = company
	if extra_conditions:
		conditions.append(extra_conditions)
	if extra_params:
		params.update(extra_params)

	where = " and ".join(conditions)
	rows = frappe.db.sql(
		f"""
		select {select_key} as bucket, coalesce(sum({amount_field}), 0) as amount
		from `tab{doctype}`
		where {where}
		group by bucket
		order by bucket
		""",
		params,
		as_dict=True,
	)
	out: dict[str, float] = {}
	for row in rows:
		key = getdate(row.bucket).strftime(key_fmt)
		out[key] = float(row.amount or 0)
	return out


def _cashflow_series(company: str | None, start: date, end: date, period: str) -> list[dict]:
	"""Books-like cashflow: Payment Entry Receive/Pay, else Sales/Purchase billed."""
	grain = "day" if period == "this_month" else "month"
	buckets = _day_buckets(start, end) if grain == "day" else _month_buckets(start, end)

	can_pe = frappe.has_permission("Payment Entry", "read")
	can_si = frappe.has_permission("Sales Invoice", "read")
	can_pi = frappe.has_permission("Purchase Invoice", "read")

	inflow_map: dict[str, float] = {}
	outflow_map: dict[str, float] = {}

	if can_pe:
		inflow_map = _aggregate_doctype(
			"Payment Entry",
			"paid_amount",
			company,
			start,
			end,
			grain,
			extra_conditions="payment_type = 'Receive'",
		)
		outflow_map = _aggregate_doctype(
			"Payment Entry",
			"paid_amount",
			company,
			start,
			end,
			grain,
			extra_conditions="payment_type = 'Pay'",
		)

	if can_si and (not inflow_map or sum(inflow_map.values()) == 0):
		inflow_map = _aggregate_doctype("Sales Invoice", "grand_total", company, start, end, grain)
	if can_pi and (not outflow_map or sum(outflow_map.values()) == 0):
		outflow_map = _aggregate_doctype("Purchase Invoice", "grand_total", company, start, end, grain)

	return [
		{
			"date": bucket.strftime("%Y-%m-%d"),
			"entradas": inflow_map.get(bucket.strftime("%Y-%m-%d"), 0.0),
			"salidas": outflow_map.get(bucket.strftime("%Y-%m-%d"), 0.0),
		}
		for bucket in buckets
	]


def _billing_series(company: str | None, start: date, end: date, period: str) -> list[dict]:
	grain = "day" if period == "this_month" else "month"
	buckets = _day_buckets(start, end) if grain == "day" else _month_buckets(start, end)

	sales = (
		_aggregate_doctype("Sales Invoice", "grand_total", company, start, end, grain)
		if frappe.has_permission("Sales Invoice", "read")
		else {}
	)
	purchases = (
		_aggregate_doctype("Purchase Invoice", "grand_total", company, start, end, grain)
		if frappe.has_permission("Purchase Invoice", "read")
		else {}
	)

	return [
		{
			"date": bucket.strftime("%Y-%m-%d"),
			"ventas": sales.get(bucket.strftime("%Y-%m-%d"), 0.0),
			"compras": purchases.get(bucket.strftime("%Y-%m-%d"), 0.0),
		}
		for bucket in buckets
	]


def _receivable_mix(receivable: dict) -> list[dict]:
	paid = float(receivable.get("paid") or 0)
	outstanding = float(receivable.get("outstanding") or 0)
	rows = []
	if paid > 0:
		rows.append({"label": _("Cobrado"), "value": paid})
	if outstanding > 0:
		rows.append({"label": _("Pendiente"), "value": outstanding})
	if not rows:
		rows.append({"label": _("Sin datos"), "value": 0})
	return rows


@frappe.whitelist()
def get_tablero(period: str = "this_year") -> dict:
	"""Accounting board metrics for Contabilidad SPA (Books-like dashboard)."""
	if frappe.session.user == "Guest" or not has_app_permission():
		frappe.throw(_("No permission"), frappe.PermissionError)

	if period not in PERIODS:
		period = "this_year"

	start = _period_start(period)
	end = getdate(today())
	company = _default_company()

	receivable = (
		_invoice_totals("Sales Invoice", company, start, end)
		if frappe.has_permission("Sales Invoice", "read")
		else _empty_invoice_totals()
	)
	payable = (
		_invoice_totals("Purchase Invoice", company, start, end)
		if frappe.has_permission("Purchase Invoice", "read")
		else _empty_invoice_totals()
	)

	journal = (
		_journal_stats(company, start, end)
		if frappe.has_permission("Journal Entry", "read")
		else {"count": 0, "draft": 0}
	)

	return {
		"period": period,
		"period_label": PERIODS[period],
		"from_date": str(start),
		"to_date": str(end),
		"company": company,
		"currency": _currency(company),
		"chart_grain": "day" if period == "this_month" else "month",
		"receivable": receivable,
		"payable": payable,
		"journal_entries": journal,
		"cashflow": _cashflow_series(company, start, end, period),
		"billing": _billing_series(company, start, end, period),
		"receivable_mix": _receivable_mix(receivable),
		"recent_sales": (
			_recent_invoices("Sales Invoice", company, "customer_name")
			if frappe.has_permission("Sales Invoice", "read")
			else []
		),
		"recent_purchases": (
			_recent_invoices("Purchase Invoice", company, "supplier_name")
			if frappe.has_permission("Purchase Invoice", "read")
			else []
		),
	}
