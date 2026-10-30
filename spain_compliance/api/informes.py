# Copyright (c) 2026, Xappiens and contributors
# License: MIT

"""Informes del portal /contabilidad.

El balance, la cuenta de pérdidas y ganancias y las sumas y saldos se calculan
sobre el GL con la estructura del PGC (``spain_compliance.contabilidad.cuentas_anuales``).
El libro de IVA y la liquidación salen de ``Registro Fiscal IVA``.
El libro diario, el libro mayor y el plan de cuentas se consultan aquí,
sin el informe de Desk.
"""

from __future__ import annotations

import math
from collections import defaultdict

import frappe
from frappe import _
from frappe.query_builder.functions import Coalesce, Count, Max, Min, Sum
from frappe.utils import add_days, add_years, cint, flt, getdate, today

from spain_compliance.api.permission import has_app_permission
from spain_compliance.contabilidad import cuentas_anuales as ca
from spain_compliance.contabilidad.clasificacion import TIPOS_CON_CLAVE
from spain_compliance.contabilidad.pgc import nombre_pgc, normalizar_numero

_LIBROS = ("Expedidas", "Recibidas")
_MAX_FILAS = 500
_MAX_MOVIMIENTOS_MAYOR = 5000
_MAX_ASIENTOS_EXPORTACION = 20000
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
_TIPOS_COMPROBANTE = {
	"Journal Entry": "Asiento",
	"Sales Invoice": "Factura de venta",
	"Purchase Invoice": "Factura de compra",
	"Payment Entry": "Cobro o pago",
	"Stock Entry": "Movimiento de stock",
	"Stock Reconciliation": "Regularización de stock",
	"Purchase Receipt": "Albarán de compra",
	"Delivery Note": "Albarán de venta",
	"Period Closing Voucher": "Cierre del ejercicio",
	"Asset": "Inmovilizado",
	"Asset Capitalization": "Capitalización de inmovilizado",
	"Asset Repair": "Reparación de inmovilizado",
	"Landed Cost Voucher": "Costes en destino",
	"Exchange Rate Revaluation": "Revalorización de divisas",
	"Invoice Discounting": "Descuento de facturas",
	"Process Deferred Accounting": "Periodificación",
	"Subcontracting Receipt": "Recepción de subcontratación",
	"Expense Claim": "Nota de gastos",
}
_CLASES_ASIENTO = ("Apertura", "Diario", "Regularización")


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


def _exigir_gl(mensaje: str):
	if not frappe.has_permission("GL Entry", "read"):
		frappe.throw(mensaje, frappe.PermissionError)


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
	return ca.ejercicio(company, on_date)


def _periodo_por_defecto(company: str | None):
	hoy = getdate(today())
	if company:
		try:
			_nombre, inicio, fin = _ejercicio(company, hoy)
			return inicio, min(hoy, fin)
		except frappe.ValidationError:
			pass
	return hoy.replace(month=1, day=1), hoy


def _numero(value) -> float:
	return flt(value or 0)


def _formato_fecha(fecha) -> str:
	return frappe.format(getdate(fecha), {"fieldtype": "Date"})


def _ejercicios(company: str) -> list[dict]:
	limitados: dict[str, set[str]] = defaultdict(set)
	for row in frappe.get_all("Fiscal Year Company", fields=["parent", "company"]):
		limitados[row.parent].add(row.company)
	return [
		{"name": row.name, "start": str(row.year_start_date), "end": str(row.year_end_date)}
		for row in frappe.get_all(
			"Fiscal Year",
			filters={"disabled": 0},
			fields=["name", "year_start_date", "year_end_date"],
			order_by="year_start_date desc",
		)
		if not limitados.get(row.name) or company in limitados[row.name]
	]


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
	"""Compañías, periodo del ejercicio en curso y ejercicios de cada compañía."""
	_exigir_acceso()
	companies = frappe.get_list(
		"Company",
		fields=["name", "default_currency", "tax_id", "modelo_cuentas_anuales"],
		order_by="name asc",
		limit=100,
	)
	preferida = frappe.defaults.get_user_default("Company") or frappe.db.get_single_value(
		"Global Defaults", "default_company"
	)
	nombres = [row.name for row in companies]
	company = preferida if preferida in nombres else (nombres[0] if nombres else None)
	inicio, fin = _periodo_por_defecto(company)
	return {
		"company": company,
		"companies": [
			{
				"name": row.name,
				"currency": row.default_currency or "EUR",
				"tax_id": row.tax_id or "",
				"modelo": row.modelo_cuentas_anuales or "",
				"fiscal_years": _ejercicios(row.name),
			}
			for row in companies
		],
		"from_date": str(inicio),
		"to_date": str(fin),
		"today": str(getdate(today())),
		"currency": _moneda(company) if company else "EUR",
	}


