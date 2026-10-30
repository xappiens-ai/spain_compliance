# Copyright (c) 2026, Xappiens and contributors
# License: MIT

"""Plantilla de Plan General Contable español con números de cuenta.

Expone el chart ``Spain - PGCE con números`` a ERPNext (país España) y
permite reemplazar el plan de una compañía existente.
"""

from __future__ import annotations

import json
from pathlib import Path

import frappe
from frappe import _

CHART_NAME = "Spain - PGCE con números"
_CHART_FILE = Path(__file__).resolve().parent / "charts" / "es_pgce_con_numeros.json"


def load_pgc_chart() -> dict:
	"""Devuelve el árbol del PGC (clave ``tree`` del JSON)."""
	data = json.loads(_CHART_FILE.read_text(encoding="utf-8"))
	return data.get("tree") or {}


def get_pgc_chart_meta() -> dict:
	return json.loads(_CHART_FILE.read_text(encoding="utf-8"))


def patch_erpnext_charts():
	"""Extiende ``get_chart`` / ``get_charts_for_country`` con la plantilla PGC."""
	try:
		from erpnext.accounts.doctype.account.chart_of_accounts import chart_of_accounts as coa
	except ImportError:
		return

	if getattr(coa, "_spain_compliance_chart", False):
		return
	coa._spain_compliance_chart = True

	_get_chart = coa.get_chart
	_get_charts_for_country = coa.get_charts_for_country

	def get_chart(chart_template, existing_company=None):
		if not existing_company and chart_template == CHART_NAME:
			return load_pgc_chart()
		return _get_chart(chart_template, existing_company)

	def get_charts_for_country(country, with_standard=False):
		charts = list(_get_charts_for_country(country, with_standard=with_standard) or [])
		code = frappe.get_cached_value("Country", country, "code") if country else None
		if code == "es" and CHART_NAME not in charts:
			charts.insert(0, CHART_NAME)
		return charts

	coa.get_chart = get_chart
	coa.get_charts_for_country = get_charts_for_country


def _clear_company_account_defaults(company: str):
	meta = frappe.get_meta("Company")
	updates = {}
	for df in meta.fields:
		if (
			df.fieldtype == "Link"
			and df.options == "Account"
			and getattr(frappe.get_doc("Company", company), df.fieldname, None)
		):
			updates[df.fieldname] = None
	if updates:
		frappe.db.set_value("Company", company, updates)


def _delete_company_gl(company: str):
	frappe.db.delete("GL Entry", {"company": company})
	frappe.db.delete("Payment Ledger Entry", {"company": company})
	if frappe.db.exists("DocType", "Account Closing Balance"):
		frappe.db.delete("Account Closing Balance", {"company": company})


def _delete_company_accounts(company: str):
	"""Borra todas las cuentas de la compañía (hojas primero)."""
	for _attempt in range(12):
		cuentas = frappe.get_all(
			"Account",
			filters={"company": company},
			fields=["name", "is_group"],
			order_by="lft desc",
		)
		if not cuentas:
			return
		avance = False
		for c in cuentas:
			if c.is_group and frappe.db.exists("Account", {"parent_account": c.name}):
				continue
			try:
				frappe.delete_doc("Account", c.name, force=True, ignore_permissions=True)
				avance = True
			except Exception:
				frappe.db.sql("delete from `tabAccount` where name=%s", c.name)
				avance = True
		if not avance:
			frappe.db.sql("delete from `tabAccount` where company=%s", company)
			return
	else:
		frappe.throw(
			_("No se han podido eliminar todas las cuentas de {0} tras 12 intentos.").format(company)
		)


@frappe.whitelist()
def reemplazar_plan_por_pgc(company: str, wipe_gl: int | bool = 1):
	"""Elimina el plan actual (y opcionalmente el mayor) e importa el PGC español.

	Pensado para sitios que van a reimportar el mayor desde cero.
	"""
	if not frappe.has_permission("Company", "write", doc=company):
		frappe.throw(
			_("No tienes permiso para modificar la compañía {0}").format(company),
			frappe.PermissionError,
		)
	if not frappe.has_permission("Account", "write"):
		frappe.throw(_("No tienes permiso para modificar cuentas contables"), frappe.PermissionError)

	wipe_gl = int(wipe_gl)
	frappe.enqueue(
		_reemplazar_plan_por_pgc_job,
		queue="long",
		timeout=3600,
		job_name=f"spain_compliance_seed_pgc_{company}",
		company=company,
		wipe_gl=wipe_gl,
		user=frappe.session.user,
	)
	return {"queued": True}


def _reemplazar_plan_por_pgc_job(company: str, wipe_gl: int, user: str):
	try:
		resumen = sembrar_pgc(company, wipe_gl=bool(wipe_gl))
	except Exception:
		frappe.log_error(title=f"Spain Compliance: siembra PGC fallida ({company})")
		frappe.publish_realtime(
			"msgprint",
			{
				"message": _("La carga del PGC de {0} ha fallado. Revisa el Error Log.").format(company),
				"indicator": "red",
				"title": _("Plan General Contable"),
			},
			user=user,
		)
		raise

	def _avisar_exito():
		frappe.publish_realtime(
			"msgprint",
			{
				"message": _("Plan PGC cargado en {0}. Cuentas: {1}. GL borrado: {2}.").format(
					company, resumen.get("accounts"), resumen.get("wipe_gl")
				),
				"indicator": "green",
				"title": _("Plan General Contable"),
			},
			user=user,
		)

	# The RQ worker commits successful jobs. Notify only after that commit,
	# rather than splitting the account import into partial transactions.
	frappe.db.after_commit.add(_avisar_exito)


def sembrar_pgc(company: str, wipe_gl: bool = True) -> dict:
	"""Síncrono: limpia cuentas (y GL) e importa ``Spain - PGCE con números``."""
	from erpnext.accounts.doctype.account.chart_of_accounts.chart_of_accounts import create_charts

	from spain_compliance.contabilidad.plan_contable import activar_pgc

	if wipe_gl:
		_delete_company_gl(company)

	_clear_company_account_defaults(company)
	_delete_company_accounts(company)
	frappe.local.flags.ignore_chart_of_accounts = False
	create_charts(company, custom_chart=load_pgc_chart())
	activar_pgc(company)
	frappe.db.set_value("Company", company, "chart_of_accounts", CHART_NAME)

	n = frappe.db.count("Account", {"company": company})
	return {"company": company, "accounts": n, "wipe_gl": wipe_gl, "chart": CHART_NAME}
