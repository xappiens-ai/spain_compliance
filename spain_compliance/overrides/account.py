# Copyright (c) 2026, Xappiens and contributors
# License: MIT

"""Override de Account para el PGC español (árbol de 9 grupos).

En compañías marcadas con ``pgc_espanol``, cada cuenta conserva su
propio ``root_type``/``report_type`` aunque el grupo padre tenga otro
(p. ej. 438 Anticipos de clientes —pasivo— bajo el subgrupo 43 Clientes
—activo—). En el resto de compañías se mantiene el comportamiento nativo
(heredar del padre y propagar a los hijos).
"""

from __future__ import annotations

import frappe
from erpnext.accounts.doctype.account.account import Account

from spain_compliance.contabilidad.plan_contable import es_compania_pgc


class SpainAccount(Account):
	def set_root_and_report_type(self):
		if not es_compania_pgc(self.company):
			return super().set_root_and_report_type()

		# Heredar del padre solo si la cuenta no define su propio root_type
		if self.parent_account and not self.root_type:
			parent_root_type = frappe.get_cached_value("Account", self.parent_account, "root_type")
			if parent_root_type:
				self.root_type = parent_root_type

		# report_type siempre coherente con el root_type propio
		if self.root_type:
			self.report_type = (
				"Profit and Loss" if self.root_type in ("Income", "Expense") else "Balance Sheet"
			)

		# Nota: no se propaga root_type/report_type a los descendientes al
		# editar un grupo; en PGC cada cuenta mantiene su configuración.
