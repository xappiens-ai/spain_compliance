# Copyright (c) 2026, Xappiens and contributors
# License: MIT

"""Plan General Contable español: árbol de cuentas con los 9 grupos PGC.

ERPNext organiza el plan por ``root_type`` (Asset/Liability/...). El PGC agrupa
por naturaleza (grupos 1-9) y dentro de un mismo grupo conviven cuentas de
activo y de pasivo (p. ej. 430 clientes vs 438 anticipos, 470 HP deudora vs
475 HP acreedora, 570 caja vs 521 deudas c/p).

Este módulo:

- Marca compañías como "PGC" (campo ``pgc_espanol`` en Company).
- Crea las raíces (grupos 1-9) y los subgrupos de 2 dígitos necesarios.
- Recoloca los grupos de 3 dígitos y las cuentas existentes bajo su subgrupo
  según el prefijo del ``account_number``.
- Elimina (o desactiva y recoloca, si tienen enlaces) las cuentas y raíces
  heredadas del plan estándar de ERPNext.

Junto con el override de Account (``spain_compliance.overrides.account``) y los
parches de ``spain_compliance.monkey_patches``, cada cuenta conserva su propio
``root_type`` aunque cuelgue de un grupo con otro tipo, y Balance / PyG siguen
cuadrando.

Punto de entrada para usuarios: botón "Convertir plan a PGC (9 grupos)" en el
formulario de Company (``convertir_plan_a_pgc``), o desde consola::

    bench --site <sitio> execute spain_compliance.contabilidad.plan_contable.reestructurar_arbol \
        --kwargs "{'company': 'Mi Empresa S.L.'}"
"""

from __future__ import annotations

import frappe
from frappe import _

from spain_compliance.setup.custom_fields import COMPANY_PGC_FIELDNAME

# Grupos PGC (raíces del árbol). root_type nominal: los hijos pueden diferir.
GRUPOS: dict[str, tuple[str, str]] = {
	"1": ("FINANCIACIÓN BÁSICA", "Equity"),
	"2": ("ACTIVO NO CORRIENTE", "Asset"),
	"3": ("EXISTENCIAS", "Asset"),
	"4": ("ACREEDORES Y DEUDORES POR OPERACIONES COMERCIALES", "Liability"),
	"5": ("CUENTAS FINANCIERAS", "Asset"),
	"6": ("COMPRAS Y GASTOS", "Expense"),
	"7": ("VENTAS E INGRESOS", "Income"),
	"8": ("GASTOS IMPUTADOS AL PATRIMONIO NETO", "Equity"),
	"9": ("INGRESOS IMPUTADOS AL PATRIMONIO NETO", "Equity"),
}

