# Copyright (c) 2026, Xappiens and contributors
# License: MIT

import frappe
from erpnext.accounts.party import get_party_account
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, getdate, nowdate

from spain_compliance.contabilidad import cuentas_tercero
from spain_compliance.contabilidad.cuentas_tercero import ConfigError
from spain_compliance.contabilidad.plan_contable import _crear_grupo, instalar_arbol_pgc

COMPANY = "_Test SC PGC"
ABBR = "_TSCP"
OTHER_COMPANY = "_Test SC No PGC"
OTHER_ABBR = "_TSCN"
ITEM = "_Test SC Servicio"
CUSTOMER_GROUP = "_Test SC Clientes"
SUPPLIER_GROUP = "_Test SC Proveedores"
ITEM_GROUP = "_Test SC Servicios"


def _grupo(doctype, name, field, parent):
	if not frappe.db.exists(doctype, name):
		frappe.get_doc({"doctype": doctype, field: name, "parent_" + frappe.scrub(doctype): parent}).insert()


def _company(name, abbr):
	if frappe.db.exists("Company", name):
		return frappe.get_doc("Company", name)
	return frappe.get_doc(
		{
			"doctype": "Company",
			"company_name": name,
			"abbr": abbr,
			"default_currency": "EUR",
			"country": "Spain",
			"chart_of_accounts": "Standard",
		}
	).insert()


def _fiscal_year():
	today = getdate(nowdate())
	if frappe.db.sql(
		"SELECT name FROM `tabFiscal Year` WHERE %s BETWEEN year_start_date AND year_end_date", today
	):
		return
	frappe.get_doc(
		{
			"doctype": "Fiscal Year",
			"year": str(today.year),
			"year_start_date": f"{today.year}-01-01",
			"year_end_date": f"{today.year}-12-31",
		}
	).insert()


def _leaf(numero, nombre, parent, account_type, root_type):
	existente = frappe.db.get_value("Account", {"company": COMPANY, "account_number": numero})
	if existente:
		return existente
	return (
		frappe.get_doc(
			{
				"doctype": "Account",
				"company": COMPANY,
				"account_number": numero,
				"account_name": nombre,
				"parent_account": parent,
				"is_group": 0,
				"account_type": account_type,
				"root_type": root_type,
			}
		)
		.insert()
		.name
	)


def _customer(name, **kwargs):
	return frappe.get_doc(
		{
			"doctype": "Customer",
			"customer_name": name,
			"customer_type": "Company",
			"customer_group": CUSTOMER_GROUP,
			**kwargs,
		}
	).insert()


def _supplier(name, **kwargs):
	return frappe.get_doc(
		{"doctype": "Supplier", "supplier_name": name, "supplier_group": SUPPLIER_GROUP, **kwargs}
	).insert()


def _sales_invoice(customer, **kwargs):
	inv = frappe.get_doc(
		{
			"doctype": "Sales Invoice",
			"company": COMPANY,
			"customer": customer,
			"posting_date": nowdate(),
			"due_date": add_days(nowdate(), 15),
			"currency": "EUR",
			"items": [{"item_code": ITEM, "qty": 1, "rate": 100}],
			**kwargs,
		}
	)
	inv.set_missing_values()
	return inv.insert()


