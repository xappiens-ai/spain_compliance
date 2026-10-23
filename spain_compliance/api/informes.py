# Copyright (c) 2026, Xappiens and contributors
# License: MIT

"""Informes del portal /contabilidad.

Los estados contables (PyG, balance, sumas y saldos) reutilizan el motor de
ERPNext, ya parcheado para el árbol PGC, y devuelven un JSON propio de la SPA.
El libro de IVA y la liquidación salen de ``Registro Fiscal IVA``.
El libro mayor y el plan de cuentas se consultan aquí, sin el informe de Desk.
"""

from __future__ import annotations

import frappe
from frappe import _
from frappe.query_builder.functions import Coalesce, Count, Sum
from frappe.utils import cint, flt, getdate, today

from spain_compliance.api.permission import has_app_permission
from spain_compliance.contabilidad.clasificacion import TIPOS_CON_CLAVE

_LIBROS = ("Expedidas", "Recibidas")
_MAX_FILAS = 500
# IVA, recargo, IGIC e IPSI. Retención IRPF y «Otro» viven en el mismo registro
# pero no forman parte del libro ni de la liquidación de IVA.
_TIPOS_LIBRO_IVA = TIPOS_CON_CLAVE
_CAMPOS_AJUSTES = (
	"pgc_espanol",
	"serie_rectificativas",
	"meses_dudoso_cobro",
	"regimen_iva",
	"periodicidad_modelo_303",
	"modelo_cuentas_anuales",
	"epigrafe_iae",
	"prorrata_general",
	"prorrata_especial",
	"exigir_clasificacion_fiscal",
	"crear_cuenta_cliente_auto",
	"prefijo_cuenta_cliente",
	"digitos_cuenta_cliente",
	"crear_cuenta_proveedor_auto",
	"prefijo_cuenta_proveedor",
	"digitos_cuenta_proveedor",
	"contacto_aeat",
	"telefono_aeat",
)
_ROOT_LABEL = {
	"Asset": "Activo",
	"Liability": "Pasivo",
	"Equity": "Patrimonio",
	"Income": "Ingreso",
	"Expense": "Gasto",
}


def _exigir_acceso():
	if frappe.session.user == "Guest" or not has_app_permission():
		frappe.throw(_("No tiene permiso para Contabilidad"), frappe.PermissionError)


def _compania(company: str) -> str:
	_exigir_acceso()
	if not company or not frappe.db.exists("Company", company):
		frappe.throw(_("Seleccione una compañía"))
	if not frappe.has_permission("Company", "read", company):
		frappe.throw(_("No tiene permiso para esta compañía"), frappe.PermissionError)
	return company


def _fechas(from_date, to_date):
	if not from_date or not to_date:
		frappe.throw(_("Indique la fecha de inicio y la fecha de fin"))
	inicio = getdate(from_date)
	fin = getdate(to_date)
	if inicio > fin:
		frappe.throw(_("La fecha de inicio no puede ser posterior a la fecha de fin"))
	return inicio, fin


def _moneda(company: str) -> str:
	return frappe.get_cached_value("Company", company, "default_currency") or "EUR"


def _ejercicio(company: str, on_date):
	from erpnext.accounts.utils import get_fiscal_year

	nombre, inicio, fin = get_fiscal_year(on_date, company=company, verbose=0)
	return nombre, getdate(inicio), getdate(fin)


def _periodo_por_defecto(company: str | None):
	hoy = getdate(today())
	if company:
		try:
			_nombre, inicio, fin = _ejercicio(company, hoy)
			return inicio, min(hoy, fin)
		except frappe.ValidationError:
			pass
	return hoy.replace(month=1, day=1), hoy


def _limpiar_etiqueta(value) -> str:
	text = "" if value is None else str(value)
	if len(text) >= 2 and text.startswith("'") and text.endswith("'"):
		return text[1:-1]
	return text


def _numero(value) -> float:
	return flt(value or 0)