# Subgrupos PGC (2 dígitos). Se crean solo los necesarios.
SUBGRUPOS: dict[str, tuple[str, str]] = {
	"10": ("Capital", "Equity"),
	"11": ("Reservas", "Equity"),
	"12": ("Resultados pendientes de aplicación", "Equity"),
	"13": ("Subvenciones, donaciones y ajustes por cambios de valor", "Equity"),
	"14": ("Provisiones", "Liability"),
	"15": ("Deudas a largo plazo con características especiales", "Liability"),
	"16": ("Deudas a largo plazo con partes vinculadas", "Liability"),
	"17": ("Deudas a largo plazo por préstamos recibidos y otros conceptos", "Liability"),
	"18": ("Pasivos por fianzas y garantías a largo plazo", "Liability"),
	"19": ("Situaciones transitorias de financiación", "Equity"),
	"20": ("Inmovilizaciones intangibles", "Asset"),
	"21": ("Inmovilizaciones materiales", "Asset"),
	"22": ("Inversiones inmobiliarias", "Asset"),
	"23": ("Inmovilizaciones materiales en curso", "Asset"),
	"24": ("Inversiones financieras a largo plazo en partes vinculadas", "Asset"),
	"25": ("Otras inversiones financieras a largo plazo", "Asset"),
	"26": ("Fianzas y depósitos constituidos a largo plazo", "Asset"),
	"28": ("Amortización acumulada del inmovilizado", "Asset"),
	"29": ("Deterioro de valor de activos no corrientes", "Asset"),
	"30": ("Comerciales", "Asset"),
	"31": ("Materias primas", "Asset"),
	"32": ("Otros aprovisionamientos", "Asset"),
	"33": ("Productos en curso", "Asset"),
	"34": ("Productos semiterminados", "Asset"),
	"35": ("Productos terminados", "Asset"),
	"36": ("Subproductos, residuos y materiales recuperados", "Asset"),
	"39": ("Deterioro de valor de las existencias", "Asset"),
	"40": ("Proveedores", "Liability"),
	"41": ("Acreedores varios", "Liability"),
	"43": ("Clientes", "Asset"),
	"44": ("Deudores varios", "Asset"),
	"46": ("Personal", "Liability"),
	"47": ("Administraciones públicas", "Liability"),
	"48": ("Ajustes por periodificación", "Asset"),
	"49": ("Deterioro de valor de créditos comerciales y provisiones a corto plazo", "Asset"),
	"50": ("Empréstitos y otras emisiones análogas a corto plazo", "Liability"),
	"51": ("Deudas a corto plazo con partes vinculadas", "Liability"),
	"52": ("Deudas a corto plazo por préstamos recibidos y otros conceptos", "Liability"),
	"53": ("Inversiones financieras a corto plazo en partes vinculadas", "Asset"),
	"54": ("Otras inversiones financieras a corto plazo", "Asset"),
	"55": ("Otras cuentas no bancarias", "Asset"),
	"56": ("Fianzas y depósitos recibidos y constituidos a corto plazo", "Asset"),
	"57": ("Tesorería", "Asset"),
	"58": ("Activos no corrientes mantenidos para la venta", "Asset"),
	"59": ("Deterioro del valor de inversiones financieras a corto plazo", "Asset"),
	"60": ("Compras", "Expense"),
	"61": ("Variación de existencias", "Expense"),
	"62": ("Servicios exteriores", "Expense"),
	"63": ("Tributos", "Expense"),
	"64": ("Gastos de personal", "Expense"),
	"65": ("Otros gastos de gestión", "Expense"),
	"66": ("Gastos financieros", "Expense"),
	"67": ("Pérdidas procedentes de activos no corrientes y gastos excepcionales", "Expense"),
	"68": ("Amortizaciones", "Expense"),
	"69": ("Pérdidas por deterioro y otras dotaciones", "Expense"),
	"70": ("Ventas de mercaderías y prestaciones de servicios", "Income"),
	"71": ("Variación de existencias", "Income"),
	"73": ("Trabajos realizados para la empresa", "Income"),
	"74": ("Subvenciones, donaciones y legados", "Income"),
	"75": ("Otros ingresos de gestión", "Income"),
	"76": ("Ingresos financieros", "Income"),
	"77": ("Beneficios procedentes de activos no corrientes e ingresos excepcionales", "Income"),
	"79": ("Excesos y aplicaciones de provisiones y de pérdidas por deterioro", "Income"),
}

# Cuentas heredadas del plan estándar de ERPNext que no se pueden borrar
# (enlazadas a documentos presentados): se desactivan y se recolocan en su
# subgrupo PGC. Clave: ``account_type`` de ERPNext → subgrupo PGC. Las cuentas
# sin ``account_type`` reconocido caen en ``FALLBACK_SUBGRUPO`` por root_type.
# ``reestructurar_arbol`` admite además un mapa por nombre de cuenta (sin abbr).
RECOLOCACION_POR_ACCOUNT_TYPE: dict[str, str] = {
	"Receivable": "43",
	"Payable": "40",
	"Bank": "57",
	"Cash": "57",
	"Tax": "47",
	"Stock": "30",
	"Stock Received But Not Billed": "40",
	"Asset Received But Not Billed": "40",
	"Service Received But Not Billed": "40",
	"Stock Adjustment": "61",
	"Cost of Goods Sold": "60",
	"Expense Account": "62",
	"Expenses Included In Valuation": "62",
	"Direct Expense": "62",
	"Indirect Expense": "62",
	"Chargeable": "62",
	"Income Account": "70",
	"Direct Income": "70",
	"Indirect Income": "75",
	"Fixed Asset": "21",
	"Accumulated Depreciation": "28",
	"Depreciation": "68",
	"Capital Work in Progress": "23",
	"Round Off": "67",
	"Temporary": "55",
	"Equity": "10",
	"Current Asset": "55",
	"Current Liability": "52",
	"Liability": "52",
}

