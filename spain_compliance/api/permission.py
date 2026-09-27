# Copyright (c) 2026, Xappiens and contributors
# For license information, please see license.txt

import frappe


def has_app_permission() -> bool:
	"""Users with Accounts or System Manager roles can open Contabilidad."""
	if frappe.session.user == "Administrator":
		return True

	roles = set(frappe.get_roles())
	return bool(roles & {"System Manager", "Accounts Manager", "Accounts User"})
