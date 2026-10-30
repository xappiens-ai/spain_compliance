# Copyright (c) 2026, Xappiens and contributors
# License: MIT

"""Runtime patches applied when the app loads.

1. Financial statements (Balance / P&L) for the PGC 9-group account tree.
2. On Frappe v15 only: Sales Invoice ``set_status`` and Account
   ``set_root_and_report_type`` (v16+ uses ``extend_doctype_class`` instead).

Financial statements assume every account of a ``root_type`` hangs under roots
with that same ``root_type``:

1. ``get_data`` walks roots of the root_type and loads GL only for accounts in
   those subtrees (lft/rgt). Under PGC, an asset account (430) may hang under
   group 4 (nominal liability) and would be skipped.
2. ``filter_accounts`` drops accounts whose parent is not in the root_type
   filter (mixed branches disappear from the report).

For PGC companies (``Company.pgc_espanol``):

- ``set_gl_entries_by_account``: one pass per root_type + company, without
  lft/rgt restriction (deduped with a sentinel key).
- ``get_accounts``: adds ancestor groups as skeleton so the hierarchy renders;
  totals still sum only accounts of the matching root_type.

Non-PGC companies keep native behaviour.
"""

from __future__ import annotations


def _frappe_supports_extend_doctype_class() -> bool:
	"""``extend_doctype_class`` exists in Frappe v16+ (``_get_extended_class``)."""
	try:
		from frappe.model import document as document_module
	except ImportError:
		return False
	return hasattr(document_module, "_get_extended_class")


def aplicar_informes_pgc():
	try:
		import frappe
		from erpnext.accounts.report import financial_statements as fs
	except ImportError:
		return

	if getattr(fs, "_spain_compliance_pgc", False):
		return
	fs._spain_compliance_pgc = True

	_get_accounts = fs.get_accounts
	_set_gl_entries_by_account = fs.set_gl_entries_by_account

	def _es_pgc(company):
		from spain_compliance.contabilidad.plan_contable import es_compania_pgc

		return es_compania_pgc(company)

	def get_accounts(company, root_type):
		cuentas = _get_accounts(company, root_type)
		if not cuentas or not _es_pgc(company):
			return cuentas

		presentes = {d.name for d in cuentas}
		faltan: set[str] = set()
		for d in cuentas:
			padre = d.parent_account
			while padre and padre not in presentes and padre not in faltan:
				faltan.add(padre)
				padre = frappe.db.get_value("Account", padre, "parent_account")

		if not faltan:
			return cuentas

		esqueleto = frappe.db.sql(
			"""
			select name, account_number, parent_account, lft, rgt, root_type, report_type,
				account_name, include_in_gross, account_type, is_group, lft, rgt
			from `tabAccount` where name in %(nombres)s
			""",
			{"nombres": tuple(faltan)},
			as_dict=True,
		)
		todas = list(cuentas) + esqueleto
		todas.sort(key=lambda d: d.lft)
		return todas

	def set_gl_entries_by_account(
		company,
		from_date,
		to_date,
		filters,
		gl_entries_by_account,
		root_lft=None,
		root_rgt=None,
		root_type=None,
		ignore_closing_entries=False,
		ignore_opening_entries=False,
		group_by_account=False,
	):
		if (
			root_type
			and root_lft
			and root_rgt
			and isinstance(gl_entries_by_account, dict)
			and _es_pgc(company)
		):
			# get_data calls once per root of the root_type; under PGC one pass
			# per company + root_type without subtree restriction is enough.
			centinela = f"__pgc_{root_type}__"
			if centinela in gl_entries_by_account:
				return
			gl_entries_by_account[centinela] = []
			return _set_gl_entries_by_account(
				company,
				from_date,
				to_date,
				filters,
				gl_entries_by_account,
				None,
				None,
				root_type=root_type,
				ignore_closing_entries=ignore_closing_entries,
				ignore_opening_entries=ignore_opening_entries,
				group_by_account=group_by_account,
			)

		return _set_gl_entries_by_account(
			company,
			from_date,
			to_date,
			filters,
			gl_entries_by_account,
			root_lft,
			root_rgt,
			root_type=root_type,
			ignore_closing_entries=ignore_closing_entries,
			ignore_opening_entries=ignore_opening_entries,
			group_by_account=group_by_account,
		)

	fs.get_accounts = get_accounts
	fs.set_gl_entries_by_account = set_gl_entries_by_account


def aplicar_doctype_extensions():
	"""On Frappe v15, patch methods that need class-level interception.

	Frappe v16+ applies the same logic via ``extend_doctype_class`` (mixins in
	``spain_compliance.overrides``). Patching the ERPNext classes here would
	double-wrap ``super()`` calls from those mixins, so we skip when extend is
	available.
	"""
	if _frappe_supports_extend_doctype_class():
		return

	try:
		from erpnext.accounts.doctype.account.account import Account
		from erpnext.accounts.doctype.sales_invoice.sales_invoice import SalesInvoice
	except ImportError:
		return

	if not getattr(SalesInvoice.set_status, "_spain_compliance", False):
		from spain_compliance.overrides.sales_invoice import set_status_with_loss_preservation

		_original_set_status = SalesInvoice.set_status

		def set_status(self, update=False, status=None, update_modified=True):
			set_status_with_loss_preservation(
				self,
				lambda **kwargs: _original_set_status(self, **kwargs),
				update=update,
				status=status,
				update_modified=update_modified,
			)

		set_status._spain_compliance = True
		SalesInvoice.set_status = set_status

	if not getattr(Account.set_root_and_report_type, "_spain_compliance", False):
		from spain_compliance.overrides.account import set_root_and_report_type_pgc

		_original_set_root = Account.set_root_and_report_type

		def set_root_and_report_type(self):
			set_root_and_report_type_pgc(self, lambda: _original_set_root(self))

		set_root_and_report_type._spain_compliance = True
		Account.set_root_and_report_type = set_root_and_report_type


def aplicar():
	aplicar_informes_pgc()
	aplicar_doctype_extensions()