# Fallback por root_type para cuentas con enlaces no previstos.
FALLBACK_SUBGRUPO = {
	"Asset": "55",
	"Liability": "52",
	"Equity": "11",
	"Expense": "62",
	"Income": "75",
}


def es_compania_pgc(company: str | None) -> bool:
	"""True si la compañía usa el árbol PGC de 9 grupos (root_type por cuenta)."""
	if not company:
		return False
	try:
		return bool(frappe.get_cached_value("Company", company, COMPANY_PGC_FIELDNAME))
	except Exception:
		return False


def activar_pgc(company: str):
	"""Marca la compañía como PGC (requiere el custom field ya instalado)."""
	frappe.db.set_value("Company", company, COMPANY_PGC_FIELDNAME, 1)
	frappe.clear_cache(doctype="Company")


def _nombre_cuenta(company: str, numero: str, nombre: str) -> str:
	abbr = frappe.get_cached_value("Company", company, "abbr")
	return f"{numero} - {nombre} - {abbr}"


def _buscar_por_numero(company: str, numero: str) -> str | None:
	return frappe.db.get_value("Account", {"company": company, "account_number": numero})


def _crear_grupo(company: str, numero: str, nombre: str, root_type: str, parent: str | None) -> str:
	existente = _buscar_por_numero(company, numero)
	if existente:
		return existente
	doc = frappe.get_doc(
		{
			"doctype": "Account",
			"company": company,
			"account_name": nombre,
			"account_number": numero,
			"is_group": 1,
			"root_type": root_type,
			"report_type": "Profit and Loss" if root_type in ("Income", "Expense") else "Balance Sheet",
			"parent_account": parent,
		}
	)
	if not parent:
		# Las raíces se crean sin padre (igual que hace el importador de planes)
		doc.flags.ignore_mandatory = True
	doc.insert(ignore_permissions=True)
	return doc.name


def instalar_arbol_pgc(company: str, subgrupos: set[str] | None = None) -> dict[str, str]:
	"""Crea (idempotente) las 9 raíces y los subgrupos indicados (o los necesarios).

	Devuelve {codigo: nombre_cuenta} para grupos y subgrupos.
	"""
	if not frappe.db.has_column("Company", COMPANY_PGC_FIELDNAME):
		frappe.throw(
			_("Falta el custom field {0} en Company; ejecuta bench migrate.").format(COMPANY_PGC_FIELDNAME)
		)

	activar_pgc(company)
	nodos: dict[str, str] = {}

	for numero, (nombre, root_type) in GRUPOS.items():
		nodos[numero] = _crear_grupo(company, numero, nombre, root_type, parent=None)

	if subgrupos is None:
		# Subgrupos necesarios según las cuentas numeradas existentes
		numeros = frappe.get_all(
			"Account",
			filters={"company": company, "account_number": ["is", "set"]},
			pluck="account_number",
		)
		subgrupos = {n[:2] for n in numeros if n and len(n) >= 3 and n[:2] in SUBGRUPOS}

	for codigo in sorted(subgrupos):
		nombre, root_type = SUBGRUPOS[codigo]
		nodos[codigo] = _crear_grupo(company, codigo, nombre, root_type, parent=nodos[codigo[0]])

	return nodos


def _mover(cuenta: str, nuevo_padre: str):
	doc = frappe.get_doc("Account", cuenta)
	if doc.parent_account == nuevo_padre:
		return
	doc.parent_account = nuevo_padre
	doc.flags.ignore_permissions = True
	doc.save()


