# Copyright (c) 2026, Xappiens and contributors
# License: MIT

"""Cuentas auxiliares por tercero del PGC (430xxxxx clientes, 400xxxxx proveedores).

En compañías PGC con la opción activada en Company:

- Al dar de alta un Customer / Supplier se crea su cuenta hoja con el siguiente
  número de la secuencia (``prefijo`` + contador hasta ``digitos``) bajo el grupo
  de 3 dígitos del prefijo, y se asigna en la tabla ``accounts`` del tercero.
- Al guardar una factura (venta / compra) de un tercero que aún no tiene cuenta
  en esa compañía se crea en ese momento y se usa como cuenta de la factura
  si esta apuntaba a la cuenta por defecto de la compañía.
- ``crear_cuentas_pendientes`` da cuenta a los terceros existentes (backfill).

Los huecos de la secuencia no se reutilizan: el número siguiente es siempre el
mayor existente + 1.
"""

from __future__ import annotations

import re

import frappe
from frappe import _
from frappe.utils import cint

from spain_compliance.contabilidad.plan_contable import es_compania_pgc
from spain_compliance.setup.custom_fields import (
	COMPANY_CUSTOMER_AUTO_FIELDNAME,
	COMPANY_CUSTOMER_DIGITS_FIELDNAME,
	COMPANY_CUSTOMER_PREFIX_FIELDNAME,
	COMPANY_SUPPLIER_AUTO_FIELDNAME,
	COMPANY_SUPPLIER_DIGITS_FIELDNAME,
	COMPANY_SUPPLIER_PREFIX_FIELDNAME,
)

ACCOUNT_NAME_MAX = 140

TIPOS: dict[str, dict] = {
	"Customer": {
		"auto": COMPANY_CUSTOMER_AUTO_FIELDNAME,
		"prefijo": COMPANY_CUSTOMER_PREFIX_FIELDNAME,
		"digitos": COMPANY_CUSTOMER_DIGITS_FIELDNAME,
		"name_field": "customer_name",
		"account_type": "Receivable",
		"root_type": "Asset",
		"default_account": "default_receivable_account",
		"invoice": "Sales Invoice",
		"invoice_party": "customer",
		"invoice_account": "debit_to",
		"movimientos": [("Sales Invoice", "customer"), ("Sales Order", "customer")],
	},
	"Supplier": {
		"auto": COMPANY_SUPPLIER_AUTO_FIELDNAME,
		"prefijo": COMPANY_SUPPLIER_PREFIX_FIELDNAME,
		"digitos": COMPANY_SUPPLIER_DIGITS_FIELDNAME,
		"name_field": "supplier_name",
		"account_type": "Payable",
		"root_type": "Liability",
		"default_account": "default_payable_account",
		"invoice": "Purchase Invoice",
		"invoice_party": "supplier",
		"invoice_account": "credit_to",
		"movimientos": [("Purchase Invoice", "supplier"), ("Purchase Order", "supplier")],
	},
}


class ConfigError(frappe.ValidationError):
	pass


# Configuración ------------------------------------------------------------------


def get_config(company: str, party_type: str) -> frappe._dict | None:
	"""Prefijo/dígitos si la creación automática está activa para ``party_type``; si no, None."""
	tipo = TIPOS[party_type]
	if not es_compania_pgc(company):
		return None
	if not frappe.db.has_column("Company", tipo["auto"]):
		return None
	values = frappe.get_cached_value("Company", company, [tipo["auto"], tipo["prefijo"], tipo["digitos"]])
	if not values or not cint(values[0]):
		return None
	return frappe._dict(prefijo=(values[1] or "").strip(), digitos=cint(values[2]))


def _validar_formato(prefijo: str, digitos: int, label: str):
	if not re.fullmatch(r"\d{3,}", prefijo or ""):
		frappe.throw(
			_("{0}: el prefijo debe tener al menos 3 cifras y solo números.").format(label), ConfigError
		)
	if digitos <= len(prefijo):
		frappe.throw(
			_("{0}: los dígitos ({1}) deben ser más que las cifras del prefijo ({2}).").format(
				label, digitos, prefijo
			),
			ConfigError,
		)