def _serializar_estado(columns, data) -> dict:
	amount_columns = []
	for column in columns or []:
		if column.get("hidden"):
			continue
		fieldname = column.get("fieldname")
		if not fieldname or fieldname in {"account", "currency", "section"}:
			continue
		amount_columns.append(
			{
				"key": fieldname,
				"label": str(column.get("label") or fieldname),
				"type": column.get("fieldtype") or "Currency",
			}
		)

	rows = []
	for raw in data or []:
		if not raw:
			continue
		label = _limpiar_etiqueta(raw.get("account_name") or raw.get("account"))
		is_group = bool(raw.get("is_group") or raw.get("is_group_account"))
		rows.append(
			{
				"label": label,
				"indent": int(raw.get("indent") or 0),
				"is_group": is_group,
				"emphasis": is_group or label.lower().startswith("total"),
				"amounts": {column["key"]: _numero(raw.get(column["key"])) for column in amount_columns},
			}
		)
	return {"columns": amount_columns, "rows": rows}


def _filtros_estado(company: str, from_date, to_date, accumulated: int):
	return frappe._dict(
		{
			"company": company,
			"filter_based_on": "Date Range",
			"period_start_date": from_date,
			"period_end_date": to_date,
			"from_fiscal_year": None,
			"to_fiscal_year": None,
			"periodicity": "Yearly",
			"accumulated_values": accumulated,
			"include_default_book_entries": 1,
			"show_zero_values": 0,
		}
	)


def _ejecutar_estado(execute, filters) -> dict:
	result = execute(filters)
	columns = result[0] if result else []
	data = result[1] if result and len(result) > 1 else []
	message = result[2] if result and len(result) > 2 else None
	payload = _serializar_estado(columns, data)
	payload["message"] = message if isinstance(message, str) else ""
	payload["company"] = filters.company
	payload["currency"] = _moneda(filters.company)
	payload["from_date"] = str(getdate(filters.period_start_date))
	payload["to_date"] = str(getdate(filters.period_end_date))
	return payload


def _registro():
	if not frappe.has_permission("Registro Fiscal IVA", "read"):
		frappe.throw(_("No tiene permiso para el libro de IVA"), frappe.PermissionError)
	return frappe.qb.DocType("Registro Fiscal IVA")


def _filtros_libro(company, libro, inicio, fin, incluir_anulados):
	Doc = _registro()
	query_filters = (Doc.company == company) & (Doc.fecha >= inicio) & (Doc.fecha <= fin)
	if libro:
		if libro not in _LIBROS:
			frappe.throw(_("Libro no válido"))
		query_filters = query_filters & (Doc.libro == libro)
	if not cint(incluir_anulados):
		query_filters = query_filters & (Doc.anulado == 0)
	query_filters = query_filters & Doc.tipo_impuesto.isin(_TIPOS_LIBRO_IVA)
	return Doc, query_filters


def _resumen_libro(Doc, query_filters, agrupar_clave=True):
	totales = (
		frappe.qb.from_(Doc)
		.select(
			Count("*").as_("filas"),
			Coalesce(Sum(Doc.base_imponible), 0).as_("base"),
			Coalesce(Sum(Doc.cuota), 0).as_("cuota"),
			Coalesce(Sum(Doc.cuota_deducible), 0).as_("deducible"),
		)
		.where(query_filters)
		.run(as_dict=True)
	)[0]
	por_clave = []
	if agrupar_clave:
		por_clave = (
			frappe.qb.from_(Doc)
			.select(
				Doc.clave_iva,
				Doc.libro,
				Count("*").as_("filas"),
				Coalesce(Sum(Doc.base_imponible), 0).as_("base"),
				Coalesce(Sum(Doc.cuota), 0).as_("cuota"),
				Coalesce(Sum(Doc.cuota_deducible), 0).as_("deducible"),
			)
			.where(query_filters)
			.groupby(Doc.libro, Doc.clave_iva)
			.orderby(Doc.libro)
			.orderby(Doc.clave_iva)
			.run(as_dict=True)
		)
	return {
		"filas": int(totales.filas or 0),
		"base": _numero(totales.base),
		"cuota": _numero(totales.cuota),
		"deducible": _numero(totales.deducible),
		"por_clave": [
			{
				"libro": row.libro,
				"clave": row.clave_iva or _("Sin clave"),
				"filas": int(row.filas or 0),
				"base": _numero(row.base),
				"cuota": _numero(row.cuota),
				"deducible": _numero(row.deducible),
			}
			for row in por_clave
		],
	}


