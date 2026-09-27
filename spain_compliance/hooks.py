app_name = "spain_compliance"
app_title = "Spain Compliance"
app_publisher = "Xappiens"
app_description = (
	"Contabilidad española para ERPNext: Plan General Contable, series de facturas "
	"rectificativas, estados de cobro (dudoso cobro / pérdida) e interfaz de contabilidad."
)
app_email = "hello@xappiens.com"
app_license = "mit"
app_icon_url = "/assets/spain_compliance/images/logo.svg"
app_icon_title = "Contabilidad"
app_icon_route = "/contabilidad"

required_apps = ["frappe/erpnext"]

# Apps screen -----------------------------------------------------------------

add_to_apps_screen = [
	{
		"name": "spain_compliance",
		"logo": "/assets/spain_compliance/images/logo.svg",
		"title": "Contabilidad",
		"route": "/contabilidad",
		"has_permission": "spain_compliance.api.permission.has_app_permission",
	}
]

website_route_rules = [
	{"from_route": "/contabilidad/<path:app_path>", "to_route": "contabilidad"},
]

# Install / migrate -------------------------------------------------------------
# Custom Fields (Company, Sales Invoice) + "Dudoso Cobro" / "Pérdida" in Sales Invoice.status

after_install = "spain_compliance.install.after_install"
after_migrate = "spain_compliance.install.after_migrate"
before_uninstall = "spain_compliance.install.before_uninstall"

# DocType overrides -------------------------------------------------------------

override_doctype_class = {
	# Credit-note naming series + collection statuses
	"Sales Invoice": "spain_compliance.overrides.sales_invoice.SalesInvoice",
	# PGC: each account keeps its own root_type inside the 9-group tree
	"Account": "spain_compliance.overrides.account.SpainAccount",
}

doctype_js = {
	"Sales Invoice": "public/js/sales_invoice.js",
	"Company": "public/js/company.js",
}

# Scheduler -------------------------------------------------------------------------

scheduler_events = {
	"daily": [
		# Overdue invoices → "Dudoso Cobro" after Company.meses_dudoso_cobro months
		"spain_compliance.tasks.auto_mark_dudoso_cobro",
	],
}