def _grupo_padre(company: str, prefijo: str) -> str | None:
	return frappe.db.get_value(
		"Account", {"company": company, "account_number": prefijo[:3], "is_group": 1}, "name"
	)


def validate_company(doc, method=None):
	"""doc_event Company.validate: configuración coherente antes de activarla."""
	if not doc.get("pgc_espanol"):
		return
	for tipo in TIPOS.values():
		if not cint(doc.get(tipo["auto"])):
			continue
		label = doc.meta.get_label(tipo["auto"])
		prefijo = (doc.get(tipo["prefijo"]) or "").strip()
		digitos = cint(doc.get(tipo["digitos"]))
		_validar_formato(prefijo, digitos, label)
		doc.set(tipo["prefijo"], prefijo)
		if not doc.is_new() and not _grupo_padre(doc.name, prefijo):
			frappe.throw(
				_("{0}: no existe el grupo de cuentas {1} en el plan de {2}.").format(
					label, prefijo[:3], doc.name
				),
				ConfigError,
			)


# Núcleo -----------------------------------------------------------------------


def cuenta_de_tercero(party_type: str, party: str, company: str) -> str | None:
	return frappe.db.get_value(
		"Party Account",
		{"parenttype": party_type, "parent": party, "company": company, "parentfield": "accounts"},
		"account",
	)


def siguiente_numero(company: str, prefijo: str, digitos: int) -> str:
	"""Mayor número de cuenta con ese prefijo y longitud + 1 (sin reutilizar huecos)."""
	actual = frappe.db.sql(
		"""
		SELECT MAX(CAST(account_number AS UNSIGNED))
		FROM `tabAccount`
		WHERE company = %(company)s
			AND account_number LIKE %(like)s
			AND CHAR_LENGTH(account_number) = %(digitos)s
			AND account_number REGEXP '^[0-9]+$'
		""",
		{"company": company, "like": f"{prefijo}%", "digitos": digitos},
	)[0][0]
	base = int(prefijo.ljust(digitos, "0"))
	numero = str(max(int(actual or 0), base) + 1)
	if len(numero) != digitos or not numero.startswith(prefijo):
		frappe.throw(
			_("La secuencia de cuentas {0} de {1} está agotada ({2} dígitos).").format(
				prefijo, company, digitos
			),
			ConfigError,
		)
	return numero


def _es_la_propia_compania(party_doc, company: str) -> bool:
	"""Tercero interno que representa a la misma compañía: no lleva cuenta auxiliar."""
	interno = party_doc.get("is_internal_customer") or party_doc.get("is_internal_supplier")
	return bool(interno) and party_doc.get("represents_company") == company


def _nombre_cuenta(party_doc, tipo: dict, numero: str, company: str) -> str:
	abbr = frappe.get_cached_value("Company", company, "abbr")
	nombre = (party_doc.get(tipo["name_field"]) or party_doc.name).strip()
	maximo = ACCOUNT_NAME_MAX - len(f"{numero} -  - {abbr}")
	return nombre[:maximo].strip()


def _moneda(party_doc, company: str) -> str:
	return party_doc.get("default_currency") or frappe.get_cached_value(
		"Company", company, "default_currency"
	)


