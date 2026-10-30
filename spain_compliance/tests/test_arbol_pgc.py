# Copyright (c) 2026, Xappiens and contributors
# License: MIT

"""Coherencia del árbol de cuentas con la numeración del PGC."""

import json
from pathlib import Path

from frappe.tests import UnitTestCase

from spain_compliance.contabilidad.arbol_pgc import (
	auditar_plantilla,
	es_codigo_relleno,
	padre_canonico,
	planificar,
	plantilla_coherente,
)
from spain_compliance.contabilidad.pgc import CUADRO

_PLANTILLA = Path(__file__).resolve().parents[1] / "contabilidad" / "charts" / "es_pgce_con_numeros.json"


class TestPadreCanonico(UnitTestCase):
	def test_auxiliar_no_cuelga_del_relleno_de_ceros(self):
		grupos = {"4", "43", "430", "4300", "4301"}
		self.assertTrue(es_codigo_relleno("4300", grupos))
		self.assertFalse(es_codigo_relleno("4301", grupos))
		self.assertEqual(padre_canonico("4300000161", grupos), "430")
		self.assertEqual(padre_canonico("4301000999", grupos), "4301")

	def test_cuenta_de_diez_digitos_con_ceros_es_la_de_tres(self):
		grupos = {"6", "66", "662", "6620"}
		self.assertEqual(padre_canonico("6620000001", grupos), "662")

	def test_el_cuadro_conserva_el_grupo_intermedio(self):
		grupos = {"4", "43", "431", "4310"}
		self.assertEqual(padre_canonico("43100", grupos), "4310")
		self.assertEqual(padre_canonico("4310", grupos), "431")

	def test_el_padre_sale_del_numero_no_del_hueco_donde_estuviera(self):
		grupos = {"2", "21", "22"}
		self.assertEqual(padre_canonico("210", grupos), "21")
		self.assertIsNone(padre_canonico("2", grupos))
		self.assertEqual(padre_canonico("43", {"4", "43"}), "4")


class TestPlan(UnitTestCase):
	def test_recoloca_el_auxiliar_y_renombra_el_grupo(self):
		filas = [
			_fila("4", "4", CUADRO["4"], padre=""),
			_fila("43", "43", CUADRO["43"], padre="4"),
			_fila("430", "430", "Anticipos de clientes", padre="43"),
			_fila("4300", "4300", "Anticipos de clientes", padre="430"),
			_fila("cli", "4300000161", "Cliente de ejemplo", padre="43", grupo=0),
			_fila("suelto", "", "Sin número", padre="40", grupo=0),
		]
		plan = planificar(filas, abbr="SRG")
		self.assertEqual(plan["renombrar"], [{"name": "430", "number": "430", "account_name": "Clientes"}])
		self.assertEqual(
			plan["recolocar"],
			[{"name": "cli", "number": "4300000161", "parent_number": "430"}],
		)
		self.assertEqual(plan["omitidos"], 1)
		self.assertGreaterEqual(plan["coherentes"], 4)
		self.assertEqual(plan["choques"], [])

	def test_no_toca_lo_que_ya_cuadra(self):
		filas = [
			_fila("4", "4", CUADRO["4"], padre=""),
			_fila("43", "43", CUADRO["43"], padre="4"),
			_fila("430", "430", CUADRO["430"], padre="43"),
			_fila("cli", "4300000161", "Cliente de ejemplo", padre="430", grupo=0),
		]
		plan = planificar(filas, abbr="SRG")
		self.assertEqual(plan["crear"], [])
		self.assertEqual(plan["renombrar"], [])
		self.assertEqual(plan["recolocar"], [])


class TestPlantilla(UnitTestCase):
	def test_reubica_por_numero_y_usa_el_nombre_oficial(self):
		data = {
			"country_code": "es",
			"name": "prueba",
			"tree": {
				"Inmovilizaciones materiales": {
					"Construcciones": {
						"account_number": "210",
						"root_type": "Asset",
						"is_group": 1,
					},
					"account_number": "22",
					"root_type": "Asset",
					"is_group": 1,
				}
			},
		}
		nuevo = plantilla_coherente(data)
		self.assertEqual(auditar_plantilla(nuevo), [])
		nodos = _indexar(nuevo["tree"])
		self.assertEqual(nodos["210"]["padre"], "21")
		self.assertEqual(nodos["210"]["nombre"], CUADRO["210"])
		self.assertEqual(nodos["22"]["padre"], "2")
		self.assertNotEqual(nodos["210"]["padre"], "22")

	def test_la_plantilla_del_repositorio_es_coherente(self):
		data = json.loads(_PLANTILLA.read_text())
		self.assertEqual(auditar_plantilla(data), [])


def _fila(name, number, account_name, padre, grupo=1):
	docname = f"{number} - {account_name} - SRG" if number else name
	return {
		"name": docname if number and account_name == CUADRO.get(number) else name,
		"number": number,
		"account_name": account_name,
		"is_group": grupo,
		"parent_number": padre,
	}


def _indexar(arbol, padre=""):
	meta = {
		"account_name",
		"account_number",
		"account_type",
		"account_category",
		"root_type",
		"is_group",
		"tax_rate",
		"account_currency",
	}
	out = {}
	for nombre, nodo in arbol.items():
		if nombre in meta or not isinstance(nodo, dict):
			continue
		numero = str(nodo.get("account_number") or "")
		out[numero] = {"padre": padre, "nombre": nombre}
		out.update(_indexar(nodo, numero))
	return out
