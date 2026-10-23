# Copyright (c) 2026, Xappiens and contributors
# License: MIT

"""Registro fiscal de IVA: una fila por factura, clave y tipo impositivo.

Se genera al validar una factura de venta o de compra de una compañía española
(o con el Plan General Contable activo) y se marca anulado al cancelarla.
Los libros y los modelos leerán de aquí.

La clasificación (tipo, clave, deducibilidad) vive en la fila de impuesto.
Si la fila está vacía y la factura usa una plantilla, se copia de la plantilla.
Las facturas ya validadas no se modifican: al reconstruir, la copia se hace
solo en memoria para calcular el registro.
"""

from __future__ import annotations

import json

import frappe
from frappe import _
from frappe.utils import cint, flt, getdate

from spain_compliance.contabilidad.clasificacion import (
	DEDUCIBLE_BIEN,
	DEDUCIBLE_NO,
	LIBRO_EXPEDIDAS,
	LIBRO_RECIBIDAS,
	TIPO_RETENCION,
	TIPOS_IVA,
)
from spain_compliance.contabilidad.identificacion import nif_espanol_valido, normalizar_identificador
from spain_compliance.setup.custom_fields import (
	COMPANY_PGC_FIELDNAME,
	TAX_CLASSIFICATION_FIELDS,
)

DOCTYPES_FACTURA = ("Sales Invoice", "Purchase Invoice")
_PLANTILLA = {
	"Sales Invoice": "Sales Taxes and Charges Template",
	"Purchase Invoice": "Purchase Taxes and Charges Template",
}


def aplica_registro_fiscal(company: str | None) -> bool:
	"""Compañía de España o con el árbol PGC. El resto del sitio no se toca."""
	if not company or not frappe.db.exists("Company", company):
		return False
	if not frappe.db.has_column("Company", COMPANY_PGC_FIELDNAME):
		return False
	country, pgc = frappe.db.get_value("Company", company, ["country", COMPANY_PGC_FIELDNAME])
	return country == "Spain" or bool(pgc)


def validar_factura(doc, method=None):
	if not aplica_registro_fiscal(doc.company) or doc.docstatus == 2:
		return
	copiar_clasificacion(doc)
	if not cint(frappe.db.get_value("Company", doc.company, "exigir_clasificacion_fiscal")):
		return
	for tax in doc.get("taxes") or []:
		if not _es_fila_fiscal(tax):
			continue
		for parte in _desglose(doc, tax):
			if _incompleta(doc, tax, parte):
				frappe.throw(
					_(
						"El impuesto {0} de la factura no tiene clasificación fiscal completa "
						"(tipo, clave y, en compras, deducibilidad). Complétala en la factura o "
						"en su plantilla, o desactiva «Exigir clasificación fiscal» en la compañía {1}."
					).format(
						frappe.bold(tax.get("description") or tax.get("account_head")),
						frappe.bold(doc.company),
					)
				)


def on_submit(doc, method=None):
	sincronizar(doc, avisar=True)


def on_cancel(doc, method=None):
	anular(doc.doctype, doc.name)


def copiar_clasificacion(doc):
	"""Rellena las filas vacías con la plantilla de impuestos. No pisa lo ya informado."""
	plantilla = doc.get("taxes_and_charges")
	if not plantilla:
		return
	doctype = _PLANTILLA.get(doc.doctype)
	if not doctype or not frappe.db.exists(doctype, plantilla):
		return

	usadas: set[int] = set()
	origen = frappe.get_cached_doc(doctype, plantilla).taxes
	for tax in doc.get("taxes") or []:
		for indice, fila in enumerate(origen):
			if indice in usadas:
				continue
			if fila.account_head != tax.account_head or flt(fila.rate) != flt(tax.rate):
				continue
			for campo in TAX_CLASSIFICATION_FIELDS:
				if not tax.get(campo) and fila.get(campo):
					tax.set(campo, fila.get(campo))
			usadas.add(indice)
			break