def crear_cuenta_tercero(party_type: str, party: str | object, company: str) -> str | None:
	"""Crea y asigna la cuenta auxiliar del tercero en ``company``. Idempotente.

	Devuelve la cuenta asignada (nueva o ya existente) o None si la compañía no
	tiene la creación automática activada para ese tipo de tercero.
	"""
	config = get_config(company, party_type)
	if not config:
		return None

	party_doc = party if not isinstance(party, str) else frappe.get_doc(party_type, party)
	if _es_la_propia_compania(party_doc, company):
		return None
	existente = cuenta_de_tercero(party_type, party_doc.name, company)
	if existente:
		return existente

	tipo = TIPOS[party_type]
	_validar_formato(config.prefijo, config.digitos, company)
	padre = _grupo_padre(company, config.prefijo)
	if not padre:
		frappe.throw(
			_("No existe el grupo de cuentas {0} en el plan de {1}.").format(config.prefijo[:3], company),
			ConfigError,
		)

	# Serializa la numeración entre altas simultáneas en la misma compañía
	frappe.db.sql("SELECT name FROM `tabAccount` WHERE name = %s FOR UPDATE", padre)
	numero = siguiente_numero(company, config.prefijo, config.digitos)

	account = frappe.get_doc(
		{
			"doctype": "Account",
			"company": company,
			"parent_account": padre,
			"account_number": numero,
			"account_name": _nombre_cuenta(party_doc, tipo, numero, company),
			"is_group": 0,
			"account_type": tipo["account_type"],
			"root_type": tipo["root_type"],
			"report_type": "Balance Sheet",
			"account_currency": _moneda(party_doc, company),
		}
	)
	account.flags.ignore_permissions = True
	account.insert()

	row = party_doc.append("accounts", {"company": company, "account": account.name})
	row.db_insert()
	frappe.clear_document_cache(party_type, party_doc.name)
	return account.name


def _crear_aislado(party_type: str, party, company: str) -> str | None:
	"""``crear_cuenta_tercero`` en un savepoint: si falla, deshace solo esa cuenta y relanza."""
	savepoint = "spain_compliance_cuenta_tercero"
	frappe.db.savepoint(savepoint)
	try:
		cuenta = crear_cuenta_tercero(party_type, party, company)
	except Exception:
		frappe.db.rollback(save_point=savepoint)
		raise
	frappe.db.release_savepoint(savepoint)
	return cuenta


def _avisar_error(party_type: str, party: str, company: str):
	frappe.log_error(title=f"Spain Compliance: cuenta de {party_type} {party} ({company})")
	frappe.msgprint(
		_("No se ha podido crear la cuenta contable de {0} en {1}. Revisa el Error Log.").format(
			frappe.bold(party), company
		),
		indicator="orange",
		alert=True,
	)


def _companias_auto(party_type: str) -> list[str]:
	campo = TIPOS[party_type]["auto"]
	if not frappe.db.has_column("Company", campo):
		return []
	return frappe.get_all("Company", filters={"pgc_espanol": 1, campo: 1}, pluck="name")


# doc_events ---------------------------------------------------------------------


def on_party_insert(doc, method=None):
	"""Customer / Supplier after_insert: cuenta en cada compañía PGC con la opción activa."""
	for company in _companias_auto(doc.doctype):
		try:
			_crear_aislado(doc.doctype, doc, company)
		except Exception:
			_avisar_error(doc.doctype, doc.name, company)


def on_invoice_before_validate(doc, method=None):
	"""Sales / Purchase Invoice before_validate: el tercero tiene cuenta propia en la compañía."""
	if doc.docstatus != 0 or doc.get("is_return") or doc.get("is_opening") == "Yes":
		return
	party_type = "Customer" if doc.doctype == "Sales Invoice" else "Supplier"
	tipo = TIPOS[party_type]
	party = doc.get(tipo["invoice_party"])
	if not party or not doc.company or not get_config(doc.company, party_type):
		return

	cuenta = crear_cuenta_tercero(party_type, party, doc.company)
	if not cuenta:
		return

	actual = doc.get(tipo["invoice_account"])
	por_defecto = frappe.get_cached_value("Company", doc.company, tipo["default_account"])
	if not actual or actual == por_defecto or frappe.db.get_value("Account", actual, "disabled"):
		doc.set(tipo["invoice_account"], cuenta)


# Backfill -----------------------------------------------------------------------