@frappe.whitelist()
def get_contexto() -> dict:
	"""Compañía por defecto y periodo del ejercicio en curso."""
	_exigir_acceso()
	companies = frappe.get_list("Company", fields=["name", "default_currency"], order_by="name asc", limit=100)
	preferida = frappe.defaults.get_user_default("Company") or frappe.db.get_single_value(
		"Global Defaults", "default_company"
	)
	nombres = [row.name for row in companies]
	company = preferida if preferida in nombres else (nombres[0] if nombres else None)
	inicio, fin = _periodo_por_defecto(company)
	return {
		"company": company,
		"companies": [{"name": row.name, "currency": row.default_currency or "EUR"} for row in companies],
		"from_date": str(inicio),
		"to_date": str(fin),
		"currency": _moneda(company) if company else "EUR",
	}


@frappe.whitelist()
def perdidas_y_ganancias(company: str, from_date: str, to_date: str) -> dict:
	company = _compania(company)
	if not frappe.has_permission("GL Entry", "read"):
		frappe.throw(_("No tiene permiso para ver la cuenta de resultados"), frappe.PermissionError)
	inicio, fin = _fechas(from_date, to_date)
	from erpnext.accounts.report.profit_and_loss_statement.profit_and_loss_statement import execute

	return _ejecutar_estado(execute, _filtros_estado(company, inicio, fin, accumulated=0))


@frappe.whitelist()
def balance_situacion(company: str, to_date: str, from_date: str | None = None) -> dict:
	"""Balance a una fecha. El saldo acumula todo el histórico hasta ese día."""
	company = _compania(company)
	if not frappe.has_permission("GL Entry", "read"):
		frappe.throw(_("No tiene permiso para ver el balance"), frappe.PermissionError)
	fin = getdate(to_date or from_date or today())
	try:
		_nombre, inicio, fy_fin = _ejercicio(company, fin)
	except frappe.ValidationError:
		inicio = fin.replace(month=1, day=1)
		fy_fin = fin.replace(month=12, day=31)
	if fin > fy_fin:
		fin = fy_fin
	from erpnext.accounts.report.balance_sheet.balance_sheet import execute

	payload = _ejecutar_estado(execute, _filtros_estado(company, inicio, fin, accumulated=1))
	payload["from_date"] = str(inicio)
	payload["to_date"] = str(fin)
	return payload


@frappe.whitelist()
def sumas_y_saldos(company: str, from_date: str, to_date: str) -> dict:
	company = _compania(company)
	if not frappe.has_permission("GL Entry", "read"):
		frappe.throw(_("No tiene permiso para ver las sumas y saldos"), frappe.PermissionError)
	inicio, fin = _fechas(from_date, to_date)
	nombre, fy_inicio, fy_fin = _ejercicio(company, inicio)
	if inicio < fy_inicio or fin > fy_fin:
		frappe.throw(
			_("El periodo debe estar dentro del ejercicio {0} ({1} – {2})").format(
				nombre, frappe.format(fy_inicio, {"fieldtype": "Date"}), frappe.format(fy_fin, {"fieldtype": "Date"})
			)
		)
	from erpnext.accounts.report.trial_balance.trial_balance import execute

	filters = frappe._dict(
		{
			"company": company,
			"fiscal_year": nombre,
			"from_date": inicio,
			"to_date": fin,
			"show_group_accounts": 1,
			"show_zero_values": 0,
			"show_net_values": 1,
			"with_period_closing_entry_for_current_period": 1,
			"include_default_book_entries": 1,
		}
	)
	columns, data = execute(filters)
	payload = _serializar_estado(columns, data)
	payload.update(
		{
			"message": "",
			"company": company,
			"currency": _moneda(company),
			"from_date": str(inicio),
			"to_date": str(fin),
			"fiscal_year": nombre,
		}
	)
	return payload


def _cuentas_descendientes(company: str, account: str) -> list[str]:
	row = frappe.db.get_value("Account", account, ["name", "company", "lft", "rgt", "is_group"], as_dict=True)
	if not row or row.company != company:
		frappe.throw(_("La cuenta no pertenece a la compañía"))
	if not row.is_group:
		return [row.name]
	return frappe.get_all(
		"Account",
		filters={"company": company, "lft": [">=", row.lft], "rgt": ["<=", row.rgt]},
		pluck="name",
	)


