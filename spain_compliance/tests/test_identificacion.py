# Copyright (c) 2026, Xappiens and contributors
# License: MIT

"""Dígito de control de NIF, NIE, CIF y NIF-IVA. Los números son de prueba."""

import frappe
from frappe.tests.utils import FrappeTestCase

from spain_compliance.contabilidad.identificacion import (
	nif_espanol_valido,
	nif_iva_valido,
	validate_party,
)


class TestIdentificacion(FrappeTestCase):
	def test_dni_nie_y_cif(self):
		self.assertTrue(nif_espanol_valido("12345678Z"))
		self.assertTrue(nif_espanol_valido("12345678-Z"))
		self.assertFalse(nif_espanol_valido("12345678A"))

		self.assertTrue(nif_espanol_valido("X1234567L"))
		self.assertFalse(nif_espanol_valido("X1234567A"))

		self.assertTrue(nif_espanol_valido("B12345674"))
		self.assertFalse(nif_espanol_valido("B12345670"))
		self.assertTrue(nif_espanol_valido("P1234567D"))
		self.assertFalse(nif_espanol_valido("P12345674"))

	def test_nif_iva(self):
		self.assertTrue(nif_iva_valido("ES12345678Z"))
		self.assertFalse(nif_iva_valido("ES12345678A"))
		self.assertTrue(nif_iva_valido("DE123456789"))
		self.assertFalse(nif_iva_valido("12345678Z"))

	def test_aviso_sin_bloquear_el_alta(self):
		if not frappe.db.exists("Customer Group", "_Test SC Fiscal Clientes"):
			frappe.get_doc(
				{
					"doctype": "Customer Group",
					"customer_group_name": "_Test SC Fiscal Clientes",
					"parent_customer_group": "All Customer Groups",
				}
			).insert()

		frappe.clear_messages()
		cliente = frappe.get_doc(
			{
				"doctype": "Customer",
				"customer_name": "_Test SC NIF mal",
				"customer_type": "Company",
				"customer_group": "_Test SC Fiscal Clientes",
				"tax_id": "12345678A",
				"tipo_identificacion_fiscal": "NIF",
			}
		).insert()
		self.assertTrue(cliente.name)
		mensajes = " ".join(m.get("message") or "" for m in frappe.get_message_log())
		self.assertIn("12345678A", mensajes)

	def test_pasaporte_no_se_valida_como_nif(self):
		doc = frappe._dict(
			tax_id="NO-ES-UN-NIF",
			tipo_identificacion_fiscal="Pasaporte",
			customer_name="Viajero",
			name="VIAJERO",
		)
		frappe.clear_messages()
		validate_party(doc)
		self.assertFalse(frappe.get_message_log())
