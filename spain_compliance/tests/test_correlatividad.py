# Copyright (c) 2026, Xappiens and contributors
# License: MIT

"""Correlatividad y numeración oficial al validar Sales Invoice."""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, getdate, nowdate

from spain_compliance.contabilidad.correlatividad import (
	get_counter_digits,
	series_prefix_from_name,
)
from spain_compliance.contabilidad.numeracion import (
	PROVISIONAL_NAME_PREFIX,
	is_provisional_name,
)

COMPANY = "_Test SC Correl"
ABBR = "_TSCCR"
CUSTOMER = "_Test SC Correl Cliente"
ITEM = "_Test SC Correl Item"
ITEM_GROUP = "_Test SC Correl Items"
CUSTOMER_GROUP = "_Test SC Correl Clientes"


def _ensure_masters():
	today = getdate(nowdate())
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

	for doctype, name, field, parent in (
		("Customer Group", CUSTOMER_GROUP, "customer_group_name", "All Customer Groups"),
		("Item Group", ITEM_GROUP, "item_group_name", "All Item Groups"),
	):
		if not frappe.db.exists(doctype, name):
			frappe.get_doc({"doctype": doctype, field: name, "parent_" + frappe.scrub(doctype): parent}).insert()

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


def _invoice(posting_date, series, **kwargs):
	inv = frappe.get_doc(
		{
			"doctype": "Sales Invoice",
			"company": COMPANY,
			"customer": CUSTOMER,
			"naming_series": series,
			"set_posting_time": 1,
			"posting_date": posting_date,
			"due_date": add_days(posting_date, 15),
			"currency": "EUR",
			"items": [{"item_code": ITEM, "qty": 1, "rate": 50}],
			**kwargs,
		}
	)
	inv.set_missing_values()
	return inv


class TestCorrelatividad(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		_ensure_masters()

	def _series(self, tag: str) -> str:
		return f"SCORR-{tag}-.YYYY.-"

	def test_prefix_helpers(self):
		self.assertEqual(get_counter_digits("XAP.F.YY.#####"), 5)
		self.assertEqual(get_counter_digits("{abbr}.F.YY.{#####}"), 5)
		self.assertEqual(series_prefix_from_name("XAPF2600060", 5), "XAPF26")
		self.assertEqual(series_prefix_from_name("XAPF2600016-1", 5), "XAPF26")
		self.assertIsNone(series_prefix_from_name(f"{PROVISIONAL_NAME_PREFIX}26-00001", 5))

	def test_borrador_usa_nombre_provisional_y_conserva_serie_oficial(self):
		series = self._series("DRAFT")
		inv = _invoice(nowdate(), series).insert()
		self.assertTrue(is_provisional_name(inv.name))
		self.assertEqual(inv.naming_series, series)
		# Guardar de nuevo no consume serie oficial
		inv.posting_date = nowdate()
		inv.save()
		self.assertTrue(is_provisional_name(inv.name))

	def test_validar_asigna_numero_oficial(self):
		series = self._series("SUB")
		inv = _invoice(nowdate(), series).insert()
		draft_name = inv.name
		self.assertTrue(is_provisional_name(draft_name))
		inv.submit()
		inv.reload()
		self.assertFalse(is_provisional_name(inv.name))
		self.assertNotEqual(inv.name, draft_name)
		self.assertTrue(inv.name.startswith("SCORR-SUB-"))
		self.assertEqual(inv.docstatus, 1)

	def test_fecha_futura_se_rechaza_al_validar(self):
		series = self._series("FUT")
		# Borrador con fecha futura: permitido (aún no hay número oficial)
		inv = _invoice(add_days(nowdate(), 30), series).insert()
		self.assertTrue(is_provisional_name(inv.name))
		with self.assertRaises(frappe.ValidationError):
			inv.submit()

	def test_fecha_anterior_a_factura_previa_se_rechaza_al_validar(self):
		series = self._series("ORD")
		later = add_days(nowdate(), -2)
		earlier = add_days(nowdate(), -10)
		first = _invoice(later, series).insert()
		first.submit()
		second = _invoice(earlier, series).insert()
		self.assertTrue(is_provisional_name(second.name))
		with self.assertRaises(frappe.ValidationError):
			second.submit()
		ok = _invoice(later, series).insert()
		ok.submit()
		self.assertGreater(ok.name, first.name)

	def test_mismo_dia_ok(self):
		series = self._series("SAME")
		d = nowdate()
		a = _invoice(d, series).insert()
		a.submit()
		b = _invoice(d, series).insert()
		b.submit()
		self.assertEqual(getdate(a.posting_date), getdate(b.posting_date))
		self.assertLess(a.name, b.name)

	def test_cancelada_sigue_contando_para_el_orden(self):
		series = self._series("CAN")
		d1 = add_days(nowdate(), -5)
		d2 = nowdate()
		a = _invoice(d1, series).insert()
		a.submit()
		a.reload()
		a.cancel()
		blocked = _invoice(add_days(d1, -1), series).insert()
		with self.assertRaises(frappe.ValidationError):
			blocked.submit()
		b = _invoice(d2, series).insert()
		b.submit()
		self.assertGreater(b.name, a.name)

	def test_borradores_no_consumen_ni_bloquean_serie(self):
		"""Varios borradores no avanzan el contador oficial ni se correlacionan."""
		series = self._series("GAP")
		d = nowdate()
		drafts = [_invoice(d, series).insert() for _ in range(3)]
		for draft in drafts:
			self.assertTrue(is_provisional_name(draft.name))
		first = _invoice(d, series).insert()
		first.submit()
		# El primero validado es el 00001 de la serie, no el 00004
		self.assertTrue(first.name.endswith("00001"))


	def test_misma_serie_con_plantilla_naming_distinta(self):
		year = getdate(nowdate()).strftime("%Y")
		series_a = f"SCXTMPL.F.{year}."
		series_alt = f"SCXTMPL.F.{year}.#####"
		later = nowdate()
		earlier = add_days(nowdate(), -5)
		first = _invoice(later, series_a).insert()
		first.submit()
		self.assertEqual(series_prefix_from_name(first.name, 5), f"SCXTMPLF{year}")
		second = _invoice(earlier, series_alt).insert()
		with self.assertRaises(frappe.ValidationError):
			second.submit()

	def test_ignore_validate_no_salta_correlatividad_al_validar(self):
		series = self._series("IGN")
		later = nowdate()
		earlier = add_days(nowdate(), -7)
		first = _invoice(later, series).insert()
		first.submit()
		blocked = _invoice(earlier, series).insert()
		blocked.flags.ignore_validate = True
		with self.assertRaises(frappe.ValidationError):
			blocked.submit()