@frappe.whitelist()
def libro_mayor(company: str, from_date: str, to_date: str, account: str | None = None) -> dict:
	company = _compania(company)
	if not frappe.has_permission("GL Entry", "read"):
		frappe.throw(_("No tiene permiso para ver el libro mayor"), frappe.PermissionError)
	inicio, fin = _fechas(from_date, to_date)
	cuentas = _cuentas_descendientes(company, account) if account else None

	GL = frappe.qb.DocType("GL Entry")
	condiciones = (
		(GL.company == company)
		& (GL.posting_date >= inicio)
		& (GL.posting_date <= fin)
		& (GL.is_cancelled == 0)
	)
	if cuentas:
		condiciones = condiciones & GL.account.isin(cuentas)

	finance_book = frappe.get_cached_value("Company", company, "default_finance_book") or ""
	condiciones = condiciones & (
		GL.finance_book.isnull() | GL.finance_book.isin(["", finance_book])
	)

	total = (
		frappe.qb.from_(GL).select(Count("*").as_("filas")).where(condiciones).run(as_dict=True)
	)[0].filas
	movimientos = (
		frappe.qb.from_(GL)
		.select(
			GL.name,
			GL.posting_date,
			GL.account,
			GL.debit,
			GL.credit,
			GL.voucher_type,
			GL.voucher_no,
			GL.party,
			GL.against,
			GL.remarks,
		)
		.where(condiciones)
		.orderby(GL.posting_date)
		.orderby(GL.creation)
		.limit(_MAX_FILAS)
		.run(as_dict=True)
	)

	apertura = 0.0
	if cuentas:
		apertura_q = (
			frappe.qb.from_(GL)
			.select(Coalesce(Sum(GL.debit), 0).as_("debit"), Coalesce(Sum(GL.credit), 0).as_("credit"))
			.where(
				(GL.company == company)
				& (GL.posting_date < inicio)
				& (GL.is_cancelled == 0)
				& GL.account.isin(cuentas)
				& (GL.finance_book.isnull() | GL.finance_book.isin(["", finance_book]))
			)
			.run(as_dict=True)
		)[0]
		apertura = _numero(apertura_q.debit) - _numero(apertura_q.credit)

	saldo = apertura
	rows = []
	for row in movimientos:
		debe = _numero(row.debit)
		haber = _numero(row.credit)
		if cuentas:
			saldo += debe - haber
		rows.append(
			{
				"name": row.name,
				"posting_date": str(row.posting_date),
				"account": row.account,
				"debit": debe,
				"credit": haber,
				"balance": saldo if cuentas else None,
				"voucher_type": row.voucher_type,
				"voucher_no": row.voucher_no,
				"party": row.party or "",
				"against": row.against or "",
				"remarks": row.remarks or "",
			}
		)

	return {
		"company": company,
		"currency": _moneda(company),
		"from_date": str(inicio),
		"to_date": str(fin),
		"account": account or "",
		"opening_balance": apertura if cuentas else None,
		"rows": rows,
		"total": int(total or 0),
		"truncated": int(total or 0) > len(rows),
	}


@frappe.whitelist()
def libro_iva(
	company: str,
	from_date: str,
	to_date: str,
	libro: str = "Expedidas",
	incluir_anulados: int | str = 0,
) -> dict:
	company = _compania(company)
	inicio, fin = _fechas(from_date, to_date)
	Doc, query_filters = _filtros_libro(company, libro, inicio, fin, incluir_anulados)
	resumen = _resumen_libro(Doc, query_filters)
	sin_clasificar = (
		frappe.qb.from_(Doc)
		.select(Count("*").as_("filas"))
		.where(query_filters & (Doc.sin_clasificar == 1))
		.run(as_dict=True)
	)[0].filas

	filas = (
		frappe.qb.from_(Doc)
		.select(
			Doc.name,
			Doc.fecha,
			Doc.libro,
			Doc.numero,
			Doc.numero_externo,
			Doc.party_name,
			Doc.nif,
			Doc.clave_iva,
			Doc.tipo_impuesto,
			Doc.base_imponible,
			Doc.tipo_impositivo,
			Doc.cuota,
			Doc.cuota_deducible,
			Doc.total_factura,
			Doc.anulado,
			Doc.sin_clasificar,
			Doc.voucher_type,
			Doc.voucher_no,
		)
		.where(query_filters)
		.orderby(Doc.fecha)
		.orderby(Doc.numero)
		.limit(_MAX_FILAS)
		.run(as_dict=True)
	)
	rows = [
		{
			"name": row.name,
			"fecha": str(row.fecha),
			"libro": row.libro,
			"numero": row.numero_externo or row.numero or "",
			"party_name": row.party_name or "",
			"nif": row.nif or "",
			"clave": row.clave_iva or "",
			"tipo_impuesto": row.tipo_impuesto or "",
			"base": _numero(row.base_imponible),
			"tipo": _numero(row.tipo_impositivo),
			"cuota": _numero(row.cuota),
			"deducible": _numero(row.cuota_deducible),
			"total": _numero(row.total_factura),
			"anulado": bool(row.anulado),
			"sin_clasificar": bool(row.sin_clasificar),
			"voucher_type": row.voucher_type,
			"voucher_no": row.voucher_no,
		}
		for row in filas
	]
	return {
		"company": company,
		"currency": _moneda(company),
		"libro": libro,
		"from_date": str(inicio),
		"to_date": str(fin),
		"rows": rows,
		"totals": {
			"filas": resumen["filas"],
			"base": resumen["base"],
			"cuota": resumen["cuota"],
			"deducible": resumen["deducible"],
		},
		"por_clave": resumen["por_clave"],
		"sin_clasificar": int(sin_clasificar or 0),
		"truncated": resumen["filas"] > len(rows),
	}