def sincronizar(doc, avisar: bool = False) -> list[str]:
	"""Sustituye las filas vigentes de la factura por el desglose actual. Devuelve sus nombres."""
	if not aplica_registro_fiscal(doc.company) or doc.docstatus != 1:
		return []

	copiar_clasificacion(doc)
	_borrar_vigentes(doc.doctype, doc.name)
	nombres = []
	pendientes = 0
	for datos in construir_filas(doc):
		registro = frappe.get_doc({"doctype": "Registro Fiscal IVA", **datos})
		registro.insert(ignore_permissions=True)
		nombres.append(registro.name)
		pendientes += cint(registro.sin_clasificar)

	if avisar and pendientes:
		frappe.msgprint(
			_(
				"La factura {0} tiene {1} línea(s) de impuesto sin clasificación fiscal. "
				"El registro de IVA queda pendiente de clasificar."
			).format(frappe.bold(doc.name), pendientes),
			indicator="orange",
			alert=True,
			title=_("Registro fiscal de IVA"),
		)
	return nombres


def anular(voucher_type: str, voucher_no: str):
	for nombre in frappe.get_all(
		"Registro Fiscal IVA",
		filters={"voucher_type": voucher_type, "voucher_no": voucher_no, "anulado": 0},
		pluck="name",
	):
		frappe.db.set_value("Registro Fiscal IVA", nombre, "anulado", 1)


def construir_filas(doc) -> list[dict]:
	cabecera = _cabecera(doc)
	compania = _datos_compania(doc.company)
	filas = []
	for tax in doc.get("taxes") or []:
		if not _es_fila_fiscal(tax):
			continue
		for parte in _desglose(doc, tax):
			filas.append(_fila(doc, tax, parte, cabecera, compania))
	return filas


# Reconstrucción -----------------------------------------------------------


def _check_permiso(company: str):
	if not frappe.has_permission("Company", "write", doc=company):
		frappe.throw(
			_("No tienes permiso para modificar la compañía {0}").format(company), frappe.PermissionError
		)
	if not set(frappe.get_roles()) & {"Accounts Manager", "System Manager", "Administrator"}:
		frappe.throw(_("Solo un gestor de cuentas puede reconstruir el registro fiscal"), frappe.PermissionError)


@frappe.whitelist()
def reconstruir_registro_fiscal(company: str, dry_run: int | str = 1):
	"""Vista previa (dry_run=1) o reconstrucción en segundo plano del registro de una compañía."""
	_check_permiso(company)
	if not aplica_registro_fiscal(company):
		frappe.throw(
			_("El registro fiscal solo se genera en compañías de España o con el Plan General Contable activo.")
		)

	if cint(dry_run):
		return reconstruir(company, dry_run=True)

	frappe.enqueue(
		_reconstruir_job,
		queue="long",
		timeout=3600,
		job_name=f"spain_compliance_registro_fiscal_{company}",
		company=company,
		user=frappe.session.user,
	)
	return {"queued": True}


def reconstruir(company: str, dry_run: bool = True) -> dict:
	resumen = {"dry_run": dry_run, "facturas": 0, "filas": 0, "sin_clasificar": 0, "anuladas": 0, "errores": 0}
	for doctype in DOCTYPES_FACTURA:
		nombres = frappe.get_all(
			doctype,
			filters={"company": company, "docstatus": ["in", [1, 2]]},
			pluck="name",
			order_by="posting_date asc, name asc",
		)
		for nombre in nombres:
			try:
				doc = frappe.get_doc(doctype, nombre)
				if doc.docstatus == 2:
					resumen["anuladas"] += 1
					if not dry_run:
						anular(doctype, nombre)
					continue
				copiar_clasificacion(doc)
				filas = construir_filas(doc)
				resumen["facturas"] += 1
				resumen["filas"] += len(filas)
				resumen["sin_clasificar"] += sum(1 for fila in filas if fila["sin_clasificar"])
				if not dry_run:
					sincronizar(doc, avisar=False)
			except Exception:
				resumen["errores"] += 1
				frappe.log_error(title=f"Spain Compliance: registro fiscal {doctype} {nombre}")
	return resumen


