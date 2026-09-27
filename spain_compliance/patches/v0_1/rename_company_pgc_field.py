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
		frappe.db.sql(
			f"update `tabCompany` set `{COMPANY_PGC_FIELDNAME}` = `{OLD_FIELDNAME}` where ifnull(`{OLD_FIELDNAME}`, 0) = 1"
		)

	frappe.delete_doc("Custom Field", f"Company-{OLD_FIELDNAME}", force=True, ignore_permissions=True)
	if frappe.db.has_column("Company", OLD_FIELDNAME):
		frappe.db.sql_ddl(f"alter table `tabCompany` drop column `{OLD_FIELDNAME}`")
	frappe.clear_cache(doctype="Company")
