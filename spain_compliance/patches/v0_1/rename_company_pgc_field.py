# Copyright (c) 2026, Xappiens and contributors
# License: MIT

"""Rename ``Company.custom_pgc_espanol`` (pre-release name) to ``Company.pgc_espanol``.

No-op on sites that never had the old field.
"""

import frappe

from spain_compliance.setup.custom_fields import COMPANY_PGC_FIELDNAME, create_app_custom_fields

OLD_FIELDNAME = "custom_pgc_espanol"


def execute():
	if not frappe.db.exists("Custom Field", f"Company-{OLD_FIELDNAME}"):
		return

	create_app_custom_fields()

	if frappe.db.has_column("Company", OLD_FIELDNAME) and frappe.db.has_column(
		"Company", COMPANY_PGC_FIELDNAME
	):
		# Literal identifiers only (fixed fieldnames); avoids f-string SQL.
		frappe.db.sql(
			"update `tabCompany` set `pgc_espanol` = `custom_pgc_espanol` "
			"where ifnull(`custom_pgc_espanol`, 0) = 1"
		)

	frappe.delete_doc("Custom Field", f"Company-{OLD_FIELDNAME}", force=True, ignore_permissions=True)
	if frappe.db.has_column("Company", OLD_FIELDNAME):
		frappe.db.sql_ddl("alter table `tabCompany` drop column `custom_pgc_espanol`")
	frappe.clear_cache(doctype="Company")