def _reconstruir_job(company: str, user: str):
	try:
		resumen = reconstruir(company, dry_run=False)
	except Exception:
		frappe.log_error(title=f"Spain Compliance: reconstrucción de registro fiscal fallida ({company})")
		frappe.publish_realtime(
			"msgprint",
			{
				"message": _("La reconstrucción del registro fiscal de {0} ha fallado. Revisa el Error Log.").format(
					company
				),
				"indicator": "red",
				"title": _("Registro fiscal de IVA"),
			},
			user=user,
		)
		raise

	frappe.publish_realtime(
		"msgprint",
		{
			"message": _(
				"Registro fiscal de {0} reconstruido. Facturas: {1} · Filas: {2} · "
				"Pendientes de clasificar: {3} · Anuladas: {4} · Errores: {5}"
			).format(
				frappe.bold(company),
				resumen["facturas"],
				resumen["filas"],
				resumen["sin_clasificar"],
				resumen["anuladas"],
				resumen["errores"],
			),
			"indicator": "green" if not resumen["errores"] else "orange",
			"title": _("Registro fiscal de IVA"),
		},
		user=user,
	)
	return resumen


# Desglose -----------------------------------------------------------------


def _es_fila_fiscal(tax) -> bool:
	if tax.get("tipo_impuesto"):
		return True
	if (tax.get("charge_type") or "") == "Actual":
		return False
	cuenta = tax.get("account_head")
	if not cuenta:
		return False
	return frappe.get_cached_value("Account", cuenta, "account_type") == "Tax"


def _desglose(doc, tax) -> list[dict]:
	"""Una entrada por clave y tipo. La clave del ítem, si la tiene, manda sobre la de la fila."""
	detalle = _detalle(tax)
	items: dict[str, list] = {}
	for item in doc.get("items") or []:
		items.setdefault(item.item_code or item.item_name, []).append(item)

	if not detalle:
		cuota = flt(tax.base_tax_amount if tax.get("base_tax_amount") is not None else tax.tax_amount)
		tasa = flt(tax.rate)
		neto = flt(doc.base_net_total)
		return [
			{
				"rate": tasa,
				"cuota": flt(cuota, 2),
				"base": _base(tasa, cuota, neto),
				"clave": tax.get("clave_iva"),
			}
		]

	grupos: dict[tuple, dict] = {}
	for clave_item, valor in detalle.items():
		if isinstance(valor, (list, tuple)) and len(valor) >= 2:
			tasa, cuota = flt(valor[0]), flt(valor[1])
		else:
			tasa, cuota = flt(tax.rate), flt(valor)
		filas_item = items.get(clave_item) or []
		neto = sum(flt(fila.get("base_net_amount") or fila.get("net_amount")) for fila in filas_item)
		clave = _clave_items(filas_item) or tax.get("clave_iva")
		grupo = grupos.setdefault(
			(clave or "", tasa),
			{"rate": tasa, "cuota": 0.0, "base": 0.0, "clave": clave},
		)
		grupo["cuota"] += cuota
		grupo["base"] += _base(tasa, cuota, neto)

	for grupo in grupos.values():
		grupo["cuota"] = flt(grupo["cuota"], 2)
		grupo["base"] = flt(grupo["base"], 2)
	return list(grupos.values())


def _detalle(tax) -> dict:
	detalle = tax.get("item_wise_tax_detail")
	if isinstance(detalle, str):
		if not detalle:
			return {}
		try:
			detalle = json.loads(detalle)
		except ValueError:
			return {}
	return detalle if isinstance(detalle, dict) else {}


def _clave_items(filas_item) -> str | None:
	claves = set()
	for item in filas_item:
		plantilla = item.get("item_tax_template")
		if not plantilla:
			continue
		clave = frappe.db.get_value("Item Tax Template", plantilla, "clave_iva")
		if clave:
			claves.add(clave)
	if len(claves) == 1:
		return claves.pop()
	return None


def _base(tasa: float, cuota: float, neto: float) -> float:
	if tasa:
		return flt(cuota * 100.0 / tasa, 2)
	return flt(neto, 2)


def _incompleta(doc, tax, parte) -> bool:
	tipo = tax.get("tipo_impuesto")
	if not tipo:
		return True
	if tipo in TIPOS_IVA and not parte.get("clave"):
		return True
	if tipo == TIPO_RETENCION and not tax.get("clave_retencion"):
		return True
	return doc.doctype == "Purchase Invoice" and tipo in TIPOS_IVA and not tax.get("deducible_iva")