# Estados contables -------------------------------------------------------------------


@frappe.whitelist()
def perdidas_y_ganancias(company: str, from_date: str, to_date: str, comparar: int | str = 1) -> dict:
	"""Cuenta de pérdidas y ganancias del PGC con el mismo periodo del año anterior."""
	company = _compania(company)
	_exigir_gl(_("No tiene permiso para ver la cuenta de resultados"))
	inicio, fin = _fechas(from_date, to_date)
	periodos = [(inicio, fin)]
	if cint(comparar):
		periodos.append(ca.periodo_anterior(inicio, fin))

	calculos = [ca.calcular_pyg(company, desde, hasta) for desde, hasta in periodos]
	lineas = ca.lineas_pyg([periodo for periodo, _mensual in calculos])
	meses = [ca.meses_entre(desde, hasta) for desde, hasta in periodos]
	avisos = {}
	for periodo, _mensual in calculos:
		avisos.update(periodo.avisos)

	try:
		nombre_ejercicio = _ejercicio(company, fin)[0]
	except frappe.ValidationError:
		nombre_ejercicio = ""
	return {
		"company": company,
		"currency": _moneda(company),
		"from_date": str(inicio),
		"to_date": str(fin),
		"fiscal_year": nombre_ejercicio,
		"periodos": [
			{"desde": str(desde), "hasta": str(hasta), "label": _etiqueta_periodo(desde, hasta)}
			for desde, hasta in periodos
		],
		"lineas": lineas,
		"kpis": [ca.kpis_pyg(lineas, i) for i in range(len(periodos))],
		"meses": meses,
		"mensual": [
			ca.totales_pyg_mensuales(mensual, meses_periodo)
			for (_periodo, mensual), meses_periodo in zip(calculos, meses, strict=True)
		],
		"avisos": sorted(avisos.values()),
	}


def _etiqueta_periodo(desde, hasta) -> str:
	desde, hasta = getdate(desde), getdate(hasta)
	if desde.year == hasta.year and (desde.month, desde.day, hasta.month, hasta.day) == (1, 1, 12, 31):
		return str(desde.year)
	if desde.year == hasta.year:
		return _("{0} a {1}").format(desde.strftime("%d/%m"), hasta.strftime("%d/%m/%Y"))
	return _("{0} a {1}").format(_formato_fecha(desde), _formato_fecha(hasta))


@frappe.whitelist()
def balance_situacion(
	company: str, to_date: str, from_date: str | None = None, comparar: str = "cierre"
) -> dict:
	"""Balance a una fecha con la estructura del PGC.

	``comparar``: ``cierre`` (cierre del ejercicio anterior), ``interanual`` (misma
	fecha del año anterior) o vacío.
	"""
	company = _compania(company)
	_exigir_gl(_("No tiene permiso para ver el balance"))
	fecha = getdate(to_date or from_date or today())
	fechas = [fecha]
	nombre_ejercicio = ""
	try:
		nombre_ejercicio, fy_inicio, _fy_fin = _ejercicio(company, fecha)
	except frappe.ValidationError:
		fy_inicio = fecha.replace(month=1, day=1)
	if comparar == "cierre":
		fechas.append(getdate(add_days(fy_inicio, -1)))
	elif comparar == "interanual":
		fechas.append(getdate(add_years(fecha, -1)))

	periodos = [ca.calcular_balance(company, f) for f in fechas]
	activo = ca.construir_arbol(ca.ACTIVO, periodos)
	pasivo = ca.construir_arbol(ca.PATRIMONIO_PASIVO, periodos)
	masas = ca.masas_balance(activo, pasivo)
	avisos = {}
	for periodo in periodos:
		avisos.update(periodo.avisos)
	return {
		"company": company,
		"currency": _moneda(company),
		"from_date": str(fy_inicio),
		"to_date": str(fecha),
		"fiscal_year": nombre_ejercicio,
		"comparar": comparar or "",
		"periodos": [{"fecha": str(f), "label": _formato_fecha(f)} for f in fechas],
		"activo": activo,
		"pasivo": pasivo,
		"masas": masas,
		"ratios": [ca.ratios_balance(m) for m in masas],
		"descuadre": [round(m["activo"] - m["pasivo_total"], 2) for m in masas],
		"avisos": sorted(avisos.values()),
	}