class TestCuentasTercero(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		_fiscal_year()
		_grupo("Customer Group", CUSTOMER_GROUP, "customer_group_name", "All Customer Groups")
		_grupo("Supplier Group", SUPPLIER_GROUP, "supplier_group_name", "All Supplier Groups")
		_grupo("Item Group", ITEM_GROUP, "item_group_name", "All Item Groups")
		_company(COMPANY, ABBR)
		_company(OTHER_COMPANY, OTHER_ABBR)

		nodos = instalar_arbol_pgc(COMPANY, {"40", "43"})
		cls.grupo_430 = _crear_grupo(COMPANY, "430", "Clientes", "Asset", nodos["43"])
		cls.grupo_435 = _crear_grupo(COMPANY, "435", "Clientes, otras cuentas", "Asset", nodos["43"])
		cls.grupo_400 = _crear_grupo(COMPANY, "400", "Proveedores", "Liability", nodos["40"])
		cls.generica_cliente = _leaf("43000000", "Clientes genérica", cls.grupo_430, "Receivable", "Asset")
		cls.generica_proveedor = _leaf(
			"40000000", "Proveedores genérica", cls.grupo_400, "Payable", "Liability"
		)
		# Ruido fuera de la secuencia: otro grupo (435) y otro bloque del mismo grupo (4009)
		_leaf("43500001", "Clientes otras", cls.grupo_435, "Receivable", "Asset")
		_leaf("40090001", "Facturas pendientes de recibir", cls.grupo_400, "Payable", "Liability")

		frappe.db.set_value(
			"Company",
			COMPANY,
			{
				"default_receivable_account": cls.generica_cliente,
				"default_payable_account": cls.generica_proveedor,
			},
		)

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

	def setUp(self):
		self._configurar(cliente=1, proveedor=1)

	def _configurar(self, cliente=1, proveedor=1, prefijo_cliente="4300", prefijo_proveedor="4000"):
		company = frappe.get_doc("Company", COMPANY)
		company.update(
			{
				"crear_cuenta_cliente_auto": cliente,
				"prefijo_cuenta_cliente": prefijo_cliente,
				"digitos_cuenta_cliente": 8,
				"crear_cuenta_proveedor_auto": proveedor,
				"prefijo_cuenta_proveedor": prefijo_proveedor,
				"digitos_cuenta_proveedor": 8,
			}
		)
		company.save()

	def _numero_siguiente_cliente(self):
		return cuentas_tercero.siguiente_numero(COMPANY, "4300", 8)

	# Configuración ---------------------------------------------------------

	def test_prefijo_no_numerico_se_rechaza(self):
		with self.assertRaises(ConfigError):
			self._configurar(prefijo_cliente="43A0")

	def test_prefijo_corto_se_rechaza(self):
		with self.assertRaises(ConfigError):
			self._configurar(prefijo_cliente="43")

	def test_digitos_insuficientes_se_rechazan(self):
		company = frappe.get_doc("Company", COMPANY)
		company.digitos_cuenta_cliente = 4
		with self.assertRaises(ConfigError):
			company.save()

	def test_grupo_padre_inexistente_se_rechaza(self):
		with self.assertRaises(ConfigError):
			self._configurar(prefijo_cliente="4390")

	def test_sin_pgc_no_hay_config(self):
		self.assertIsNone(cuentas_tercero.get_config(OTHER_COMPANY, "Customer"))

	# Alta de terceros ---------------------------------------------------------

	def test_alta_cliente_crea_cuenta_secuencial(self):
		esperado = self._numero_siguiente_cliente()
		c1 = _customer("_Test SC Cliente Uno")
		c2 = _customer("_Test SC Cliente Dos")

		cuenta1 = cuentas_tercero.cuenta_de_tercero("Customer", c1.name, COMPANY)
		cuenta2 = cuentas_tercero.cuenta_de_tercero("Customer", c2.name, COMPANY)
		self.assertEqual(frappe.db.get_value("Account", cuenta1, "account_number"), esperado)
		self.assertEqual(frappe.db.get_value("Account", cuenta2, "account_number"), str(int(esperado) + 1))

		acc = frappe.get_doc("Account", cuenta1)
		self.assertEqual(acc.parent_account, self.grupo_430)
		self.assertEqual(acc.account_type, "Receivable")
		self.assertEqual(acc.root_type, "Asset")
		self.assertEqual(acc.account_currency, "EUR")
		self.assertEqual(acc.account_name, "_Test SC Cliente Uno")
		self.assertEqual(get_party_account("Customer", c1.name, COMPANY), cuenta1)

	def test_primera_cuenta_tras_la_generica(self):
		self.assertGreater(int(self._numero_siguiente_cliente()), 43000000)

	def test_alta_sin_opcion_no_crea_cuenta(self):
		self._configurar(cliente=0)
		c = _customer("_Test SC Sin Opcion")
		self.assertIsNone(cuentas_tercero.cuenta_de_tercero("Customer", c.name, COMPANY))
		self.assertEqual(get_party_account("Customer", c.name, COMPANY), self.generica_cliente)

	def test_compania_sin_pgc_no_recibe_cuenta(self):
		c = _customer("_Test SC Solo PGC")
		self.assertIsNone(cuentas_tercero.cuenta_de_tercero("Customer", c.name, OTHER_COMPANY))

	def test_no_reutiliza_huecos(self):
		siguiente = int(self._numero_siguiente_cliente())
		_leaf(str(siguiente + 5), "Hueco manual", self.grupo_430, "Receivable", "Asset")
		c = _customer("_Test SC Tras Hueco")
		cuenta = cuentas_tercero.cuenta_de_tercero("Customer", c.name, COMPANY)
		self.assertEqual(frappe.db.get_value("Account", cuenta, "account_number"), str(siguiente + 6))

	def test_cuentas_de_otro_bloque_no_afectan(self):
		# 43500001 (grupo 435) y 40090001 (bloque 4009) quedan fuera de 4300 / 4000
		self.assertTrue(self._numero_siguiente_cliente().startswith("4300"))
		self.assertTrue(cuentas_tercero.siguiente_numero(COMPANY, "4000", 8).startswith("4000"))

	def test_idempotente(self):
		c = _customer("_Test SC Idempotente")
		primera = cuentas_tercero.cuenta_de_tercero("Customer", c.name, COMPANY)
		self.assertEqual(cuentas_tercero.crear_cuenta_tercero("Customer", c.name, COMPANY), primera)
		filas = frappe.get_all(
			"Party Account", filters={"parent": c.name, "parenttype": "Customer", "company": COMPANY}
		)
		self.assertEqual(len(filas), 1)

	def test_conserva_cuentas_de_otras_companias(self):
		otra = frappe.db.get_value(
			"Account", {"company": OTHER_COMPANY, "account_type": "Receivable", "is_group": 0}
		)
		c = _customer("_Test SC Multi", accounts=[{"company": OTHER_COMPANY, "account": otra}])
		c.reload()
		por_compania = {r.company: r.account for r in c.accounts}
		self.assertEqual(por_compania[OTHER_COMPANY], otra)
		self.assertTrue(por_compania[COMPANY].startswith("4300"))

	def test_respeta_cuenta_indicada_en_el_alta(self):
		manual = _leaf("43500099", "Cuenta manual", self.grupo_435, "Receivable", "Asset")
		c = _customer("_Test SC Manual", accounts=[{"company": COMPANY, "account": manual}])
		self.assertEqual(cuentas_tercero.cuenta_de_tercero("Customer", c.name, COMPANY), manual)

	def test_cliente_interno_de_la_propia_compania_sin_cuenta(self):
		c = _customer(
			"_Test SC Interno Propio",
			is_internal_customer=1,
			represents_company=COMPANY,
			companies=[{"company": COMPANY}],
		)
		self.assertIsNone(cuentas_tercero.cuenta_de_tercero("Customer", c.name, COMPANY))
		pendientes = cuentas_tercero.terceros_sin_cuenta("Customer", COMPANY, solo_con_movimientos=False)
		self.assertNotIn(c.name, pendientes)

	def test_cliente_interno_de_otra_compania_si_lleva_cuenta(self):
		c = _customer(
			"_Test SC Interno Otra",
			is_internal_customer=1,
			represents_company=OTHER_COMPANY,
			companies=[{"company": COMPANY}],
		)
		self.assertIsNotNone(cuentas_tercero.cuenta_de_tercero("Customer", c.name, COMPANY))

	def test_nombre_largo_se_recorta(self):
		c = _customer("_Test SC " + "X" * 131)
		cuenta = cuentas_tercero.cuenta_de_tercero("Customer", c.name, COMPANY)
		self.assertIsNotNone(cuenta)
		self.assertLessEqual(len(cuenta), 140)

	def test_moneda_del_cliente(self):
		c = _customer("_Test SC Dolares", default_currency="USD")
		cuenta = cuentas_tercero.cuenta_de_tercero("Customer", c.name, COMPANY)
		self.assertEqual(frappe.db.get_value("Account", cuenta, "account_currency"), "USD")

	def test_alta_proveedor(self):
		esperado = cuentas_tercero.siguiente_numero(COMPANY, "4000", 8)
		s = _supplier("_Test SC Proveedor")
		cuenta = cuentas_tercero.cuenta_de_tercero("Supplier", s.name, COMPANY)
		acc = frappe.get_doc("Account", cuenta)
		self.assertEqual(acc.account_number, esperado)
		self.assertEqual(acc.parent_account, self.grupo_400)
		self.assertEqual(acc.account_type, "Payable")
		self.assertEqual(acc.root_type, "Liability")

	def test_fallo_no_bloquea_el_alta(self):
		frappe.db.set_value("Company", COMPANY, "prefijo_cuenta_cliente", "4390")
		frappe.clear_document_cache("Company", COMPANY)
		try:
			c = _customer("_Test SC Sin Grupo")
			self.assertTrue(frappe.db.exists("Customer", c.name))
			self.assertIsNone(cuentas_tercero.cuenta_de_tercero("Customer", c.name, COMPANY))
		finally:
			frappe.db.set_value("Company", COMPANY, "prefijo_cuenta_cliente", "4300")
			frappe.clear_document_cache("Company", COMPANY)

	# Facturas -----------------------------------------------------------------

	def test_factura_crea_cuenta_de_tercero_existente(self):
		self._configurar(cliente=0)
		c = _customer("_Test SC Previo")
		self._configurar(cliente=1)

		inv = _sales_invoice(c.name)
		cuenta = cuentas_tercero.cuenta_de_tercero("Customer", c.name, COMPANY)
		self.assertIsNotNone(cuenta)
		self.assertEqual(inv.debit_to, cuenta)

	def test_factura_respeta_cuenta_no_generica(self):
		self._configurar(cliente=0)
		c = _customer("_Test SC Cuenta 435")
		self._configurar(cliente=1)
		otra = _leaf("43500002", "Clientes otras dos", self.grupo_435, "Receivable", "Asset")

		inv = _sales_invoice(c.name, debit_to=otra)
		self.assertEqual(inv.debit_to, otra)

	def test_factura_sin_opcion_no_toca_nada(self):
		self._configurar(cliente=0)
		c = _customer("_Test SC Factura Sin Opcion")
		inv = _sales_invoice(c.name)
		self.assertEqual(inv.debit_to, self.generica_cliente)
		self.assertIsNone(cuentas_tercero.cuenta_de_tercero("Customer", c.name, COMPANY))

	# Backfill -----------------------------------------------------------------

	def test_backfill(self):
		self._configurar(cliente=0)
		con_mov = _customer("_Test SC Backfill Con Movimientos")
		sin_mov = _customer("_Test SC Backfill Sin Movimientos")
		_sales_invoice(con_mov.name)  # borrador sin opción activa: cuenta genérica
		self._configurar(cliente=1)

		previa = cuentas_tercero.crear_cuentas_pendientes(COMPANY, "Customer", dry_run=1)
		self.assertIn(con_mov.name, previa["terceros"])
		self.assertNotIn(sin_mov.name, previa["terceros"])
		self.assertIsNone(cuentas_tercero.cuenta_de_tercero("Customer", con_mov.name, COMPANY))

		hecho = cuentas_tercero.crear_cuentas_pendientes(COMPANY, "Customer", dry_run=0)
		self.assertFalse(hecho["errores"])
		self.assertIsNotNone(cuentas_tercero.cuenta_de_tercero("Customer", con_mov.name, COMPANY))
		self.assertIsNone(cuentas_tercero.cuenta_de_tercero("Customer", sin_mov.name, COMPANY))

		todos = cuentas_tercero.crear_cuentas_pendientes(
			COMPANY, "Customer", solo_con_movimientos=0, dry_run=1
		)
		self.assertIn(sin_mov.name, todos["terceros"])

	def test_backfill_sin_opcion_falla(self):
		self._configurar(cliente=0)
		with self.assertRaises(ConfigError):
			cuentas_tercero.crear_cuentas_pendientes(COMPANY, "Customer")