@frappe.whitelist()
def liquidacion_iva(company: str, from_date: str, to_date: str) -> dict:
	"""Borrador de liquidación a partir del registro fiscal. No es el modelo 303 presentado."""
	company = _compania(company)
	inicio, fin = _fechas(from_date, to_date)
	Doc, base = _filtros_libro(company, None, inicio, fin, incluir_anulados=0)
	expedidas = _resumen_libro(Doc, base & (Doc.libro == "Expedidas"))
	recibidas = _resumen_libro(Doc, base & (Doc.libro == "Recibidas"))
	resultado = expedidas["cuota"] - recibidas["deducible"]
	return {
		"company": company,
		"currency": _moneda(company),
		"from_date": str(inicio),
		"to_date": str(fin),
		"repercutido": {"base": expedidas["base"], "cuota": expedidas["cuota"], "filas": expedidas["filas"]},
		"soportado": {
			"base": recibidas["base"],
			"cuota": recibidas["cuota"],
			"deducible": recibidas["deducible"],
			"filas": recibidas["filas"],
		},
		"resultado": resultado,
		"a_ingresar": resultado > 0,
		"por_clave_expedidas": expedidas["por_clave"],
		"por_clave_recibidas": recibidas["por_clave"],
	}


@frappe.whitelist()
def plan_cuentas(company: str) -> dict:
	company = _compania(company)
	if not frappe.has_permission("Account", "read"):
		frappe.throw(_("No tiene permiso para ver el plan de cuentas"), frappe.PermissionError)
	cuentas = frappe.get_all(
		"Account",
		filters={"company": company},
		fields=[
			"name",
			"account_name",
			"account_number",
			"parent_account",
			"is_group",
			"root_type",
			"account_type",
		],
		order_by="lft asc",
		limit=2000,
	)
	por_nombre = {row.name: row for row in cuentas}

	def _nivel(name: str, vistos: set[str] | None = None) -> int:
		vistos = vistos or set()
		padre = por_nombre[name].parent_account
		if not padre or padre not in por_nombre or name in vistos:
			return 0
		vistos.add(name)
		return 1 + _nivel(padre, vistos)

	return {
		"company": company,
		"accounts": [
			{
				"name": row.name,
				"account_name": row.account_name,
				"account_number": row.account_number or "",
				"parent_account": row.parent_account or "",
				"is_group": bool(row.is_group),
				"root_type": row.root_type or "",
				"root_label": _(_ROOT_LABEL.get(row.root_type, row.root_type or "")),
				"account_type": row.account_type or "",
				"indent": _nivel(row.name),
			}
			for row in cuentas
		],
	}


@frappe.whitelist()
def ajustes(company: str) -> dict:
	"""Parámetros fiscales de la compañía. La edición sigue en el formulario de Desk."""
	company = _compania(company)
	meta = frappe.get_meta("Company")
	doc = frappe.get_cached_doc("Company", company)
	campos = []
	for fieldname in _CAMPOS_AJUSTES:
		if not meta.has_field(fieldname):
			continue
		df = meta.get_field(fieldname)
		campos.append(
			{
				"fieldname": fieldname,
				"label": df.label,
				"fieldtype": df.fieldtype,
				"value": doc.get(fieldname),
			}
		)
	return {
		"company": company,
		"company_name": doc.company_name,
		"abbr": doc.abbr,
		"tax_id": doc.tax_id or "",
		"currency": doc.default_currency,
		"country": doc.country,
		"fields": campos,
	}