@frappe.whitelist()
def sumas_y_saldos(company: str, from_date: str, to_date: str) -> dict:
	"""Balance de sumas y saldos por grupo, subgrupo, cuenta y subcuenta del PGC."""
	company = _compania(company)
	_exigir_gl(_("No tiene permiso para ver las sumas y saldos"))
	inicio, fin = _fechas(from_date, to_date)
	nombre, fy_inicio, fy_fin = _ejercicio(company, inicio)
	if inicio < fy_inicio or fin > fy_fin:
		frappe.throw(
			_("El periodo debe estar dentro del ejercicio {0}, del {1} al {2}").format(
				nombre, _formato_fecha(fy_inicio), _formato_fecha(fy_fin)
			)
		)
	resultado = ca.calcular_sumas_y_saldos(company, inicio, fin, fy_inicio)
	return {
		"company": company,
		"currency": _moneda(company),
		"from_date": str(inicio),
		"to_date": str(fin),
		"fiscal_year": nombre,
		"fiscal_year_start": str(fy_inicio),
		**resultado,
	}


# Libros ---------------------------------------------------------------------------------


def _cuentas_descendientes(company: str, account: str) -> list[str]:
	"""Subcuentas de una cuenta de grupo: las del árbol y las que empiezan por su número.

	El árbol de Desk depende de la plantilla de la compañía; el número PGC no.
	"""
	row = frappe.db.get_value(
		"Account", account, ["name", "company", "lft", "rgt", "is_group", "account_number"], as_dict=True
	)
	if not row or row.company != company:
		frappe.throw(_("La cuenta no pertenece a la compañía"))
	if not row.is_group:
		return [row.name]
	cuentas = set(
		frappe.get_all(
			"Account",
			filters={"company": company, "lft": [">=", row.lft], "rgt": ["<=", row.rgt], "is_group": 0},
			pluck="name",
		)
	)
	if row.account_number:
		cuentas.update(
			frappe.get_all(
				"Account",
				filters={
					"company": company,
					"is_group": 0,
					"account_number": ["like", f"{row.account_number}%"],
				},
				pluck="name",
			)
		)
	return sorted(cuentas)


def _condicion_gl(GL, company, inicio, fin, finance_book):
	return (
		(GL.company == company)
		& (GL.posting_date >= inicio)
		& (GL.posting_date <= fin)
		& (GL.is_cancelled == 0)
		& (GL.finance_book.isnull() | GL.finance_book.isin(["", finance_book or ""]))
	)


def _libro_por_defecto(company: str) -> str:
	return frappe.get_cached_value("Company", company, "default_finance_book") or ""


def _ejercicio_unico(company, inicio, fin):
	nombre, fy_start, fy_end = _ejercicio(company, inicio)
	otro, _, _ = _ejercicio(company, fin)
	if nombre != otro:
		frappe.throw(_("El libro diario se consulta dentro de un mismo ejercicio"))
	return nombre, fy_start, fy_end


def _clase_asiento(voucher_type: str, is_opening: str | None) -> str:
	# Código de Comercio: apertura, asiento ordinario y regularización (cierre de PyG).
	if is_opening == "Yes":
		return "Apertura"
	if voucher_type == "Period Closing Voucher":
		return "Regularización"
	return "Diario"


def _numeracion_asientos(company, desde, hasta, finance_book) -> dict:
	"""Número correlativo por comprobante, desde el inicio del ejercicio."""
	GL = frappe.qb.DocType("GL Entry")
	filas = (
		frappe.qb.from_(GL)
		.select(
			GL.voucher_type,
			GL.voucher_no,
			Min(GL.posting_date).as_("posting_date"),
			Min(GL.creation).as_("creation"),
			Max(GL.is_opening).as_("is_opening"),
			Sum(GL.debit).as_("debit"),
			Sum(GL.credit).as_("credit"),
		)
		.where(_condicion_gl(GL, company, desde, hasta, finance_book))
		.groupby(GL.voucher_type, GL.voucher_no)
		.orderby(Min(GL.posting_date))
		.orderby(Min(GL.creation))
		.orderby(GL.voucher_type)
		.orderby(GL.voucher_no)
		.run(as_dict=True)
	)
	return {
		(row.voucher_type, row.voucher_no): {
			"numero": index,
			"posting_date": getdate(row.posting_date),
			"is_opening": row.is_opening or "No",
			"debit": _numero(row.debit),
			"credit": _numero(row.credit),
		}
		for index, row in enumerate(filas, start=1)
	}


