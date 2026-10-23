# Copyright (c) 2026, Xappiens and contributors
# License: MIT

"""Registro fiscal de IVA al validar facturas de una compañía española."""

import frappe
from erpnext.accounts.doctype.sales_invoice.sales_invoice import make_sales_return
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, nowdate

from spain_compliance.contabilidad.clasificacion import (
	CLAVE_RETENCION_PROFESIONAL,
	CLAVE_SUJETA,
	DEDUCIBLE_CORRIENTE,
	TIPO_IVA,
	TIPO_RETENCION,
	etiqueta,
)
from spain_compliance.contabilidad.registro_fiscal import reconstruir, sincronizar

COMPANY = "_Test SC Fiscal"
ABBR = "_TSCF"
CUSTOMER = "_Test SC Fiscal Cliente"
SUPPLIER = "_Test SC Fiscal Proveedor"
ITEM = "_Test SC Fiscal Item"
ITEM_GROUP = "_Test SC Fiscal Items"
CUSTOMER_GROUP = "_Test SC Fiscal Clientes"
SUPPLIER_GROUP = "_Test SC Fiscal Proveedores"
CLAVE_EXENTA = etiqueta("E6", "Exenta otros")


def _grupo(doctype, name, field, parent):
	if not frappe.db.exists(doctype, name):
		frappe.get_doc({"doctype": doctype, field: name, "parent_" + frappe.scrub(doctype): parent}).insert()


def _registros(voucher_no):
	return frappe.get_all(
		"Registro Fiscal IVA",
		filters={"voucher_no": voucher_no, "anulado": 0},
		fields=[
			"name",
			"libro",
			"base_imponible",
			"tipo_impositivo",
			"cuota",
			"cuota_deducible",
			"clave_iva",
			"clave_retencion",
			"tipo_impuesto",
			"sin_clasificar",
			"tipo_factura",
			"factura_rectificada",
			"numero_externo",
			"nif",
			"pais",
			"anulado",
		],
	)


