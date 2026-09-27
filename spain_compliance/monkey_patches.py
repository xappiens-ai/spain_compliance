# Copyright (c) 2026, Xappiens and contributors
# License: MIT

"""Parches para que Balance / PyG funcionen con el árbol PGC de 9 grupos.

Los informes financieros de ERPNext asumen que todas las cuentas de un
``root_type`` cuelgan de raíces con ese mismo ``root_type``:

1. ``get_data`` recorre las raíces del root_type y trae el GL solo de las
   cuentas dentro de esos subárboles (lft/rgt). Con el PGC, una cuenta de
   activo (430) puede colgar del grupo 4 (pasivo nominal) y se quedaría fuera.
2. ``filter_accounts`` descarta cuentas cuyo padre no está en la lista
   filtrada por root_type (ramas mixtas desaparecerían del informe).

Para compañías PGC (``Company.pgc_espanol``):

- ``set_gl_entries_by_account``: una sola pasada por root_type + compañía,
  sin restricción lft/rgt (deduplicada con una clave centinela).
- ``get_accounts``: añade los grupos ancestros como esqueleto para que la
  jerarquía se muestre completa; los totales solo suman las cuentas del
  root_type correspondiente.

En compañías no PGC el comportamiento es exactamente el nativo.
"""

from __future__ import annotations


def aplicar():
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
			# get_data llama una vez por raíz del root_type; con PGC basta una
			# pasada por compañía + root_type sin restricción de subárbol.
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