def _numeracion_rango(company, inicio, fin, finance_book) -> dict:
	"""Numeración de asientos de todos los ejercicios que toca el rango."""
	numeracion = {}
	actual = getdate(inicio)
	fin = getdate(fin)
	while actual <= fin:
		try:
			_nombre, fy_inicio, fy_fin = _ejercicio(company, actual)
		except frappe.ValidationError:
			break
		numeracion.update(_numeracion_asientos(company, fy_inicio, min(fy_fin, fin), finance_book))
		actual = getdate(add_days(fy_fin, 1))
	return numeracion


def _nombres_terceros(pares: set[tuple[str, str]]) -> dict[tuple[str, str], str]:
	campos = {"Customer": "customer_name", "Supplier": "supplier_name", "Employee": "employee_name"}
	por_tipo: dict[str, list[str]] = defaultdict(list)
	for party_type, party in pares:
		if party_type in campos and party:
			por_tipo[party_type].append(party)
	nombres = {}
	for party_type, partes in por_tipo.items():
		for row in frappe.get_all(
			party_type, filters={"name": ["in", partes]}, fields=["name", campos[party_type]]
		):
			nombres[(party_type, row.name)] = row.get(campos[party_type]) or row.name
	return nombres


def _cabeceras_comprobante(claves: list[tuple[str, str]]) -> dict:
	"""Concepto, tercero y subtipo de cada comprobante a partir de su documento."""
	por_tipo: dict[str, list[str]] = defaultdict(list)
	for voucher_type, voucher_no in claves:
		por_tipo[voucher_type].append(voucher_no)
	out: dict[tuple[str, str], dict] = {}

	def cargar(doctype, campos, construir):
		if not por_tipo.get(doctype):
			return
		for row in frappe.get_all(
			doctype, filters={"name": ["in", por_tipo[doctype]]}, fields=["name", *campos]
		):
			out[(doctype, row.name)] = construir(row)

	cargar(
		"Journal Entry",
		["user_remark", "title"],
		lambda row: {"concepto": (row.user_remark or row.title or "").strip(), "tercero": "", "subtipo": ""},
	)
	cargar(
		"Payment Entry",
		["remarks", "party_name", "payment_type"],
		lambda row: {
			"concepto": (row.remarks or "").strip(),
			"tercero": row.party_name or "",
			"subtipo": {"Receive": _("Cobro"), "Pay": _("Pago"), "Internal Transfer": _("Traspaso")}.get(
				row.payment_type, ""
			),
		},
	)
	cargar(
		"Sales Invoice",
		["customer_name", "remarks", "is_return"],
		lambda row: {
			"concepto": (row.remarks or "").strip()
			if (row.remarks or "").strip() not in ("", "No Remarks")
			else "",
			"tercero": row.customer_name or "",
			"subtipo": _("Rectificativa") if row.is_return else "",
		},
	)
	cargar(
		"Purchase Invoice",
		["supplier_name", "bill_no", "remarks", "is_return"],
		lambda row: {
			"concepto": (row.bill_no and _("Factura {0}").format(row.bill_no))
			or ((row.remarks or "").strip() if (row.remarks or "").strip() not in ("", "No Remarks") else ""),
			"tercero": row.supplier_name or "",
			"subtipo": _("Rectificativa") if row.is_return else "",
		},
	)
	return out


def _claves_por_texto(company, inicio, fin, finance_book, texto: str) -> set[tuple[str, str]]:
	GL = frappe.qb.DocType("GL Entry")
	Account = frappe.qb.DocType("Account")
	patron = f"%{texto.strip()}%"
	filas = (
		frappe.qb.from_(GL)
		.join(Account)
		.on(Account.name == GL.account)
		.select(GL.voucher_type, GL.voucher_no)
		.distinct()
		.where(_condicion_gl(GL, company, inicio, fin, finance_book))
		.where(
			GL.voucher_no.like(patron)
			| GL.remarks.like(patron)
			| GL.party.like(patron)
			| Account.account_number.like(f"{texto.strip()}%")
			| Account.account_name.like(patron)
		)
		.run(as_dict=True)
	)
	return {(row.voucher_type, row.voucher_no) for row in filas}


def _claves_por_cuenta(company, inicio, fin, finance_book, cuentas: list[str]) -> set[tuple[str, str]]:
	GL = frappe.qb.DocType("GL Entry")
	filas = (
		frappe.qb.from_(GL)
		.select(GL.voucher_type, GL.voucher_no)
		.distinct()
		.where(_condicion_gl(GL, company, inicio, fin, finance_book))
		.where(GL.account.isin(cuentas))
		.run(as_dict=True)
	)
	return {(row.voucher_type, row.voucher_no) for row in filas}


