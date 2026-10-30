# Copyright (c) 2026, Xappiens and contributors
# License: MIT

"""Estructura PGC del balance y la PyG y clasificación de cuentas por prefijo."""

from frappe.tests import UnitTestCase

from spain_compliance.contabilidad import cuentas_anuales as ca
from spain_compliance.contabilidad.pgc import CUADRO, normalizar_numero


class TestEstructura(UnitTestCase):
	def test_todo_destino_es_partida_hoja(self):
		hojas_balance = set(ca.HOJAS_BALANCE)
		for prefijo, destino in ca._REGLAS_BALANCE.items():
			destinos = destino if isinstance(destino, tuple) else (destino,)
			for code in destinos:
				self.assertIn(code, hojas_balance, prefijo)
		for prefijo, code in ca._INDICE_PYG.items():
			self.assertIn(code, ca.HOJAS_PYG, prefijo)

	def test_reglas_por_signo_van_de_activo_a_pasivo(self):
		for prefijo, (deudora, acreedora) in ca.POR_SIGNO.items():
			self.assertEqual(ca.lado(deudora), "activo", prefijo)
			self.assertEqual(ca.lado(acreedora), "pasivo", prefijo)

	def test_orden_pyg_incluye_todas_las_lineas(self):
		codigos = {nodo["code"] for nodo in ca.PYG} | set(ca.SUBTOTALES_PYG)
		self.assertEqual(set(ca.ORDEN_PYG), codigos)
		self.assertEqual(ca.ORDEN_PYG[-1], "A.5")

	def test_cuadro_tiene_los_nueve_grupos(self):
		self.assertEqual({codigo for codigo in CUADRO if len(codigo) == 1}, set("123456789"))


class TestClasificacion(UnitTestCase):
	def test_balance_por_prefijo_mas_largo(self):
		casos = {
			"4300000161": "B.III.1",
			"4709000001": "B.III.5",
			"4700000001": "B.III.6",
			"4752000001": "PC.V.5",
			"4770000021": "PC.V.6",
			"2801000001": "A.I.1",
			"2811000001": "A.II.1",
			"2810000001": "A.II.2",
			"1290000000": "PN.1.VII",
			"5570000001": "PN.1.VIII",
			"9400001": "PN.3",
		}
		for numero, esperado in casos.items():
			self.assertEqual(ca.partida_balance(numero, 1)[0], esperado, numero)

	def test_cero_de_relleno_no_activa_subcuenta_de_cuatro_digitos(self):
		self.assertEqual(ca.partida_balance("2800000001", -1)[0], "A.I.7")
		self.assertEqual(ca.partida_pyg("6620000001")[0], "15.b")
		self.assertEqual(ca.partida_pyg("6621000001")[0], "15.a")

	def test_cambio_de_lado_segun_saldo(self):
		self.assertEqual(ca.partida_balance("5720000001", 100)[0], "B.VII.1")
		self.assertEqual(ca.partida_balance("5720000001", -100)[0], "PC.III.2")
		self.assertEqual(ca.partida_balance("5510000001", 100)[0], "B.V.5")
		self.assertEqual(ca.partida_balance("5510000001", -100)[0], "PC.III.5")
		self.assertEqual(ca.partida_balance("4070000001", 100)[0], "B.II.6")
		self.assertEqual(ca.partida_balance("4070000001", -100)[0], "PC.V.1")

	def test_pyg_por_prefijo(self):
		casos = {
			"7000000001": "1.a",
			"7050000001": "1.b",
			"7100": "2",
			"6000000001": "4.a",
			"6400000001": "6.a",
			"6420000001": "6.b",
			"6290000001": "7.a",
			"6810000001": "8",
			"7680000001": "17",
			"6300000001": "20",
			"7954": "7.c",
			"7957": "6.c",
		}
		for numero, esperado in casos.items():
			self.assertEqual(ca.partida_pyg(numero)[0], esperado, numero)

	def test_cuenta_fuera_del_cuadro_se_avisa(self):
		destino, inferida = ca.partida_balance("4500000001", 10)
		self.assertEqual(destino, "B.III.3")
		self.assertTrue(inferida)

	def test_sin_numero_se_clasifica_por_tipo(self):
		self.assertEqual(ca.partida_pyg("", "Expense", "Cost of Goods Sold"), ("4.a", True))
		self.assertEqual(ca.partida_pyg("", "Income", None), ("5.a", True))
		self.assertEqual(ca.partida_balance("", 10, "Asset", "Bank"), ("B.VII.1", True))
		self.assertEqual(ca.partida_balance("", -10, "Liability", "Payable"), ("PC.V.1", True))

	def test_grupos_seis_y_siete_son_resultados(self):
		self.assertTrue(ca.es_pyg("6000000001", "Asset"))
		self.assertFalse(ca.es_pyg("4300000001", "Income"))
		self.assertTrue(ca.es_pyg("", "Expense"))
		self.assertEqual(normalizar_numero("430.0001"), "4300001")


class TestPresentacion(UnitTestCase):
	def _periodo(self, importes: dict[str, float]):
		periodo = ca.Periodo()
		for code, importe in importes.items():
			info = {"account": f"cuenta-{code}", "numero": "", "nombre": code, "sintetica": False}
			periodo.sumar(code, f"cuenta-{code}", importe, info)
		return periodo

	def test_subtotales_pyg(self):
		periodo = self._periodo({"1.a": 1000, "4.a": -600, "6.a": -200, "14.b": 10, "15.b": -30, "20": -45})
		lineas = {linea["code"]: linea["importes"][0] for linea in ca.lineas_pyg([periodo])}
		self.assertEqual(lineas["A.1"], 200)
		self.assertEqual(lineas["A.2"], -20)
		self.assertEqual(lineas["A.3"], 180)
		self.assertEqual(lineas["A.5"], 135)

	def test_ratios_sin_pasivo_no_dividen_por_cero(self):
		ratios = ca.ratios_balance(
			{"ac": 100, "pc": 0, "pnc": 0, "pn": 100, "existencias": 0, "disponible": 50, "activo": 100}
		)
		self.assertIsNone(ratios["liquidez"])
		self.assertEqual(ratios["fondo_maniobra"], 100)

	def test_meses_entre(self):
		self.assertEqual(
			ca.meses_entre("2026-11-15", "2027-02-01"), ["2026-11", "2026-12", "2027-01", "2027-02"]
		)

	def test_tipo_de_nodo(self):
		self.assertEqual(ca._tipo_nodo("A) Activo no corriente"), "masa")
		self.assertEqual(ca._tipo_nodo("A-1) Fondos propios"), "submasa")
		self.assertEqual(ca._tipo_nodo("VII. Efectivo y otros activos líquidos equivalentes"), "epigrafe")
		self.assertEqual(ca._tipo_nodo("1. Tesorería"), "partida")
		self.assertEqual(ca._tipo_nodo("a) Ventas"), "partida")
		self.assertEqual(ca._tipo_nodo("Total activo"), "total")
