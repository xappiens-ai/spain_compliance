# Copyright (c) 2026, Xappiens and contributors
# License: MIT

"""Informes del portal: libro de IVA, liquidación y estados contables."""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import getdate, nowdate

from spain_compliance.api.informes import (
	ajustes,
	libro_iva,
	libro_mayor,
	liquidacion_iva,
	perdidas_y_ganancias,
	plan_cuentas,
	sumas_y_saldos,
)

COMPANY = "_Test SC Informes"
ABBR = "_TSCI"


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


def _company():
	if frappe.db.exists("Company", COMPANY):
		return
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


def _registro(**kwargs):
	today = getdate(nowdate())
	trimestre = f"{((today.month - 1) // 3) + 1}T"
	doc = frappe.get_doc(
		{
			"doctype": "Registro Fiscal IVA",
			"naming_series": "RF-.YYYY.-",
			"company": COMPANY,
			"fecha": today,
			"ejercicio": str(today.year),
			"periodo_trimestre": trimestre,
			"periodo_mes": f"{today.month:02d}",
			"voucher_type": "Sales Invoice",
			"voucher_no": "SI-TEST-INFORMES",
			"numero": "1",
			"party_name": "Tercero informes",
			"nif": "B00000000",
			"currency": "EUR",
			**kwargs,
		}
	)
	doc.flags.ignore_links = True
	return doc.insert()


class TestInformes(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		_fiscal_year()
		_company()

	def setUp(self):
		super().setUp()
		frappe.db.delete("Registro Fiscal IVA", {"company": COMPANY})

	def test_libro_y_liquidacion(self):
		today = nowdate()
		_registro(
			libro="Expedidas",
			voucher_no="SI-TEST-INFORMES-E",
			base_imponible=100,
			tipo_impositivo=21,
			cuota=21,
			cuota_deducible=0,
			clave_iva="S1",
			tipo_impuesto="IVA",
		)
		_registro(
			libro="Recibidas",
			voucher_type="Purchase Invoice",
			voucher_no="PI-TEST-INFORMES-R",
			numero="F-9",
			base_imponible=50,
			tipo_impositivo=21,
			cuota=10.5,
			cuota_deducible=10,
			clave_iva="S1",
			tipo_impuesto="IVA",
		)
		_registro(
			libro="Expedidas",
			voucher_no="SI-TEST-INFORMES-X",
			anulado=1,
			base_imponible=999,
			cuota=999,
		)

		libro = libro_iva(COMPANY, f"{getdate(today).year}-01-01", today, "Expedidas")
		self.assertEqual(libro["totals"]["filas"], 1)
		self.assertEqual(libro["totals"]["base"], 100)
		self.assertEqual(libro["totals"]["cuota"], 21)
		self.assertEqual(libro["rows"][0]["nif"], "B00000000")
		self.assertFalse(libro["rows"][0]["anulado"])

		liquidacion = liquidacion_iva(COMPANY, f"{getdate(today).year}-01-01", today)
		self.assertEqual(liquidacion["repercutido"]["cuota"], 21)
		self.assertEqual(liquidacion["soportado"]["deducible"], 10)
		self.assertEqual(liquidacion["resultado"], 11)
		self.assertTrue(liquidacion["a_ingresar"])

	def test_libro_excluye_retencion_y_otro(self):
		today = nowdate()
		inicio = f"{getdate(today).year}-01-01"
		_registro(
			libro="Expedidas",
			voucher_no="SI-TEST-INFORMES-IVA",
			base_imponible=100,
			cuota=21,
			tipo_impuesto="IVA",
			clave_iva="S1",
		)
		_registro(
			libro="Expedidas",
			voucher_no="SI-TEST-INFORMES-IRPF",
			base_imponible=100,
			tipo_impositivo=15,
			cuota=15,
			tipo_impuesto="Retención IRPF",
		)
		_registro(
			libro="Expedidas",
			voucher_no="SI-TEST-INFORMES-OTRO",
			base_imponible=40,
			cuota=40,
			tipo_impuesto="Otro",
		)
		_registro(
			libro="Recibidas",
			voucher_type="Purchase Invoice",
			voucher_no="PI-TEST-INFORMES-IGIC",
			base_imponible=100,
			tipo_impositivo=7,
			cuota=7,
			cuota_deducible=7,
			tipo_impuesto="IGIC",
			clave_iva="S1",
		)

		libro = libro_iva(COMPANY, inicio, today, "Expedidas")
		self.assertEqual(libro["totals"]["filas"], 1)
		self.assertEqual(libro["totals"]["base"], 100)
		self.assertEqual(libro["totals"]["cuota"], 21)
		self.assertEqual([row["tipo_impuesto"] for row in libro["rows"]], ["IVA"])

		liquidacion = liquidacion_iva(COMPANY, inicio, today)
		self.assertEqual(liquidacion["repercutido"]["cuota"], 21)
		self.assertEqual(liquidacion["repercutido"]["filas"], 1)
		self.assertEqual(liquidacion["soportado"]["cuota"], 7)
		self.assertEqual(liquidacion["soportado"]["deducible"], 7)
		self.assertEqual(liquidacion["resultado"], 14)

	def test_estados_y_plan(self):
		from erpnext.accounts.utils import get_fiscal_year

		_nombre, fy_inicio, fy_fin = get_fiscal_year(nowdate(), company=COMPANY, verbose=0)
		inicio = str(getdate(fy_inicio))
		fin = str(min(getdate(nowdate()), getdate(fy_fin)))
		pyg = perdidas_y_ganancias(COMPANY, inicio, fin)
		self.assertEqual(pyg["company"], COMPANY)
		self.assertEqual(pyg["currency"], "EUR")
		self.assertIn("rows", pyg)
		self.assertIn("columns", pyg)

		mayor = libro_mayor(COMPANY, inicio, fin)
		self.assertEqual(mayor["rows"], [])
		self.assertEqual(mayor["opening_balance"], None)

		sumas = sumas_y_saldos(COMPANY, inicio, fin)
		self.assertTrue(sumas["fiscal_year"])
		self.assertIn("columns", sumas)

		plan = plan_cuentas(COMPANY)
		self.assertGreater(len(plan["accounts"]), 0)
		self.assertIn("indent", plan["accounts"][0])

		config = ajustes(COMPANY)
		self.assertEqual(config["abbr"], ABBR)
		tipos = {field["fieldname"]: field["fieldtype"] for field in config["fields"]}
		self.assertEqual(tipos["regimen_iva"], "Select")
		self.assertEqual(tipos["periodicidad_modelo_303"], "Select")
		self.assertEqual(tipos["modelo_cuentas_anuales"], "Select")
		self.assertEqual(tipos["prorrata_general"], "Percent")
		self.assertEqual(tipos["pgc_espanol"], "Check")

	def test_invitado_no_entra(self):
		frappe.set_user("Guest")
		try:
			self.assertRaises(frappe.PermissionError, ajustes, COMPANY)
		finally:
			frappe.set_user("Administrator")