@frappe.whitelist()
def libro_diario(
	company: str,
	from_date: str,
	to_date: str,
	page: int | str = 1,
	page_size: int | str = 100,
	search: str | None = None,
	clase: str | None = None,
	voucher_type: str | None = None,
	account: str | None = None,
) -> dict:
	"""Libro Diario (Código de Comercio arts. 25-28).

	Un asiento es un comprobante validado. El número es correlativo en el
	ejercicio, por fecha de contabilización, y se calcula al consultar.
	``page_size`` 0 devuelve todos los asientos filtrados (exportación).
	"""
	company = _compania(company)
	_exigir_gl(_("No tiene permiso para ver el libro diario"))
	inicio, fin = _fechas(from_date, to_date)
	ejercicio, fy_start, _fy_end = _ejercicio_unico(company, inicio, fin)
	finance_book = _libro_por_defecto(company)
	numeracion = _numeracion_asientos(company, fy_start, fin, finance_book)

	en_periodo = [clave for clave, meta in numeracion.items() if meta["posting_date"] >= inicio]
	tipos: dict[str, int] = defaultdict(int)
	for voucher, _voucher_no in en_periodo:
		tipos[voucher] += 1

	claves = en_periodo
	if voucher_type:
		claves = [clave for clave in claves if clave[0] == voucher_type]
	if clase:
		if clase not in _CLASES_ASIENTO:
			frappe.throw(_("Clase de asiento no válida"))
		claves = [
			clave for clave in claves if _clase_asiento(clave[0], numeracion[clave]["is_opening"]) == clase
		]
	if account:
		permitidas = _claves_por_cuenta(
			company, inicio, fin, finance_book, _cuentas_descendientes(company, account)
		)
		claves = [clave for clave in claves if clave in permitidas]
	if search and search.strip():
		permitidas = _claves_por_texto(company, inicio, fin, finance_book, search)
		claves = [clave for clave in claves if clave in permitidas]
	claves.sort(key=lambda clave: numeracion[clave]["numero"])

	total_asientos = len(claves)
	tamano = cint(page_size)
	if tamano <= 0:
		tamano = _MAX_ASIENTOS_EXPORTACION
	paginas = max(1, math.ceil(total_asientos / tamano))
	pagina = min(max(1, cint(page) or 1), paginas)
	visibles = claves[(pagina - 1) * tamano : pagina * tamano]

	entries = _asientos(company, inicio, fin, finance_book, visibles, numeracion)
	total_debe = sum(numeracion[clave]["debit"] for clave in claves)
	total_haber = sum(numeracion[clave]["credit"] for clave in claves)
	return {
		"company": company,
		"currency": _moneda(company),
		"from_date": str(inicio),
		"to_date": str(fin),
		"fiscal_year": ejercicio,
		"fiscal_year_start": str(fy_start),
		"entries": entries,
		"totals": {
			"debe": round(total_debe, 2),
			"haber": round(total_haber, 2),
			"asientos": total_asientos,
			"asientos_periodo": len(en_periodo),
			"asientos_mostrados": len(entries),
			"filas": sum(len(entry["lines"]) for entry in entries),
		},
		"tipos": [
			{"value": tipo, "label": _(_TIPOS_COMPROBANTE.get(tipo, tipo)), "asientos": n}
			for tipo, n in sorted(tipos.items(), key=lambda item: -item[1])
		],
		"pagination": {"page": pagina, "pages": paginas, "page_size": tamano, "total": total_asientos},
		"cuadrado": abs(total_debe - total_haber) < 0.005,
		"truncated": paginas > 1,
	}


