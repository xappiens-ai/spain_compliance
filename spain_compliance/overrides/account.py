# Copyright (c) 2026, Xappiens and contributors
# License: MIT

"""Account extension for the Spanish PGC (9-group tree).

On companies marked with ``pgc_espanol``, each account keeps its own
``root_type``/``report_type`` even when the parent group has another
(e.g. 438 Customer advances — liability — under subgroup 43 Customers —
asset —). Other companies keep the native behaviour (inherit from parent
and propagate to children).

Wired via ``extend_doctype_class`` on Frappe v16+; on v15 the same method is
applied by ``monkey_patches`` (no ``override_doctype_class``).
"""

from __future__ import annotations

import frappe
from frappe.model.document import Document

from spain_compliance.contabilidad.plan_contable import es_compania_pgc


def set_root_and_report_type_pgc(doc, call_original):
	"""PGC-aware ``set_root_and_report_type``; ``call_original`` is the upstream impl."""
	if not es_compania_pgc(doc.company):
		return call_original()

	# Inherit from parent only when the account does not define its own root_type
	if doc.parent_account and not doc.root_type:
		parent_root_type = frappe.get_cached_value("Account", doc.parent_account, "root_type")
		if parent_root_type:
			doc.root_type = parent_root_type

	# report_type always consistent with this account's own root_type
	if doc.root_type:
		doc.report_type = (
			"Profit and Loss" if doc.root_type in ("Income", "Expense") else "Balance Sheet"
		)

	# Note: do not propagate root_type/report_type to descendants when editing a
	# group; under PGC each account keeps its own configuration.


class AccountMixin(Document):
	"""Frappe v16+ ``extend_doctype_class`` extension for PGC root types."""

	def set_root_and_report_type(self):
		set_root_and_report_type_pgc(
			self,
			lambda: super(AccountMixin, self).set_root_and_report_type(),
		)