def _asegurar_subgrupo(company: str, codigo: str, nodos: dict[str, str]) -> str:
	if codigo not in nodos:
		nombre, root_type = SUBGRUPOS[codigo]
		nodos[codigo] = _crear_grupo(company, codigo, nombre, root_type, parent=nodos[codigo[0]])
	return nodos[codigo]


def reestructurar_arbol(
	company: str,
	raices_antiguas: list[str] | None = None,
	recolocaciones: dict[str, str] | None = None,
) -> dict:
	"""Reestructura el árbol al PGC de 9 grupos y limpia el plan estándar heredado.

	- Mueve los grupos de 3 dígitos bajo su subgrupo (2 dígitos) y este bajo su grupo.
	- Mueve cuentas numeradas huérfanas de grupo por prefijo.
	- Cuentas antiguas sin borrar posible → desactivadas y recolocadas.
	- Borra cuentas y raíces antiguas sin transacciones ni enlaces.

	``recolocaciones`` (opcional): ``{nombre de cuenta sin abbr: código PGC}`` para
	decidir a mano dónde recolocar cuentas heredadas que no se pueden borrar.
	Si no se indica, se usa ``account_type`` y, en su defecto, el ``root_type``.
	"""
	recolocaciones = recolocaciones or {}
	resumen = {"movidos": [], "recolocados": [], "borrados": [], "no_borrados": []}
	nodos = instalar_arbol_pgc(company)

	# 1) Grupos de 3 dígitos → subgrupo por prefijo
	grupos_3 = frappe.get_all(
		"Account",
		filters={"company": company, "is_group": 1, "account_number": ["like", "___"]},
		fields=["name", "account_number"],
	)
	for g in grupos_3:
		codigo = g.account_number[:2]
		if codigo in SUBGRUPOS:
			_mover(g.name, _asegurar_subgrupo(company, codigo, nodos))
			resumen["movidos"].append(g.name)

	# 2) Cuentas numeradas (>=4 dígitos) cuyo padre no es PGC → grupo de 3 dígitos o subgrupo
	hojas = frappe.get_all(
		"Account",
		filters={"company": company, "is_group": 0, "account_number": ["is", "set"]},
		fields=["name", "account_number", "parent_account"],
	)
	numeros_grupo = {g.account_number: g.name for g in grupos_3}
	for h in hojas:
		n = h.account_number or ""
		if len(n) < 4:
			continue
		destino = numeros_grupo.get(n[:3])
		if not destino and n[:2] in SUBGRUPOS:
			destino = _asegurar_subgrupo(company, n[:2], nodos)
		if destino and h.parent_account != destino:
			padre_actual = frappe.db.get_value("Account", h.parent_account, "account_number")
			if not padre_actual or padre_actual not in (n[:3], n[:2]):
				_mover(h.name, destino)
				resumen["movidos"].append(h.name)

	# 3) Raíces antiguas a limpiar (toda raíz que no sea un grupo PGC 1-9)
	if raices_antiguas is None:
		todas = frappe.get_all(
			"Account",
			filters={"company": company, "parent_account": ["is", "not set"]},
			fields=["name", "account_number"],
		)
		raices_antiguas = [r.name for r in todas if (r.account_number or "") not in GRUPOS]

	abbr = frappe.get_cached_value("Company", company, "abbr")

	def recolocar(nombre_cuenta: str, root_type: str, account_type: str | None):
		base = nombre_cuenta[: -len(f" - {abbr}")] if nombre_cuenta.endswith(f" - {abbr}") else nombre_cuenta
		codigo = (
			recolocaciones.get(base)
			or RECOLOCACION_POR_ACCOUNT_TYPE.get(account_type or "")
			or FALLBACK_SUBGRUPO.get(root_type, "55")
		)
		if len(codigo) == 3:
			destino = _buscar_por_numero(company, codigo) or _asegurar_subgrupo(company, codigo[:2], nodos)
		else:
			destino = _asegurar_subgrupo(company, codigo, nodos)
		doc = frappe.get_doc("Account", nombre_cuenta)
		doc.parent_account = destino
		doc.disabled = 1
		doc.flags.ignore_permissions = True
		doc.save()
		resumen["recolocados"].append(nombre_cuenta)

	# 4) Borrar (hojas primero); lo enlazado se desactiva y recoloca
	for _pass in range(6):
		pendientes = []
		for raiz in raices_antiguas:
			if not frappe.db.exists("Account", raiz):
				continue
			lft, rgt = frappe.db.get_value("Account", raiz, ["lft", "rgt"])
			pendientes += frappe.get_all(
				"Account",
				filters={"lft": [">", lft], "rgt": ["<", rgt]},
				fields=["name", "root_type", "account_type"],
				order_by="lft desc",
			)
		if not pendientes:
			break
		avance = False
		for cuenta in pendientes:
			if frappe.db.get_value("Account", cuenta.name, "is_group"):
				if frappe.db.count("Account", {"parent_account": cuenta.name}):
					continue
			try:
				frappe.delete_doc("Account", cuenta.name, ignore_permissions=True)
				resumen["borrados"].append(cuenta.name)
				avance = True
			except (frappe.LinkExistsError, frappe.ValidationError):
				if not frappe.db.get_value("Account", cuenta.name, "is_group"):
					recolocar(cuenta.name, cuenta.root_type, cuenta.account_type)
					avance = True
		if not avance:
			break

	# 5) Borrar raíces antiguas vacías
	for raiz in raices_antiguas:
		if not frappe.db.exists("Account", raiz):
			continue
		if frappe.db.count("Account", {"parent_account": raiz}):
			resumen["no_borrados"].append(raiz)
			continue
		try:
			frappe.delete_doc("Account", raiz, ignore_permissions=True)
			resumen["borrados"].append(raiz)
		except (frappe.LinkExistsError, frappe.ValidationError):
			resumen["no_borrados"].append(raiz)

	return resumen