def _asientos(company, inicio, fin, finance_book, claves, numeracion) -> list[dict]:
	if not claves:
		return []
	GL = frappe.qb.DocType("GL Entry")
	Account = frappe.qb.DocType("Account")
	buscadas = set(claves)
	lineas = []
	numeros = sorted({voucher_no for _tipo, voucher_no in claves})
	for i in range(0, len(numeros), 1000):
		lineas.extend(
			row
			for row in frappe.qb.from_(GL)
			.join(Account)
			.on(Account.name == GL.account)
			.select(
				GL.name,
				GL.posting_date,
				GL.account,
				GL.debit,
				GL.credit,
				GL.voucher_type,
				GL.voucher_no,
				GL.remarks,
				GL.party_type,
				GL.party,
				Account.account_number,
				Account.account_name,
			)
			.where(_condicion_gl(GL, company, inicio, fin, finance_book))
			.where(GL.voucher_no.isin(numeros[i : i + 1000]))
			.orderby(GL.posting_date)
			.orderby(GL.creation)
			.orderby(GL.name)
			.run(as_dict=True)
			if (row.voucher_type, row.voucher_no) in buscadas
		)

	grupos: dict[tuple, list] = defaultdict(list)
	for row in lineas:
		grupos[(row.voucher_type, row.voucher_no)].append(row)
	cabeceras = _cabeceras_comprobante(list(grupos))
	terceros = _nombres_terceros({(row.party_type, row.party) for row in lineas if row.party})

	entries = []
	for clave in claves:
		filas = grupos.get(clave)
		if not filas:
			continue
		meta = numeracion[clave]
		filas.sort(
			key=lambda row: (
				0 if _numero(row.debit) else 1,
				row.account_number or "",
				row.account_name or "",
				row.name,
			)
		)
		cabecera = cabeceras.get(clave, {})
		concepto = cabecera.get("concepto") or next(
			(row.remarks.strip() for row in filas if (row.remarks or "").strip()), ""
		)
		lines = []
		for row in filas:
			lines.append(
				{
					"name": row.name,
					"account": row.account,
					"account_number": row.account_number or "",
					"account_name": row.account_name or row.account,
					"concepto": (row.remarks or "").strip() or concepto,
					"tercero": terceros.get((row.party_type, row.party), row.party or ""),
					"debit": _numero(row.debit),
					"credit": _numero(row.credit),
				}
			)
		entries.append(
			{
				"numero": meta["numero"],
				"posting_date": str(filas[0].posting_date),
				"voucher_type": clave[0],
				"voucher_label": _(_TIPOS_COMPROBANTE.get(clave[0], clave[0])),
				"voucher_subtype": cabecera.get("subtipo", ""),
				"voucher_no": clave[1],
				"clase": _clase_asiento(clave[0], meta.get("is_opening")),
				"concepto": concepto,
				"tercero": cabecera.get("tercero", ""),
				"debit": round(sum(line["debit"] for line in lines), 2),
				"credit": round(sum(line["credit"] for line in lines), 2),
				"lines": lines,
			}
		)
	return entries