def _fila(doc, tax, parte, cabecera, compania) -> dict:
	tipo = tax.get("tipo_impuesto") or ""
	es_iva = tipo in TIPOS_IVA
	es_retencion = tipo == TIPO_RETENCION
	cuota = parte["cuota"]
	fila = {
		**cabecera,
		"tax_row": tax.get("name"),
		"tipo_impuesto": tipo,
		"clave_iva": parte.get("clave") if es_iva or not tipo else None,
		"deducible_iva": tax.get("deducible_iva") if es_iva else None,
		"clave_retencion": tax.get("clave_retencion") if es_retencion else None,
		"base_imponible": parte["base"],
		"tipo_impositivo": parte["rate"],
		"cuota": cuota,
		"cuota_deducible": _cuota_deducible(doc, tipo, tax.get("deducible_iva"), cuota, compania),
		"sin_clasificar": 1 if _incompleta(doc, tax, parte) else 0,
	}
	return fila


def _cuota_deducible(doc, tipo, deducible, cuota, compania) -> float:
	if doc.doctype != "Purchase Invoice" or tipo not in TIPOS_IVA:
		return 0
	if deducible == DEDUCIBLE_NO:
		return 0
	if deducible == DEDUCIBLE_BIEN:
		return cuota
	prorrata = compania.prorrata_general
	if prorrata is None:
		prorrata = 100
	return flt(cuota * flt(prorrata) / 100.0, 2)


def _datos_compania(company: str):
	return frappe.db.get_value(
		"Company", company, ["prorrata_general", "default_currency"], as_dict=True
	) or frappe._dict(prorrata_general=100, default_currency="EUR")


def _cabecera(doc) -> dict:
	fecha = getdate(doc.posting_date)
	venta = doc.doctype == "Sales Invoice"
	party_type = "Customer" if venta else "Supplier"
	party = doc.customer if venta else doc.supplier
	tax_id, tipo_id = (None, None)
	if party and frappe.db.exists(party_type, party):
		tax_id, tipo_id = frappe.db.get_value(party_type, party, ["tax_id", "tipo_identificacion_fiscal"]) or (
			None,
			None,
		)
	nif = normalizar_identificador(tax_id)
	rectificativa = cint(doc.get("is_return"))
	return {
		"company": doc.company,
		"libro": LIBRO_EXPEDIDAS if venta else LIBRO_RECIBIDAS,
		"voucher_type": doc.doctype,
		"voucher_no": doc.name,
		"fecha": fecha,
		"fecha_operacion": fecha,
		"fecha_expedicion": getdate(doc.bill_date) if not venta and doc.get("bill_date") else fecha,
		"ejercicio": str(fecha.year),
		"periodo_trimestre": f"{(fecha.month - 1) // 3 + 1}T",
		"periodo_mes": f"{fecha.month:02d}",
		"party_type": party_type,
		"party": party,
		"party_name": doc.customer_name if venta else doc.supplier_name,
		"tipo_identificacion": tipo_id,
		"nif": nif,
		"pais": _pais(party_type, party, tipo_id, nif),
		"tipo_factura": "R1" if rectificativa else "F1",
		"serie": doc.get("naming_series"),
		"numero": doc.name,
		"numero_externo": doc.get("bill_no") if not venta else None,
		"factura_rectificada": doc.get("return_against") if rectificativa else None,
		"total_factura": flt(doc.base_grand_total),
		"currency": frappe.get_cached_value("Company", doc.company, "default_currency") or "EUR",
		"anulado": 0,
	}


def _pais(party_type: str, party: str | None, tipo_id: str | None, nif: str) -> str | None:
	if tipo_id == "NIF" or (nif and nif_espanol_valido(nif)):
		return "ES"
	if tipo_id == "NIF-IVA" and len(nif) >= 2 and nif[:2].isalpha():
		return nif[:2]
	if not party:
		return None
	direccion = frappe.db.get_value(
		"Dynamic Link",
		{"link_doctype": party_type, "link_name": party, "parenttype": "Address"},
		"parent",
	)
	if not direccion:
		return None
	pais = frappe.db.get_value("Address", direccion, "country")
	if not pais:
		return None
	return frappe.db.get_value("Country", pais, "code")


def _borrar_vigentes(voucher_type: str, voucher_no: str):
	for nombre in frappe.get_all(
		"Registro Fiscal IVA",
		filters={"voucher_type": voucher_type, "voucher_no": voucher_no, "anulado": 0},
		pluck="name",
	):
		frappe.delete_doc("Registro Fiscal IVA", nombre, ignore_permissions=True, force=True)