def _con_movimientos(party_type: str, company: str) -> set[str]:
	partes = set(
		frappe.get_all(
			"GL Entry",
			filters={"company": company, "party_type": party_type, "is_cancelled": 0},
			pluck="party",
			distinct=True,
		)
	)
	for doctype, campo in TIPOS[party_type]["movimientos"]:
		partes.update(
			frappe.get_all(
				doctype,
				filters={"company": company, "docstatus": ["<", 2]},
				pluck=campo,
				distinct=True,
			)
		)
	return {p for p in partes if p}


def terceros_sin_cuenta(party_type: str, company: str, solo_con_movimientos: bool = True) -> list[str]:
	"""Terceros activos sin cuenta propia en ``company``, por fecha de alta."""
	con_cuenta = set(
		frappe.get_all(
			"Party Account",
			filters={"parenttype": party_type, "company": company, "parentfield": "accounts"},
			pluck="parent",
		)
	)
	interno = "is_internal_customer" if party_type == "Customer" else "is_internal_supplier"
	candidatos = frappe.get_all(
		party_type,
		filters={"disabled": 0},
		fields=["name", interno, "represents_company"],
		order_by="creation asc, name asc",
	)
	filtro = _con_movimientos(party_type, company) if solo_con_movimientos else None
	return [
		p.name
		for p in candidatos
		if p.name not in con_cuenta
		and not _es_la_propia_compania(p, company)
		and (filtro is None or p.name in filtro)
	]


def crear_cuentas_pendientes(
	company: str,
	party_type: str = "Customer",
	solo_con_movimientos: int = 1,
	dry_run: int = 1,
) -> dict:
	"""Backfill: crea la cuenta de los terceros que aún no la tienen en ``company``.

	Con ``dry_run`` solo devuelve qué se haría. Requiere la opción activa en Company.
	"""
	if party_type not in TIPOS:
		frappe.throw(_("Tipo de tercero no válido: {0}").format(party_type))
	config = get_config(company, party_type)
	if not config:
		frappe.throw(
			_("La creación automática de cuentas de {0} no está activa en {1}.").format(
				_(party_type), company
			),
			ConfigError,
		)

	pendientes = terceros_sin_cuenta(party_type, company, bool(cint(solo_con_movimientos)))
	resultado = {"company": company, "party_type": party_type, "pendientes": len(pendientes)}
	if cint(dry_run):
		resultado["terceros"] = pendientes
		return resultado

	creadas, errores = [], []
	for party in pendientes:
		try:
			creadas.append((party, _crear_aislado(party_type, party, company)))
		except Exception:
			frappe.log_error(title=f"Spain Compliance: backfill {party_type} {party} ({company})")
			errores.append(party)
	resultado.update(creadas=creadas, errores=errores)
	return resultado


@frappe.whitelist()
def crear_cuentas_pendientes_desde_company(company: str, party_type: str = "Customer"):
	"""Botón de Company: backfill en segundo plano de terceros con movimientos."""
	if not frappe.has_permission("Company", "write", doc=company) or not frappe.has_permission(
		"Account", "create"
	):
		frappe.throw(_("No tienes permiso para crear cuentas contables"), frappe.PermissionError)
	if party_type not in TIPOS or not get_config(company, party_type):
		frappe.throw(
			_("La creación automática de cuentas de {0} no está activa en {1}.").format(
				_(party_type), company
			)
		)
	frappe.enqueue(
		_backfill_job,
		queue="long",
		timeout=3600,
		job_name=f"spain_compliance_cuentas_{party_type}_{company}",
		company=company,
		party_type=party_type,
		user=frappe.session.user,
	)
	return {"queued": True}


def _backfill_job(company: str, party_type: str, user: str):
	resultado = crear_cuentas_pendientes(company, party_type, solo_con_movimientos=1, dry_run=0)
	frappe.db.commit()
	frappe.publish_realtime(
		"msgprint",
		{
			"message": _("Cuentas creadas: {0} · Errores: {1} (ver Error Log).").format(
				len(resultado["creadas"]), len(resultado["errores"])
			),
			"indicator": "orange" if resultado["errores"] else "green",
			"title": _("Cuentas de terceros · {0}").format(company),
		},
		user=user,
	)
	return resultado