@frappe.whitelist()
def libro_mayor(
	company: str,
	from_date: str,
	to_date: str,
	account: str | None = None,
	page: int | str = 1,
	page_size: int | str = 20,
) -> dict:
	"""Libro mayor por cuenta: saldo anterior, movimientos con saldo acumulado y totales.

	Sin cuenta lista todas las cuentas con movimientos, paginadas. Con una cuenta
	de grupo, sus subcuentas. El saldo anterior de las cuentas de resultados empieza
	en el ejercicio de la fecha de inicio.
	"""
	company = _compania(company)
	_exigir_gl(_("No tiene permiso para ver el libro mayor"))
	inicio, fin = _fechas(from_date, to_date)
	finance_book = _libro_por_defecto(company)
	try:
		fy_inicio = _ejercicio(company, inicio)[1]
	except frappe.ValidationError:
		fy_inicio = inicio.replace(month=1, day=1)
	alcance = _cuentas_descendientes(company, account) if account else None

	saldos = _saldos_mayor(company, inicio, fin, fy_inicio, finance_book, alcance)
	if account and len(alcance or []) == 1:
		visibles_alcance = alcance
	else:
		visibles_alcance = [
			cuenta
			for cuenta, s in saldos.items()
			if s["movimientos"] or (alcance is not None and abs(s["saldo_inicial"]) >= 0.005)
		]
	info = {
		row.name: row
		for row in frappe.get_all(
			"Account",
			filters={"name": ["in", visibles_alcance or [""]]},
			fields=["name", "account_number", "account_name", "root_type"],
		)
	}

	def orden_cuenta(name):
		cuenta = info.get(name)
		if not cuenta:
			return ("~", name)
		return (normalizar_numero(cuenta.account_number) or "~", cuenta.account_name or name)

	ordenadas = sorted(visibles_alcance, key=orden_cuenta)
	tamano = max(1, cint(page_size) or 20)
	paginas = max(1, math.ceil(len(ordenadas) / tamano))
	pagina = min(max(1, cint(page) or 1), paginas)
	en_pagina = ordenadas[(pagina - 1) * tamano : pagina * tamano]

	movimientos = _movimientos_mayor(company, inicio, fin, finance_book, en_pagina)
	numeracion = _numeracion_rango(company, inicio, fin, finance_book) if movimientos else {}
	terceros = _nombres_terceros({(row.party_type, row.party) for row in movimientos if row.party})
	por_cuenta: dict[str, list] = defaultdict(list)
	for row in movimientos:
		por_cuenta[row.account].append(row)

	cuentas = []
	for name in en_pagina:
		cuenta = info.get(name)
		s = saldos.get(name) or {"saldo_inicial": 0.0, "debe": 0.0, "haber": 0.0, "movimientos": 0}
		saldo = s["saldo_inicial"]
		filas = []
		for row in por_cuenta.get(name, []):
			debe, haber = _numero(row.debit), _numero(row.credit)
			saldo += debe - haber
			contrapartidas = [item.strip() for item in (row.against or "").split(",") if item.strip()]
			filas.append(
				{
					"name": row.name,
					"posting_date": str(row.posting_date),
					"asiento": (numeracion.get((row.voucher_type, row.voucher_no)) or {}).get("numero"),
					"voucher_type": row.voucher_type,
					"voucher_label": _(_TIPOS_COMPROBANTE.get(row.voucher_type, row.voucher_type)),
					"voucher_no": row.voucher_no,
					"concepto": (row.remarks or "").strip(),
					"contrapartida": contrapartidas[0] if contrapartidas else "",
					"contrapartidas": len(contrapartidas),
					"tercero": terceros.get((row.party_type, row.party), row.party or ""),
					"debit": debe,
					"credit": haber,
					"balance": round(saldo, 2),
				}
			)
		numero = normalizar_numero(cuenta.account_number) if cuenta else ""
		cuentas.append(
			{
				"account": name,
				"numero": numero,
				"nombre": (cuenta.account_name if cuenta else name) or name,
				"ruta": [
					{"codigo": numero[:largo], "nombre": nombre_pgc(numero[:largo])}
					for largo in (1, 2, 3)
					if len(numero) > largo and nombre_pgc(numero[:largo])
				],
				"pyg": ca.es_pyg(normalizar_numero(cuenta.account_number), cuenta.root_type)
				if cuenta
				else False,
				"saldo_inicial": round(s["saldo_inicial"], 2),
				"debe": round(s["debe"], 2),
				"haber": round(s["haber"], 2),
				"saldo_final": round(s["saldo_inicial"] + s["debe"] - s["haber"], 2),
				"n_movimientos": s["movimientos"],
				"movimientos": filas,
				"truncated": s["movimientos"] > len(filas),
			}
		)

	serie = None
	if len(cuentas) == 1 and cuentas[0]["movimientos"]:
		serie = _serie_diaria(cuentas[0])
	en_alcance = [saldos[name] for name in ordenadas if name in saldos]
	return {
		"company": company,
		"currency": _moneda(company),
		"from_date": str(inicio),
		"to_date": str(fin),
		"account": account or "",
		"cuentas": cuentas,
		"totales": {
			"cuentas": len(ordenadas),
			"saldo_inicial": round(sum(s["saldo_inicial"] for s in en_alcance), 2),
			"debe": round(sum(s["debe"] for s in en_alcance), 2),
			"haber": round(sum(s["haber"] for s in en_alcance), 2),
			"movimientos": sum(s["movimientos"] for s in en_alcance),
		},
		"pagination": {"page": pagina, "pages": paginas, "page_size": tamano, "total": len(ordenadas)},
		"serie": serie,
		"truncated": any(cuenta["truncated"] for cuenta in cuentas),
	}


def _saldos_mayor(company, inicio, fin, fy_inicio, finance_book, alcance) -> dict[str, dict]:
	params = {
		"company": company,
		"inicio": inicio,
		"fin": fin,
		"fy_inicio": fy_inicio,
		"finance_book": finance_book,
	}
	if alcance is not None:
		if not alcance:
			return {}
	filas = frappe.db.sql(
		"""
		SELECT g.account, a.account_number, a.root_type,
			IF(g.posting_date < %(inicio)s, 1, 0) AS previo,
			IF(g.posting_date < %(fy_inicio)s, 1, 0) AS antes_ejercicio,
			COUNT(*) AS lineas, SUM(g.debit) AS debe, SUM(g.credit) AS haber
		FROM `tabGL Entry` g
		INNER JOIN `tabAccount` a ON a.name = g.account
		WHERE g.company = %(company)s AND g.posting_date <= %(fin)s AND g.is_cancelled = 0
			AND (g.finance_book IS NULL OR g.finance_book IN ('', %(finance_book)s))
			AND (%(con_acotacion)s = 0 OR g.account IN %(alcance)s)
		GROUP BY g.account, previo, antes_ejercicio
		""",
		{
			**params,
			"alcance": tuple(alcance or ("",)),
			"con_acotacion": int(alcance is not None),
		},
		as_dict=True,
	)
	saldos: dict[str, dict] = {}
	for row in filas:
		s = saldos.setdefault(
			row.account, {"saldo_inicial": 0.0, "debe": 0.0, "haber": 0.0, "movimientos": 0}
		)
		if not row.previo:
			s["debe"] += _numero(row.debe)
			s["haber"] += _numero(row.haber)
			s["movimientos"] += int(row.lineas or 0)
		elif not (row.antes_ejercicio and ca.es_pyg(normalizar_numero(row.account_number), row.root_type)):
			s["saldo_inicial"] += _numero(row.debe) - _numero(row.haber)
	return saldos