# API ----------------------------------------------------------------------


def _check_pgc_permission(company: str):
	if not frappe.has_permission("Company", "write", doc=company):
		frappe.throw(
			_("No tienes permiso para modificar la compañía {0}").format(company), frappe.PermissionError
		)
	if not frappe.has_permission("Account", "write"):
		frappe.throw(_("No tienes permiso para modificar cuentas contables"), frappe.PermissionError)


@frappe.whitelist()
def convertir_plan_a_pgc(company: str):
	"""Convierte el plan de cuentas de ``company`` al árbol PGC de 9 grupos (en segundo plano)."""
	_check_pgc_permission(company)
	frappe.enqueue(
		_convertir_plan_a_pgc_job,
		queue="long",
		timeout=3600,
		job_name=f"spain_compliance_pgc_{company}",
		company=company,
		user=frappe.session.user,
	)
	return {"queued": True}


def _convertir_plan_a_pgc_job(company: str, user: str):
	try:
		resumen = reestructurar_arbol(company)
	except Exception:
		frappe.log_error(title=f"Spain Compliance: conversión PGC fallida ({company})")
		frappe.publish_realtime(
			"msgprint",
			{
				"message": _("La conversión al PGC de {0} ha fallado. Revisa el Error Log.").format(company),
				"indicator": "red",
				"title": _("Plan General Contable"),
			},
			user=user,
		)
		raise

	frappe.publish_realtime(
		"msgprint",
		{
			"message": _(
				"Plan de cuentas de {0} convertido al PGC de 9 grupos.<br>"
				"Movidas: {1} · Recolocadas y desactivadas: {2} · Borradas: {3} · Raíces no borradas: {4}"
			).format(
				frappe.bold(company),
				len(resumen["movidos"]),
				len(resumen["recolocados"]),
				len(resumen["borrados"]),
				len(resumen["no_borrados"]),
			),
			"indicator": "green",
			"title": _("Plan General Contable"),
		},
		user=user,
	)
	return resumen