class TestRegistroFiscal(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		today = frappe.utils.getdate(nowdate())
		if not frappe.db.sql(
			"SELECT name FROM `tabFiscal Year` WHERE %s BETWEEN year_start_date AND year_end_date", today
		):
			frappe.get_doc(
				{
					"doctype": "Fiscal Year",
					"year": str(today.year),
					"year_start_date": f"{today.year}-01-01",
					"year_end_date": f"{today.year}-12-31",
				}
			).insert()

		_grupo("Customer Group", CUSTOMER_GROUP, "customer_group_name", "All Customer Groups")
		_grupo("Supplier Group", SUPPLIER_GROUP, "supplier_group_name", "All Supplier Groups")
		_grupo("Item Group", ITEM_GROUP, "item_group_name", "All Item Groups")

		if not frappe.db.exists("Company", COMPANY):
			frappe.get_doc(
				{
					"doctype": "Company",
					"company_name": COMPANY,
					"abbr": ABBR,
					"default_currency": "EUR",
					"country": "Spain",
					"chart_of_accounts": "Standard",
				}
			).insert()

		if not frappe.db.exists("Customer", CUSTOMER):
			frappe.get_doc(
				{
					"doctype": "Customer",
					"customer_name": CUSTOMER,
					"customer_type": "Company",
					"customer_group": CUSTOMER_GROUP,
					"tax_id": "B12345674",
					"tipo_identificacion_fiscal": "NIF",
				}
			).insert()

		if not frappe.db.exists("Supplier", SUPPLIER):
			frappe.get_doc(
				{
					"doctype": "Supplier",
					"supplier_name": SUPPLIER,
					"supplier_group": SUPPLIER_GROUP,
					"tax_id": "ESB12345674",
					"tipo_identificacion_fiscal": "NIF-IVA",
				}
			).insert()

		if not frappe.db.exists("Item", ITEM):
			frappe.get_doc(
				{
					"doctype": "Item",
					"item_code": ITEM,
					"item_group": ITEM_GROUP,
					"stock_uom": "Nos",
					"is_stock_item": 0,
				}
			).insert()

		cls.cost_center = frappe.db.get_value("Company", COMPANY, "cost_center")
		cls.tax_account = frappe.db.get_value(
			"Account", {"company": COMPANY, "account_name": "IVA test fiscal"}
		)
		if not cls.tax_account:
			padre = frappe.db.get_value(
				"Account", {"company": COMPANY, "is_group": 1, "root_type": "Liability"}, "name"
			)
			cls.tax_account = (
				frappe.get_doc(
					{
						"doctype": "Account",
						"company": COMPANY,
						"account_name": "IVA test fiscal",
						"parent_account": padre,
						"is_group": 0,
						"account_type": "Tax",
						"root_type": "Liability",
					}
				)
				.insert()
				.name
			)

	def setUp(self):
		# La clase comparte transacción: cada test deja la compañía como estaba.
		frappe.db.set_value(
			"Company",
			COMPANY,
			{
				"country": "Spain",
				"pgc_espanol": 0,
				"exigir_clasificacion_fiscal": 0,
				"prorrata_general": 100,
			},
		)

	def _impuesto(self, **kwargs):
		fila = {
			"charge_type": "On Net Total",
			"account_head": self.tax_account,
			"description": "Impuesto",
			"rate": 21,
			"cost_center": self.cost_center,
		}
		fila.update(kwargs)
		return fila

	def _venta(self, taxes, **kwargs):
		inv = frappe.get_doc(
			{
				"doctype": "Sales Invoice",
				"company": COMPANY,
				"customer": CUSTOMER,
				"naming_series": "SCRF-.YYYY.-",
				"posting_date": nowdate(),
				"due_date": add_days(nowdate(), 15),
				"currency": "EUR",
				"items": [{"item_code": ITEM, "qty": 1, "rate": 100}],
				**kwargs,
			}
		)
		inv.set_missing_values()
		for tax in taxes:
			inv.append("taxes", tax)
		return inv.insert()

	def _compra(self, taxes, rate=200, **kwargs):
		inv = frappe.get_doc(
			{
				"doctype": "Purchase Invoice",
				"company": COMPANY,
				"supplier": SUPPLIER,
				"bill_no": frappe.generate_hash(length=8),
				"bill_date": nowdate(),
				"posting_date": nowdate(),
				"currency": "EUR",
				"items": [{"item_code": ITEM, "qty": 1, "rate": rate}],
				**kwargs,
			}
		)
		inv.set_missing_values()
		for tax in taxes:
			inv.append("taxes", tax)
		return inv.insert()

	def test_venta_21_crea_una_fila(self):
		inv = self._venta([self._impuesto(tipo_impuesto=TIPO_IVA, clave_iva=CLAVE_SUJETA)])
		inv.submit()
		filas = _registros(inv.name)
		self.assertEqual(len(filas), 1)
		fila = filas[0]
		self.assertEqual(fila.libro, "Expedidas")
		self.assertEqual(fila.base_imponible, 100)
		self.assertEqual(fila.tipo_impositivo, 21)
		self.assertEqual(fila.cuota, 21)
		self.assertEqual(fila.clave_iva, CLAVE_SUJETA)
		self.assertEqual(fila.sin_clasificar, 0)
		self.assertEqual(fila.tipo_factura, "F1")
		self.assertEqual(fila.nif, "B12345674")
		self.assertEqual(fila.pais, "ES")

	def test_sin_clasificar_no_bloquea(self):
		inv = self._venta([self._impuesto()])
		inv.submit()
		filas = _registros(inv.name)
		self.assertEqual(len(filas), 1)
		self.assertEqual(filas[0].sin_clasificar, 1)
		self.assertEqual(filas[0].cuota, 21)

	def test_exigir_clasificacion_bloquea(self):
		frappe.db.set_value("Company", COMPANY, "exigir_clasificacion_fiscal", 1)
		nueva = frappe.get_doc(
			{
				"doctype": "Sales Invoice",
				"company": COMPANY,
				"customer": CUSTOMER,
				"naming_series": "SCRF-.YYYY.-",
				"posting_date": nowdate(),
				"due_date": add_days(nowdate(), 15),
				"currency": "EUR",
				"items": [{"item_code": ITEM, "qty": 1, "rate": 100}],
			}
		)
		nueva.set_missing_values()
		nueva.append("taxes", self._impuesto())
		with self.assertRaises(frappe.ValidationError):
			nueva.insert()

	def test_compra_prorrata_y_retencion(self):
		frappe.db.set_value("Company", COMPANY, "prorrata_general", 50)
		inv = self._compra(
			[
				self._impuesto(
					tipo_impuesto=TIPO_IVA,
					clave_iva=CLAVE_SUJETA,
					deducible_iva=DEDUCIBLE_CORRIENTE,
					description="IVA",
				),
				self._impuesto(
					rate=15,
					description="IRPF",
					tipo_impuesto=TIPO_RETENCION,
					clave_retencion=CLAVE_RETENCION_PROFESIONAL,
					add_deduct_tax="Deduct",
				),
			]
		)
		inv.submit()
		filas = {fila.tipo_impuesto: fila for fila in _registros(inv.name)}
		self.assertEqual(set(filas), {TIPO_IVA, TIPO_RETENCION})
		self.assertEqual(filas[TIPO_IVA].libro, "Recibidas")
		self.assertEqual(filas[TIPO_IVA].base_imponible, 200)
		self.assertEqual(filas[TIPO_IVA].cuota, 42)
		self.assertEqual(filas[TIPO_IVA].cuota_deducible, 21)
		self.assertEqual(filas[TIPO_RETENCION].cuota, 30)
		self.assertEqual(filas[TIPO_RETENCION].clave_retencion, CLAVE_RETENCION_PROFESIONAL)
		self.assertEqual(filas[TIPO_RETENCION].cuota_deducible, 0)
		self.assertEqual(filas[TIPO_IVA].numero_externo, inv.bill_no)
		self.assertEqual(filas[TIPO_IVA].pais, "ES")

	def test_rectificativa_en_negativo(self):
		inv = self._venta([self._impuesto(tipo_impuesto=TIPO_IVA, clave_iva=CLAVE_SUJETA)])
		inv.submit()
		abono = make_sales_return(inv.name)
		abono.insert()
		abono.submit()
		filas = _registros(abono.name)
		self.assertEqual(len(filas), 1)
		self.assertEqual(filas[0].tipo_factura, "R1")
		self.assertEqual(filas[0].factura_rectificada, inv.name)
		self.assertEqual(filas[0].base_imponible, -100)
		self.assertEqual(filas[0].cuota, -21)

	def test_cancelar_anula_el_registro(self):
		inv = self._venta([self._impuesto(tipo_impuesto=TIPO_IVA, clave_iva=CLAVE_SUJETA)])
		inv.submit()
		self.assertEqual(len(_registros(inv.name)), 1)
		inv.cancel()
		self.assertEqual(_registros(inv.name), [])
		self.assertTrue(
			frappe.db.get_value(
				"Registro Fiscal IVA", {"voucher_no": inv.name}, "anulado"
			)
		)

	def test_copia_de_la_plantilla_y_reconstruccion(self):
		plantilla = frappe.get_doc(
			{
				"doctype": "Sales Taxes and Charges Template",
				"title": f"_Test SC IVA {frappe.generate_hash(length=6)}",
				"company": COMPANY,
				"taxes": [
					self._impuesto(tipo_impuesto=TIPO_IVA, clave_iva=CLAVE_SUJETA, description="IVA 21")
				],
			}
		).insert()
		# La fila entra vacía; al validar se copia de la plantilla. No se deja que
		# set_missing_values añada la plantilla y luego añadamos otra fila.
		inv = frappe.get_doc(
			{
				"doctype": "Sales Invoice",
				"company": COMPANY,
				"customer": CUSTOMER,
				"naming_series": "SCRF-.YYYY.-",
				"posting_date": nowdate(),
				"due_date": add_days(nowdate(), 15),
				"currency": "EUR",
				"items": [{"item_code": ITEM, "qty": 1, "rate": 100}],
			}
		)
		inv.set_missing_values()
		inv.append("taxes", self._impuesto())
		inv.taxes_and_charges = plantilla.name
		inv.insert()
		self.assertEqual(len(inv.taxes), 1)
		self.assertEqual(inv.taxes[0].clave_iva, CLAVE_SUJETA)
		inv.submit()

		frappe.db.set_value("Sales Taxes and Charges", inv.taxes[0].name, "clave_iva", None)
		frappe.db.set_value("Sales Taxes and Charges", inv.taxes[0].name, "tipo_impuesto", None)
		for nombre in frappe.get_all("Registro Fiscal IVA", filters={"voucher_no": inv.name}, pluck="name"):
			frappe.delete_doc("Registro Fiscal IVA", nombre, force=True)

		previa = reconstruir(COMPANY, dry_run=True)
		self.assertGreaterEqual(previa["filas"], 1)
		self.assertEqual(frappe.db.count("Registro Fiscal IVA", {"voucher_no": inv.name}), 0)

		reconstruir(COMPANY, dry_run=False)
		filas = _registros(inv.name)
		self.assertEqual(filas[0].clave_iva, CLAVE_SUJETA)
		self.assertEqual(filas[0].sin_clasificar, 0)
		sincronizar(inv)
		self.assertEqual(len(_registros(inv.name)), 1)

	def test_clave_del_articulo_sustituye_a_la_fila(self):
		plantilla_item = frappe.get_doc(
			{
				"doctype": "Item Tax Template",
				"title": f"_Test SC Exento {frappe.generate_hash(length=6)}",
				"company": COMPANY,
				"clave_iva": CLAVE_EXENTA,
				"taxes": [{"tax_type": self.tax_account, "tax_rate": 0}],
			}
		).insert()
		inv = self._venta(
			[self._impuesto(tipo_impuesto=TIPO_IVA, clave_iva=CLAVE_SUJETA)],
			items=[{"item_code": ITEM, "qty": 1, "rate": 100, "item_tax_template": plantilla_item.name}],
		)
		inv.submit()
		filas = _registros(inv.name)
		self.assertEqual(len(filas), 1)
		self.assertEqual(filas[0].clave_iva, CLAVE_EXENTA)
		self.assertEqual(filas[0].tipo_impositivo, 0)
		self.assertEqual(filas[0].base_imponible, 100)
		self.assertEqual(filas[0].cuota, 0)

	def test_fuera_de_espana_no_registra(self):
		frappe.db.set_value("Company", COMPANY, {"country": "France", "pgc_espanol": 0})
		inv = self._venta([self._impuesto(tipo_impuesto=TIPO_IVA, clave_iva=CLAVE_SUJETA)])
		inv.submit()
		self.assertFalse(frappe.db.exists("Registro Fiscal IVA", {"voucher_no": inv.name}))

	def test_cargo_que_no_es_impuesto_no_genera_fila(self):
		ingreso = frappe.db.get_value("Company", COMPANY, "default_income_account")
		inv = self._venta(
			[
				self._impuesto(tipo_impuesto=TIPO_IVA, clave_iva=CLAVE_SUJETA),
				{
					"charge_type": "Actual",
					"account_head": ingreso,
					"description": "Portes",
					"tax_amount": 10,
					"cost_center": self.cost_center,
				},
			]
		)
		inv.submit()
		self.assertEqual(len(_registros(inv.name)), 1)