def _movimientos_mayor(company, inicio, fin, finance_book, cuentas) -> list:
	if not cuentas:
		return []
	GL = frappe.qb.DocType("GL Entry")
	return (
		frappe.qb.from_(GL)
		.select(
			GL.name,
			GL.posting_date,
			GL.account,
			GL.debit,
			GL.credit,
			GL.voucher_type,
			GL.voucher_no,
			GL.party_type,
			GL.party,
			GL.against,
			GL.remarks,
		)
		.where(_condicion_gl(GL, company, inicio, fin, finance_book))
		.where(GL.account.isin(cuentas))
		.orderby(GL.account)
		.orderby(GL.posting_date)
		.orderby(GL.creation)
		.orderby(GL.name)
		.limit(_MAX_MOVIMIENTOS_MAYOR)
		.run(as_dict=True)
	)


def _serie_diaria(cuenta: dict) -> list[dict]:
	dias: dict[str, dict] = {}
	for fila in cuenta["movimientos"]:
		dia = dias.setdefault(
			fila["posting_date"], {"fecha": fila["posting_date"], "debe": 0.0, "haber": 0.0}
		)
		dia["debe"] += fila["debit"]
		dia["haber"] += fila["credit"]
		dia["saldo"] = fila["balance"]
	return [
		{"fecha": d["fecha"], "debe": round(d["debe"], 2), "haber": round(d["haber"], 2), "saldo": d["saldo"]}
		for d in dias.values()
	]


@frappe.whitelist()
def cuentas_con_movimiento(company: str, from_date: str, to_date: str) -> list[dict]:
	"""Subcuentas con movimientos en el periodo, en orden de número (navegación del mayor)."""
	company = _compania(company)
	_exigir_gl(_("No tiene permiso para ver el libro mayor"))
	inicio, fin = _fechas(from_date, to_date)
	filas = frappe.db.sql(
		"""
		SELECT g.account, a.account_number, a.account_name, COUNT(*) AS movimientos
		FROM `tabGL Entry` g
		INNER JOIN `tabAccount` a ON a.name = g.account
		WHERE g.company = %(company)s AND g.posting_date BETWEEN %(inicio)s AND %(fin)s
			AND g.is_cancelled = 0
		GROUP BY g.account
		""",
		{"company": company, "inicio": inicio, "fin": fin},
		as_dict=True,
	)
	return sorted(
		(
			{
				"account": row.account,
				"numero": normalizar_numero(row.account_number),
				"nombre": row.account_name or row.account,
				"movimientos": int(row.movimientos or 0),
			}
			for row in filas
		),
		key=lambda row: (row["numero"] or "~", row["nombre"]),
	)


@frappe.whitelist()
def buscar_cuentas(company: str, txt: str | None = None, limit: int | str = 40) -> list[dict]:
	"""Cuentas por número (prefijo) o nombre, para los selectores del portal."""
	company = _compania(company)
	if not frappe.has_permission("Account", "read"):
		frappe.throw(_("No tiene permiso para ver el plan de cuentas"), frappe.PermissionError)
	texto = (txt or "").strip()
	filtros = {"company": company}
	or_filtros = None
	if texto:
		or_filtros = {"account_number": ["like", f"{texto}%"], "account_name": ["like", f"%{texto}%"]}
	else:
		filtros["is_group"] = 1
	limite = min(max(cint(limit), 1), 200)
	filas = frappe.get_all(
		"Account",
		filters=filtros,
		or_filters=or_filtros,
		fields=["name", "account_number", "account_name", "is_group", "root_type"],
		order_by="account_number asc, lft asc",
		limit=limite * 3,
	)
	filas.sort(key=lambda row: (not (row.account_number or "").startswith(texto), row.account_number or "~"))
	filas = filas[:limite]
	salida = []
	for row in filas:
		numero = normalizar_numero(row.account_number)
		nombre = row.account_name
		if row.is_group and numero and len(numero) <= 3:
			nombre = nombre_pgc(numero) or nombre
		salida.append(
			{
				"account": row.name,
				"numero": numero,
				"nombre": nombre,
				"is_group": bool(row.is_group),
				"root_type": row.root_type or "",
			}
		)
	return salida


# IVA ----------------------------------------------------------------------------------


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


# Configuración ----------------------------------------------------------------------------


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
