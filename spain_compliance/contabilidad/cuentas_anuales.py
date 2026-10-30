# Copyright (c) 2026, Xappiens and contributors
# License: MIT

"""Balance, cuenta de pérdidas y ganancias y sumas y saldos con la estructura del PGC.

Los estados siguen el modelo normal de cuentas anuales (RD 1514/2007 y RD 1/2021):
masas, epígrafes (I, II…) y partidas (1, 2…). Cada cuenta va a una partida por el
prefijo más largo de su número: 430 → B.III.1, 4709 → B.III.5.

Reglas que no se ven en las tablas:

- Los prefijos de cuatro dígitos terminados en 0 (2800, 6620, 7950…) no se usan.
  Una subcuenta 6620000001 casi siempre es la 662 rellenada con ceros, no
  «intereses de deudas con empresas del grupo».
- Algunas cuentas cambian de lado según su saldo: un banco con saldo acreedor es
  deuda con entidades de crédito; la 551 deudora es un activo y acreedora un pasivo.
- Los grupos 6 y 7 no van al balance. Su saldo del ejercicio se presenta en A-1.VII
  y el de ejercicios anteriores sin asiento de cierre en A-1.V, así que el balance
  cuadra aunque no se haya regularizado.
- Una cuenta sin número se clasifica por su tipo en ERPNext y se avisa.
"""

from __future__ import annotations

import re
from collections import defaultdict

import frappe
from frappe import _
from frappe.utils import add_months, add_years, flt, getdate

from spain_compliance.contabilidad.pgc import CUADRO, nombre_pgc, normalizar_numero

_EPS = 0.005


def _p(code: str, label: str, prefijos: tuple[str, ...] = (), hijos: list | None = None) -> dict:
	return {"code": code, "label": label, "prefijos": tuple(prefijos), "hijos": hijos or []}


# Balance --------------------------------------------------------------------------

ACTIVO = _p(
	"ACTIVO",
	"Total activo",
	hijos=[
		_p(
			"A",
			"A) Activo no corriente",
			hijos=[
				_p(
					"A.I",
					"I. Inmovilizado intangible",
					hijos=[
						_p("A.I.1", "1. Desarrollo", ("201", "2801", "2901")),
						_p("A.I.2", "2. Concesiones", ("202", "2802", "2902")),
						_p("A.I.3", "3. Patentes, licencias, marcas y similares", ("203", "2803", "2903")),
						_p("A.I.4", "4. Fondo de comercio", ("204", "2804", "2904")),
						_p("A.I.5", "5. Aplicaciones informáticas", ("206", "2806", "2906")),
						_p("A.I.6", "6. Investigación", ("200",)),
						_p(
							"A.I.7",
							"7. Otro inmovilizado intangible",
							("205", "209", "2805", "2905", "280", "290", "20"),
						),
					],
				),
				_p(
					"A.II",
					"II. Inmovilizado material",
					hijos=[
						_p("A.II.1", "1. Terrenos y construcciones", ("210", "211", "2811", "2911")),
						_p(
							"A.II.2",
							"2. Instalaciones técnicas y otro inmovilizado material",
							(
								"212",
								"213",
								"214",
								"215",
								"216",
								"217",
								"218",
								"219",
								"21",
								"281",
								"291",
								"28",
								"29",
							),
						),
						_p("A.II.3", "3. Inmovilizado en curso y anticipos", ("23",)),
					],
				),
				_p(
					"A.III",
					"III. Inversiones inmobiliarias",
					hijos=[
						_p("A.III.1", "1. Terrenos", ("220",)),
						_p("A.III.2", "2. Construcciones", ("221", "22", "282", "292", "2921")),
					],
				),
				_p(
					"A.IV",
					"IV. Inversiones en empresas del grupo y asociadas a largo plazo",
					hijos=[
						_p(
							"A.IV.1",
							"1. Instrumentos de patrimonio",
							("240", "2403", "2404", "249", "2493", "2494", "293"),
						),
						_p(
							"A.IV.2", "2. Créditos a empresas", ("242", "2423", "2424", "295", "2953", "2954")
						),
						_p(
							"A.IV.3",
							"3. Valores representativos de deuda",
							("241", "2413", "2414", "294", "2943", "2944"),
						),
						_p("A.IV.4", "4. Derivados"),
						_p("A.IV.5", "5. Otros activos financieros", ("24",)),
					],
				),
				_p(
					"A.V",
					"V. Inversiones financieras a largo plazo",
					hijos=[
						_p("A.V.1", "1. Instrumentos de patrimonio", ("2405", "2495", "250", "259")),
						_p("A.V.2", "2. Créditos a terceros", ("2425", "252", "253", "254", "2955", "298")),
						_p("A.V.3", "3. Valores representativos de deuda", ("2415", "251", "2945", "297")),
						_p("A.V.4", "4. Derivados", ("255",)),
						_p("A.V.5", "5. Otros activos financieros", ("257", "258", "26", "25", "2")),
					],
				),
				_p("A.VI", "VI. Activos por impuesto diferido", ("474",)),
				_p("A.VII", "VII. Deudores comerciales no corrientes"),
			],
		),
		_p(
			"B",
			"B) Activo corriente",
			hijos=[
				_p(
					"B.I",
					"I. Activos no corrientes mantenidos para la venta",
					("580", "581", "582", "583", "584", "599", "58"),
				),
				_p(
					"B.II",
					"II. Existencias",
					hijos=[
						_p("B.II.1", "1. Comerciales", ("30", "390", "39", "3")),
						_p(
							"B.II.2",
							"2. Materias primas y otros aprovisionamientos",
							("31", "32", "391", "392"),
						),
						_p("B.II.3", "3. Productos en curso", ("33", "34", "393", "394")),
						_p("B.II.4", "4. Productos terminados", ("35", "395")),
						_p("B.II.5", "5. Subproductos, residuos y materiales recuperados", ("36", "396")),
						_p("B.II.6", "6. Anticipos a proveedores"),
					],
				),
				_p(
					"B.III",
					"III. Deudores comerciales y otras cuentas a cobrar",
					hijos=[
						_p(
							"B.III.1",
							"1. Clientes por ventas y prestaciones de servicios",
							("430", "431", "432", "435", "436", "437", "43", "490", "493", "4935", "49"),
						),
						_p(
							"B.III.2",
							"2. Clientes, empresas del grupo y asociadas",
							("433", "434", "4933", "4934"),
						),
						_p("B.III.3", "3. Deudores varios", ("44",)),
						_p("B.III.4", "4. Personal", ("460", "544")),
						_p("B.III.5", "5. Activos por impuesto corriente", ("4709", "473")),
						_p(
							"B.III.6",
							"6. Otros créditos con las Administraciones Públicas",
							("470", "471", "472"),
						),
						_p("B.III.7", "7. Accionistas (socios) por desembolsos exigidos", ("558",)),
					],
				),
				_p(
					"B.IV",
					"IV. Inversiones en empresas del grupo y asociadas a corto plazo",
					hijos=[
						_p(
							"B.IV.1",
							"1. Instrumentos de patrimonio",
							("530", "5303", "5304", "539", "5393", "5394", "593"),
						),
						_p(
							"B.IV.2",
							"2. Créditos a empresas",
							("532", "5323", "5324", "534", "5343", "5344", "595", "5953", "5954"),
						),
						_p(
							"B.IV.3",
							"3. Valores representativos de deuda",
							("531", "5313", "5314", "533", "5333", "5334", "594", "5943", "5944"),
						),
						_p("B.IV.4", "4. Derivados"),
						_p("B.IV.5", "5. Otros activos financieros", ("535", "5353", "5354", "53")),
					],
				),
				_p(
					"B.V",
					"V. Inversiones financieras a corto plazo",
					hijos=[
						_p("B.V.1", "1. Instrumentos de patrimonio", ("5305", "5395", "540", "549")),
						_p(
							"B.V.2",
							"2. Créditos a empresas",
							("5325", "5345", "542", "543", "547", "5955", "598", "59"),
						),
						_p(
							"B.V.3",
							"3. Valores representativos de deuda",
							("5315", "5335", "541", "546", "5945", "597"),
						),
						_p("B.V.4", "4. Derivados", ("559", "5593")),
						_p(
							"B.V.5",
							"5. Otros activos financieros",
							("5355", "545", "548", "565", "566", "54"),
						),
					],
				),
				_p("B.VI", "VI. Periodificaciones a corto plazo", ("480", "567")),
				_p(
					"B.VII",
					"VII. Efectivo y otros activos líquidos equivalentes",
					hijos=[
						_p("B.VII.1", "1. Tesorería", ("570", "571", "57")),
						_p("B.VII.2", "2. Otros activos líquidos equivalentes", ("576",)),
					],
				),
			],
		),
	],
)

PATRIMONIO_PASIVO = _p(
	"PNP",
	"Total patrimonio neto y pasivo",
	hijos=[
		_p(
			"PN",
			"A) Patrimonio neto",
			hijos=[
				_p(
					"PN.1",
					"A-1) Fondos propios",
					hijos=[
						_p(
							"PN.1.I",
							"I. Capital",
							hijos=[
								_p("PN.1.I.1", "1. Capital escriturado", ("100", "101", "102", "10")),
								_p("PN.1.I.2", "2. (Capital no exigido)", ("103", "104")),
							],
						),
						_p("PN.1.II", "II. Prima de emisión", ("110",)),
						_p(
							"PN.1.III",
							"III. Reservas",
							hijos=[
								_p("PN.1.III.1", "1. Legal y estatutarias", ("112", "1141")),
								_p(
									"PN.1.III.2",
									"2. Otras reservas",
									("113", "114", "115", "119", "11", "85", "95"),
								),
							],
						),
						_p(
							"PN.1.IV",
							"IV. (Acciones y participaciones en patrimonio propias)",
							("108", "109"),
						),
						_p(
							"PN.1.V",
							"V. Resultados de ejercicios anteriores",
							hijos=[
								_p("PN.1.V.1", "1. Remanente", ("120", "12")),
								_p(
									"PN.1.V.2", "2. (Resultados negativos de ejercicios anteriores)", ("121",)
								),
							],
						),
						_p("PN.1.VI", "VI. Otras aportaciones de socios", ("118",)),
						_p("PN.1.VII", "VII. Resultado del ejercicio", ("129",)),
						_p("PN.1.VIII", "VIII. (Dividendo a cuenta)", ("557",)),
						_p("PN.1.IX", "IX. Otros instrumentos de patrimonio neto", ("111",)),
					],
				),
				_p(
					"PN.2",
					"A-2) Ajustes en patrimonio neto",
					hijos=[
						_p(
							"PN.2.I",
							"I. Activos financieros a valor razonable con cambios en el patrimonio neto",
							("133", "80", "90"),
						),
						_p("PN.2.II", "II. Operaciones de cobertura", ("134", "81", "91")),
						_p(
							"PN.2.III",
							"III. Activos no corrientes y pasivos vinculados, mantenidos para la venta",
							("136", "86", "96"),
						),
						_p("PN.2.IV", "IV. Diferencia de conversión", ("135", "82", "92")),
						_p("PN.2.V", "V. Otros", ("137", "13", "83", "89", "99", "8", "9")),
					],
				),
				_p(
					"PN.3",
					"A-3) Subvenciones, donaciones y legados recibidos",
					("130", "131", "132", "84", "94"),
				),
			],
		),
		_p(
			"PNC",
			"B) Pasivo no corriente",
			hijos=[
				_p(
					"PNC.I",
					"I. Provisiones a largo plazo",
					hijos=[
						_p("PNC.I.1", "1. Obligaciones por prestaciones a largo plazo al personal", ("140",)),
						_p("PNC.I.2", "2. Actuaciones medioambientales", ("145",)),
						_p("PNC.I.3", "3. Provisiones por reestructuración", ("146",)),
						_p("PNC.I.4", "4. Otras provisiones", ("141", "142", "143", "147", "14")),
					],
				),
				_p(
					"PNC.II",
					"II. Deudas a largo plazo",
					hijos=[
						_p("PNC.II.1", "1. Obligaciones y otros valores negociables", ("177", "178", "179")),
						_p("PNC.II.2", "2. Deudas con entidades de crédito", ("1605", "170")),
						_p("PNC.II.3", "3. Acreedores por arrendamiento financiero", ("1625", "174")),
						_p("PNC.II.4", "4. Derivados", ("176",)),
						_p(
							"PNC.II.5",
							"5. Otros pasivos financieros",
							("1615", "1635", "171", "172", "173", "175", "17", "180", "185", "189", "18"),
						),
					],
				),
				_p(
					"PNC.III",
					"III. Deudas con empresas del grupo y asociadas a largo plazo",
					("160", "161", "162", "163", "16"),
				),
				_p("PNC.IV", "IV. Pasivos por impuesto diferido", ("479",)),
				_p("PNC.V", "V. Periodificaciones a largo plazo", ("181",)),
				_p("PNC.VI", "VI. Acreedores comerciales no corrientes"),
				_p("PNC.VII", "VII. Deuda con características especiales a largo plazo", ("15",)),
			],
		),
		_p(
			"PC",
			"C) Pasivo corriente",
			hijos=[
				_p(
					"PC.I",
					"I. Pasivos vinculados con activos no corrientes mantenidos para la venta",
					("585", "586", "587", "588", "589"),
				),
				_p("PC.II", "II. Provisiones a corto plazo", ("499", "529")),
				_p(
					"PC.III",
					"III. Deudas a corto plazo",
					hijos=[
						_p(
							"PC.III.1",
							"1. Obligaciones y otros valores negociables",
							("500", "501", "505", "506", "50"),
						),
						_p("PC.III.2", "2. Deudas con entidades de crédito", ("5105", "520", "527")),
						_p("PC.III.3", "3. Acreedores por arrendamiento financiero", ("5125", "524")),
						_p("PC.III.4", "4. Derivados", ("5595", "5598")),
						_p(
							"PC.III.5",
							"5. Otros pasivos financieros",
							(
								"19",
								"509",
								"5115",
								"5135",
								"5145",
								"521",
								"522",
								"523",
								"525",
								"526",
								"528",
								"52",
								"556",
								"5565",
								"5566",
								"560",
								"561",
								"569",
							),
						),
					],
				),
				_p(
					"PC.IV",
					"IV. Deudas con empresas del grupo y asociadas a corto plazo",
					("510", "511", "512", "513", "514", "51", "5563", "5564"),
				),
				_p(
					"PC.V",
					"V. Acreedores comerciales y otras cuentas a pagar",
					hijos=[
						_p("PC.V.1", "1. Proveedores", ("400", "401", "405", "406", "40")),
						_p("PC.V.2", "2. Proveedores, empresas del grupo y asociadas", ("403", "404")),
						_p("PC.V.3", "3. Acreedores varios", ("41",)),
						_p("PC.V.4", "4. Personal (remuneraciones pendientes de pago)", ("465", "466")),
						_p("PC.V.5", "5. Pasivos por impuesto corriente", ("4752",)),
						_p(
							"PC.V.6",
							"6. Otras deudas con las Administraciones Públicas",
							("475", "476", "477"),
						),
						_p("PC.V.7", "7. Anticipos de clientes"),
					],
				),
				_p("PC.VI", "VI. Periodificaciones a corto plazo", ("485", "568")),
				_p("PC.VII", "VII. Deuda con características especiales a corto plazo", ("502", "507")),
			],
		),
	],
)

# Cuentas que se presentan en el activo o en el pasivo según su saldo:
# prefijo → (partida si es deudora, partida si es acreedora).
POR_SIGNO: dict[str, tuple[str, str]] = {
	"407": ("B.II.6", "PC.V.1"),
	"438": ("B.III.1", "PC.V.7"),
	"46": ("B.III.4", "PC.V.4"),
	"47": ("B.III.6", "PC.V.6"),
	"48": ("B.VI", "PC.VI"),
	"4": ("B.III.3", "PC.V.3"),
	"550": ("B.V.5", "PC.III.5"),
	"551": ("B.V.5", "PC.III.5"),
	"552": ("B.V.5", "PC.III.5"),
	"5523": ("B.IV.5", "PC.IV"),
	"5524": ("B.IV.5", "PC.IV"),
	"5525": ("B.V.5", "PC.III.5"),
	"553": ("B.III.3", "PC.III.5"),
	"554": ("B.V.5", "PC.III.5"),
	"555": ("B.V.5", "PC.III.5"),
	"55": ("B.V.5", "PC.III.5"),
	"56": ("B.V.5", "PC.III.5"),
	"572": ("B.VII.1", "PC.III.2"),
	"573": ("B.VII.1", "PC.III.2"),
	"574": ("B.VII.1", "PC.III.2"),
	"575": ("B.VII.1", "PC.III.2"),
}

# Pérdidas y ganancias -------------------------------------------------------------

PYG: list[dict] = [
	_p(
		"1",
		"1. Importe neto de la cifra de negocios",
		hijos=[
			_p("1.a", "a) Ventas", ("700", "701", "702", "703", "704", "706", "708", "709", "70")),
			_p("1.b", "b) Prestaciones de servicios", ("705",)),
		],
	),
	_p("2", "2. Variación de existencias de productos terminados y en curso de fabricación", ("71",)),
	_p("3", "3. Trabajos realizados por la empresa para su activo", ("73",)),
	_p(
		"4",
		"4. Aprovisionamientos",
		hijos=[
			_p("4.a", "a) Consumo de mercaderías", ("600", "606", "608", "609", "610", "60", "61")),
			_p(
				"4.b",
				"b) Consumo de materias primas y otras materias consumibles",
				("601", "602", "6061", "6062", "6081", "6082", "6091", "6092", "611", "612"),
			),
			_p("4.c", "c) Trabajos realizados por otras empresas", ("607",)),
			_p(
				"4.d",
				"d) Deterioro de mercaderías, materias primas y otros aprovisionamientos",
				("693", "6931", "6932", "6933", "793", "7931", "7932", "7933"),
			),
		],
	),
	_p(
		"5",
		"5. Otros ingresos de explotación",
		hijos=[
			_p("5.a", "a) Ingresos accesorios y otros de gestión corriente", ("75", "72", "78", "7")),
			_p(
				"5.b",
				"b) Subvenciones de explotación incorporadas al resultado del ejercicio",
				("740", "747", "74"),
			),
		],
	),
	_p(
		"6",
		"6. Gastos de personal",
		hijos=[
			_p("6.a", "a) Sueldos, salarios y asimilados", ("640", "641", "645", "64")),
			_p("6.b", "b) Cargas sociales", ("642", "643", "649")),
			_p("6.c", "c) Provisiones", ("644", "6457", "7957")),
		],
	),
	_p(
		"7",
		"7. Otros gastos de explotación",
		hijos=[
			_p("7.a", "a) Servicios exteriores", ("62",)),
			_p("7.b", "b) Tributos", ("631", "634", "636", "639", "63")),
			_p(
				"7.c",
				"c) Pérdidas, deterioro y variación de provisiones por operaciones comerciales",
				("650", "694", "695", "794", "7954"),
			),
			_p("7.d", "d) Otros gastos de gestión corriente", ("651", "659", "65", "6")),
		],
	),
	_p("8", "8. Amortización del inmovilizado", ("68",)),
	_p("9", "9. Imputación de subvenciones de inmovilizado no financiero y otras", ("746",)),
	_p("10", "10. Excesos de provisiones", ("795", "7951", "7952", "7955", "7956", "79")),
	_p(
		"11",
		"11. Deterioro y resultado por enajenaciones del inmovilizado",
		hijos=[
			_p("11.a", "a) Deterioros y pérdidas", ("690", "691", "692", "790", "791", "792", "69")),
			_p("11.b", "b) Resultados por enajenaciones y otras", ("670", "671", "672", "770", "771", "772")),
		],
	),
	_p("12", "12. Diferencia negativa de combinaciones de negocio", ("774",)),
	_p("13", "13. Otros resultados", ("678", "778", "67", "77")),
	_p(
		"14",
		"14. Ingresos financieros",
		hijos=[
			_p("14.a", "a) De participaciones en instrumentos de patrimonio", ("760",)),
			_p(
				"14.b",
				"b) De valores negociables y otros instrumentos financieros",
				("761", "762", "767", "769", "76"),
			),
		],
	),
	_p(
		"15",
		"15. Gastos financieros",
		hijos=[
			_p(
				"15.a",
				"a) Por deudas con empresas del grupo y asociadas",
				("6611", "6615", "6616", "6621", "6641", "6651", "6654", "6655"),
			),
			_p("15.b", "b) Por deudas con terceros", ("661", "662", "664", "665", "669", "66")),
			_p("15.c", "c) Por actualización de provisiones", ("660",)),
		],
	),
	_p("16", "16. Variación de valor razonable en instrumentos financieros", ("663", "763")),
	_p("17", "17. Diferencias de cambio", ("668", "768")),
	_p(
		"18",
		"18. Deterioro y resultado por enajenaciones de instrumentos financieros",
		hijos=[
			_p("18.a", "a) Deterioros y pérdidas", ("696", "697", "698", "699", "796", "797", "798", "799")),
			_p(
				"18.b",
				"b) Resultados por enajenaciones y otras",
				("666", "667", "673", "675", "766", "773", "775"),
			),
		],
	),
	_p("19", "19. Otros ingresos y gastos de carácter financiero"),
	_p("20", "20. Impuestos sobre beneficios", ("630", "633", "638")),
	_p("21", "21. Resultado del ejercicio procedente de operaciones interrumpidas neto de impuestos"),
]

SUBTOTALES_PYG: dict[str, tuple[str, tuple[str, ...]]] = {
	"A.1": ("A.1) Resultado de explotación", tuple(str(n) for n in range(1, 14))),
	"A.2": ("A.2) Resultado financiero", tuple(str(n) for n in range(14, 20))),
	"A.3": ("A.3) Resultado antes de impuestos", ("A.1", "A.2")),
	"A.4": ("A.4) Resultado del ejercicio procedente de operaciones continuadas", ("A.3", "20")),
	"A.5": ("A.5) Resultado del ejercicio", ("A.4", "21")),
}

# Orden de presentación: cada subtotal va detrás de la última línea que suma.
ORDEN_PYG: tuple[str, ...] = (
	*(str(n) for n in range(1, 14)),
	"A.1",
	*(str(n) for n in range(14, 20)),
	"A.2",
	"A.3",
	"20",
	"A.4",
	"21",
	"A.5",
)

_PYG_POR_TIPO = {
	"Cost of Goods Sold": "4.a",
	"Stock Adjustment": "4.a",
	"Expenses Included In Valuation": "4.a",
	"Expenses Included In Asset Valuation": "7.a",
	"Depreciation": "8",
	"Round Off": "13",
	"Tax": "7.b",
}

_BALANCE_ACTIVO_POR_TIPO = {
	"Bank": "B.VII.1",
	"Cash": "B.VII.1",
	"Receivable": "B.III.1",
	"Stock": "B.II.1",
	"Fixed Asset": "A.II.2",
	"Accumulated Depreciation": "A.II.2",
	"Capital Work in Progress": "A.II.3",
	"Tax": "B.III.6",
}

_BALANCE_PASIVO_POR_TIPO = {
	"Payable": "PC.V.1",
	"Tax": "PC.V.6",
}


def _indexar(nodos) -> tuple[dict[str, str], dict[str, dict], list[str]]:
	indice: dict[str, str] = {}
	por_codigo: dict[str, dict] = {}
	hojas: list[str] = []

	def visitar(nodo):
		por_codigo[nodo["code"]] = nodo
		if not nodo["hijos"]:
			hojas.append(nodo["code"])
		for prefijo in nodo["prefijos"]:
			if prefijo in indice:
				raise ValueError(f"Prefijo PGC duplicado: {prefijo}")
			indice[prefijo] = nodo["code"]
		for hijo in nodo["hijos"]:
			visitar(hijo)

	for nodo in nodos:
		visitar(nodo)
	return indice, por_codigo, hojas


_INDICE_BALANCE, NODOS_BALANCE, HOJAS_BALANCE = _indexar([ACTIVO, PATRIMONIO_PASIVO])
_INDICE_PYG, NODOS_PYG, HOJAS_PYG = _indexar(PYG)
if set(_INDICE_BALANCE) & set(POR_SIGNO):
	raise ValueError("Un prefijo PGC no puede tener partida fija y regla por signo")
_REGLAS_BALANCE: dict[str, str | tuple[str, str]] = {**_INDICE_BALANCE, **POR_SIGNO}
_LADO_ACTIVO = frozenset(code for code in NODOS_BALANCE if code == "ACTIVO" or code[0] in "AB")


def lado(code: str) -> str:
	return "activo" if code in _LADO_ACTIVO else "pasivo"


def _prefijo_mas_largo(indice: dict, numero: str):
	for largo in range(len(numero), 0, -1):
		destino = indice.get(numero[:largo])
		if destino is not None:
			return destino
	return None


def es_pyg(numero: str, root_type: str | None) -> bool:
	"""Una cuenta numerada es de resultados si es del grupo 6 o 7; sin número, por su tipo raíz."""
	if numero:
		return numero[0] in "67"
	return root_type in ("Income", "Expense")


def partida_pyg(
	numero: str, root_type: str | None = None, account_type: str | None = None
) -> tuple[str, bool]:
	"""Partida de la PyG y si se ha inferido sin número de cuenta."""
	if numero:
		destino = _prefijo_mas_largo(_INDICE_PYG, numero)
		if destino:
			return destino, numero[:3] not in CUADRO
	destino = _PYG_POR_TIPO.get(account_type or "")
	if not destino:
		destino = "5.a" if root_type == "Income" else "7.d"
	return destino, True


def partida_balance(
	numero: str, saldo_deudor: float, root_type: str | None = None, account_type: str | None = None
) -> tuple[str, bool]:
	"""Partida del balance y si se ha inferido. ``saldo_deudor`` es debe menos haber."""
	if numero:
		destino = _prefijo_mas_largo(_REGLAS_BALANCE, numero)
		if isinstance(destino, tuple):
			return (destino[0] if saldo_deudor >= 0 else destino[1]), numero[:3] not in CUADRO
		if destino:
			return destino, numero[:3] not in CUADRO
	if root_type == "Asset":
		return _BALANCE_ACTIVO_POR_TIPO.get(account_type or "", "B.III.3"), True
	if root_type == "Equity":
		return "PN.1.III.2", True
	return _BALANCE_PASIVO_POR_TIPO.get(account_type or "", "PC.III.5"), True


# Cálculo ---------------------------------------------------------------------------


class Periodo:
	"""Importes por partida y cuenta de un periodo."""

	def __init__(self):
		self.lineas: dict[str, dict[str, float]] = defaultdict(dict)
		self.cuentas: dict[str, dict] = {}
		self.avisos: dict[str, str] = {}

	def sumar(self, code: str, clave: str, importe: float, info: dict):
		self.lineas[code][clave] = self.lineas[code].get(clave, 0.0) + importe
		self.cuentas.setdefault(clave, info)

	def total(self, code: str) -> float:
		return sum(self.lineas.get(code, {}).values())


def ejercicio(company: str, fecha) -> tuple[str, object, object]:
	from erpnext.accounts.utils import get_fiscal_year

	nombre, inicio, fin = get_fiscal_year(fecha, company=company, verbose=0)
	return nombre, getdate(inicio), getdate(fin)


def _info_cuenta(row, numero: str) -> dict:
	return {
		"account": row.account,
		"numero": numero,
		"nombre": row.account_name or row.account,
		"sintetica": False,
	}


def _avisar(periodo: Periodo, row, numero: str, destino: str, etiqueta: str):
	if numero:
		texto = _("La cuenta {0} {1} no está en el cuadro del PGC; se presenta en {2}.").format(
			numero, row.account_name, etiqueta
		)
	else:
		texto = _("La cuenta {0} no tiene número; se presenta en {1} por su tipo.").format(
			row.account, etiqueta
		)
	periodo.avisos[row.account] = texto


def calcular_balance(company: str, fecha) -> Periodo:
	"""Saldos acumulados hasta ``fecha`` repartidos por partidas del balance."""
	fecha = getdate(fecha)
	try:
		_nombre, fy_inicio, _fy_fin = ejercicio(company, fecha)
	except frappe.ValidationError:
		fy_inicio = fecha.replace(month=1, day=1)
	finance_book = frappe.get_cached_value("Company", company, "default_finance_book") or ""
	filas = frappe.db.sql(
		"""
		SELECT g.account, a.account_number, a.account_name, a.root_type, a.account_type,
			IF(g.posting_date < %(fy_inicio)s, 1, 0) AS previo,
			SUM(g.debit) AS debe, SUM(g.credit) AS haber
		FROM `tabGL Entry` g
		INNER JOIN `tabAccount` a ON a.name = g.account
		WHERE g.company = %(company)s AND g.posting_date <= %(fecha)s
			AND g.is_cancelled = 0
			AND (g.finance_book IS NULL OR g.finance_book IN ('', %(finance_book)s))
		GROUP BY g.account, previo
		""",
		{
			"company": company,
			"fecha": fecha,
			"fy_inicio": fy_inicio,
			"finance_book": finance_book,
		},
		as_dict=True,
	)

	periodo = Periodo()
	saldos: dict[str, float] = defaultdict(float)
	filas_cuenta: dict[str, object] = {}
	resultado_ejercicio = 0.0
	resultado_anterior = 0.0
	for row in filas:
		numero = normalizar_numero(row.account_number)
		neto = flt(row.debe) - flt(row.haber)
		if es_pyg(numero, row.root_type):
			if row.previo:
				resultado_anterior -= neto
			else:
				resultado_ejercicio -= neto
			continue
		saldos[row.account] += neto
		filas_cuenta[row.account] = row

	for account, saldo in saldos.items():
		if abs(saldo) < _EPS:
			continue
		row = filas_cuenta[account]
		numero = normalizar_numero(row.account_number)
		destino, inferida = partida_balance(numero, saldo, row.root_type, row.account_type)
		importe = saldo if lado(destino) == "activo" else -saldo
		periodo.sumar(destino, account, importe, _info_cuenta(row, numero))
		if inferida:
			_avisar(periodo, row, numero, destino, NODOS_BALANCE[destino]["label"])

	if abs(resultado_ejercicio) >= _EPS:
		periodo.sumar(
			"PN.1.VII",
			"__resultado_ejercicio__",
			resultado_ejercicio,
			{
				"account": None,
				"numero": "",
				"nombre": _("Resultado del ejercicio en curso (grupos 6 y 7, sin regularizar)"),
				"sintetica": True,
				"enlace": "pyg",
			},
		)
	if abs(resultado_anterior) >= _EPS:
		destino = "PN.1.V.1" if resultado_anterior > 0 else "PN.1.V.2"
		periodo.sumar(
			destino,
			"__resultado_anterior__",
			resultado_anterior,
			{
				"account": None,
				"numero": "",
				"nombre": _("Resultados de ejercicios anteriores sin asiento de cierre"),
				"sintetica": True,
			},
		)
	return periodo


def calcular_pyg(company: str, desde, hasta) -> tuple[Periodo, dict[str, dict[str, float]]]:
	"""Movimientos de los grupos 6 y 7 entre dos fechas, sin el asiento de cierre.

	Devuelve el periodo y, por mes (AAAA-MM), los importes de cada partida hoja.
	"""
	finance_book = frappe.get_cached_value("Company", company, "default_finance_book") or ""
	filas = frappe.db.sql(
		"""
		SELECT g.account, a.account_number, a.account_name, a.root_type, a.account_type,
			DATE_FORMAT(g.posting_date, '%%Y-%%m') AS mes,
			SUM(g.debit) AS debe, SUM(g.credit) AS haber
		FROM `tabGL Entry` g
		INNER JOIN `tabAccount` a ON a.name = g.account
		WHERE g.company = %(company)s AND g.posting_date BETWEEN %(desde)s AND %(hasta)s
			AND g.is_cancelled = 0 AND g.voucher_type != 'Period Closing Voucher'
			AND (g.finance_book IS NULL OR g.finance_book IN ('', %(finance_book)s))
			AND (a.root_type IN ('Income', 'Expense') OR a.account_number LIKE '6%%'
				OR a.account_number LIKE '7%%')
		GROUP BY g.account, mes
		""",
		{
			"company": company,
			"desde": getdate(desde),
			"hasta": getdate(hasta),
			"finance_book": finance_book,
		},
		as_dict=True,
	)
	periodo = Periodo()
	mensual: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
	for row in filas:
		numero = normalizar_numero(row.account_number)
		if not es_pyg(numero, row.root_type):
			continue
		destino, inferida = partida_pyg(numero, row.root_type, row.account_type)
		importe = flt(row.haber) - flt(row.debe)
		periodo.sumar(destino, row.account, importe, _info_cuenta(row, numero))
		mensual[row.mes][destino] += importe
		if inferida:
			_avisar(periodo, row, numero, destino, NODOS_PYG[destino]["label"])
	return periodo, mensual


# Presentación ------------------------------------------------------------------------

_TIPOS_NODO = (
	(re.compile(r"^Total"), "total"),
	(re.compile(r"^[A-C]\) "), "masa"),
	(re.compile(r"^A-\d\) "), "submasa"),
	(re.compile(r"^[IVX]+\. "), "epigrafe"),
	(re.compile(r"^(\d+\.|[a-z]\)) "), "partida"),
)


def _tipo_nodo(label: str) -> str:
	return next((tipo for patron, tipo in _TIPOS_NODO if patron.match(label)), "partida")


def _redondear(valores):
	return [round(v, 2) for v in valores]


def _detalle_cuentas(code: str, periodos: list[Periodo]) -> list[dict]:
	"""Cuentas de una partida agrupadas por cuenta PGC de tres dígitos."""
	claves: dict[str, dict] = {}
	for periodo in periodos:
		for clave in periodo.lineas.get(code, {}):
			claves.setdefault(clave, periodo.cuentas[clave])

	grupos: dict[str, dict] = {}
	for clave, info in claves.items():
		importes = _redondear(p.lineas.get(code, {}).get(clave, 0.0) for p in periodos)
		if info["sintetica"]:
			grupos[clave] = {
				"codigo": "",
				"nombre": info["nombre"],
				"importes": importes,
				"subcuentas": [],
				"sintetica": True,
				"enlace": info.get("enlace"),
			}
			continue
		numero = info["numero"]
		codigo = numero[:3] if len(numero) >= 3 else numero
		grupo = grupos.setdefault(
			codigo,
			{
				"codigo": codigo,
				"nombre": nombre_pgc(codigo) or info["nombre"],
				"importes": [0.0] * len(periodos),
				"subcuentas": [],
				"sintetica": False,
			},
		)
		grupo["importes"] = _redondear(a + b for a, b in zip(grupo["importes"], importes, strict=True))
		grupo["subcuentas"].append(
			{"account": info["account"], "numero": numero, "nombre": info["nombre"], "importes": importes}
		)

	for grupo in grupos.values():
		grupo["subcuentas"].sort(key=lambda row: (row["numero"] or "~", row["nombre"]))
	return sorted(grupos.values(), key=lambda row: (row["sintetica"], row["codigo"] or "~", row["nombre"]))


def construir_arbol(nodo: dict, periodos: list[Periodo], nivel: int = 0) -> dict:
	hijos = [construir_arbol(hijo, periodos, nivel + 1) for hijo in nodo["hijos"]]
	if hijos:
		importes = _redondear(sum(hijo["importes"][i] for hijo in hijos) for i in range(len(periodos)))
		cuentas = []
	else:
		importes = _redondear(periodo.total(nodo["code"]) for periodo in periodos)
		cuentas = _detalle_cuentas(nodo["code"], periodos)
	return {
		"code": nodo["code"],
		"label": nodo["label"],
		"tipo": _tipo_nodo(nodo["label"]),
		"nivel": nivel,
		"importes": importes,
		"hijos": hijos,
		"cuentas": cuentas,
	}


def lineas_pyg(periodos: list[Periodo]) -> list[dict]:
	"""Partidas y subtotales de la PyG en el orden del modelo."""
	por_codigo = {nodo["code"]: construir_arbol(nodo, periodos) for nodo in PYG}
	for linea in por_codigo.values():
		linea["tipo"] = "linea"
	for code, (label, sumandos) in SUBTOTALES_PYG.items():
		por_codigo[code] = {
			"code": code,
			"label": label,
			"tipo": "subtotal",
			"nivel": 0,
			"subtotal": True,
			"importes": _redondear(
				sum(por_codigo[s]["importes"][i] for s in sumandos) for i in range(len(periodos))
			),
			"hijos": [],
			"cuentas": [],
		}
	return [por_codigo[code] for code in ORDEN_PYG]


def totales_pyg_mensuales(mensual: dict[str, dict[str, float]], meses: list[str]) -> dict[str, list[float]]:
	"""Serie mensual de cada línea de primer nivel y de los subtotales."""
	padre = {}
	for nodo in PYG:
		padre[nodo["code"]] = nodo["code"]
		for hijo in nodo["hijos"]:
			padre[hijo["code"]] = nodo["code"]

	series: dict[str, list[float]] = {nodo["code"]: [0.0] * len(meses) for nodo in PYG}
	for i, mes in enumerate(meses):
		for hoja, importe in mensual.get(mes, {}).items():
			series[padre[hoja]][i] += importe
	for code, (_label, sumandos) in SUBTOTALES_PYG.items():
		series[code] = [sum(series[s][i] for s in sumandos) for i in range(len(meses))]
	return {code: _redondear(valores) for code, valores in series.items()}


def meses_entre(desde, hasta) -> list[str]:
	actual = getdate(desde).replace(day=1)
	fin = getdate(hasta)
	meses = []
	while actual <= fin:
		meses.append(actual.strftime("%Y-%m"))
		actual = getdate(add_months(actual, 1))
	return meses


def periodo_anterior(desde, hasta) -> tuple:
	return add_years(getdate(desde), -1), add_years(getdate(hasta), -1)


def masas_balance(activo: dict, pasivo: dict) -> list[dict]:
	"""Masas patrimoniales por periodo, a partir de los árboles ya construidos."""
	nodos: dict[str, dict] = {}

	def visitar(nodo):
		nodos[nodo["code"]] = nodo
		for hijo in nodo["hijos"]:
			visitar(hijo)

	visitar(activo)
	visitar(pasivo)
	n_periodos = len(activo["importes"])

	def valor(code, i):
		return nodos[code]["importes"][i] if code in nodos else 0.0

	masas = []
	for i in range(n_periodos):
		realizable = sum(valor(c, i) for c in ("B.I", "B.III", "B.IV", "B.V", "B.VI"))
		masas.append(
			{
				"anc": valor("A", i),
				"ac": valor("B", i),
				"existencias": valor("B.II", i),
				"realizable": round(realizable, 2),
				"disponible": valor("B.VII", i),
				"pn": valor("PN", i),
				"pnc": valor("PNC", i),
				"pc": valor("PC", i),
				"activo": valor("ACTIVO", i),
				"pasivo_total": valor("PNP", i),
			}
		)
	return masas


def _division(a: float, b: float):
	return round(a / b, 4) if abs(b) >= _EPS else None


def ratios_balance(masas: dict) -> dict:
	deuda = masas["pnc"] + masas["pc"]
	return {
		"fondo_maniobra": round(masas["ac"] - masas["pc"], 2),
		"liquidez": _division(masas["ac"], masas["pc"]),
		"acida": _division(masas["ac"] - masas["existencias"], masas["pc"]),
		"disponibilidad": _division(masas["disponible"], masas["pc"]),
		"endeudamiento": _division(deuda, masas["pn"] + deuda),
		"autonomia": _division(masas["pn"], deuda),
		"solvencia": _division(masas["activo"], deuda),
		"calidad_deuda": _division(masas["pc"], deuda),
	}


def kpis_pyg(lineas: list[dict], i: int) -> dict:
	valor = {linea["code"]: linea["importes"][i] for linea in lineas}
	cifra = valor["1"]
	ebitda = valor["A.1"] - valor["8"] - valor["11"]
	margen_bruto = cifra + valor["2"] + valor["4"]
	ingresos = sum(v for code, v in valor.items() if not code.startswith("A.") and v > 0)
	gastos = -sum(v for code, v in valor.items() if not code.startswith("A.") and v < 0)
	return {
		"cifra_negocios": round(cifra, 2),
		"margen_bruto": round(margen_bruto, 2),
		"ebitda": round(ebitda, 2),
		"resultado_explotacion": valor["A.1"],
		"resultado_financiero": valor["A.2"],
		"resultado_antes_impuestos": valor["A.3"],
		"resultado": valor["A.5"],
		"ingresos": round(ingresos, 2),
		"gastos": round(gastos, 2),
	}


# Sumas y saldos ------------------------------------------------------------------------


def calcular_sumas_y_saldos(company: str, desde, hasta, fy_inicio) -> dict:
	"""Saldo anterior, movimientos del periodo y saldo final por cuenta y por nivel PGC.

	El saldo anterior de las cuentas de resultados empieza en el ejercicio. Lo que
	arrastran de ejercicios sin cerrar se muestra en una fila calculada del subgrupo 12.
	"""
	desde, hasta, fy_inicio = getdate(desde), getdate(hasta), getdate(fy_inicio)
	finance_book = frappe.get_cached_value("Company", company, "default_finance_book") or ""
	filas = frappe.db.sql(
		"""
		SELECT g.account, a.account_number, a.account_name, a.root_type, a.account_type,
			IF(g.posting_date < %(desde)s, 1, 0) AS previo,
			IF(g.posting_date < %(fy_inicio)s, 1, 0) AS antes_ejercicio,
			SUM(g.debit) AS debe, SUM(g.credit) AS haber
		FROM `tabGL Entry` g
		INNER JOIN `tabAccount` a ON a.name = g.account
		WHERE g.company = %(company)s AND g.posting_date <= %(hasta)s
			AND g.is_cancelled = 0
			AND (g.finance_book IS NULL OR g.finance_book IN ('', %(finance_book)s))
		GROUP BY g.account, previo, antes_ejercicio
		""",
		{
			"company": company,
			"desde": desde,
			"hasta": hasta,
			"fy_inicio": fy_inicio,
			"finance_book": finance_book,
		},
		as_dict=True,
	)

	cuentas: dict[str, dict] = {}
	arrastre_resultados = 0.0
	for row in filas:
		numero = normalizar_numero(row.account_number)
		cuenta = cuentas.setdefault(
			row.account,
			{
				"account": row.account,
				"numero": numero,
				"nombre": row.account_name or row.account,
				"saldo_inicial": 0.0,
				"debe": 0.0,
				"haber": 0.0,
			},
		)
		neto = flt(row.debe) - flt(row.haber)
		if not row.previo:
			cuenta["debe"] += flt(row.debe)
			cuenta["haber"] += flt(row.haber)
		elif es_pyg(numero, row.root_type) and row.antes_ejercicio:
			arrastre_resultados += neto
		else:
			cuenta["saldo_inicial"] += neto

	hojas = []
	for cuenta in cuentas.values():
		cuenta["saldo_final"] = cuenta["saldo_inicial"] + cuenta["debe"] - cuenta["haber"]
		if any(abs(cuenta[k]) >= _EPS for k in ("saldo_inicial", "debe", "haber", "saldo_final")):
			hojas.append(cuenta)
	if abs(arrastre_resultados) >= _EPS:
		hojas.append(
			{
				"account": None,
				"numero": "120" if arrastre_resultados < 0 else "121",
				"nombre": _("Resultados de ejercicios anteriores sin asiento de cierre (calculado)"),
				"saldo_inicial": arrastre_resultados,
				"debe": 0.0,
				"haber": 0.0,
				"saldo_final": arrastre_resultados,
				"sintetica": True,
			}
		)

	nombres_compania = {
		row.account_number: row.account_name
		for row in frappe.get_all(
			"Account",
			filters={"company": company, "is_group": 1},
			fields=["account_number", "account_name"],
		)
		if row.account_number and len(row.account_number) <= 3
	}

	grupos: dict[str, dict] = {}
	filas_hoja = []
	for hoja in hojas:
		numero = hoja["numero"]
		cadena = [numero[:k] for k in (1, 2, 3) if k <= len(numero)] if numero else ["—"]
		for nivel, codigo in enumerate(cadena, start=1):
			grupo = grupos.setdefault(
				codigo,
				{
					"codigo": codigo,
					"nombre": nombre_pgc(codigo)
					or nombres_compania.get(codigo)
					or (_("Cuentas sin número") if codigo == "—" else _("Cuenta {0}").format(codigo)),
					"nivel": nivel,
					"padre": cadena[nivel - 2] if nivel > 1 else None,
					"es_grupo": True,
					"account": None,
					"saldo_inicial": 0.0,
					"debe": 0.0,
					"haber": 0.0,
					"saldo_final": 0.0,
				},
			)
			for campo in ("saldo_inicial", "debe", "haber", "saldo_final"):
				grupo[campo] += hoja[campo]
		filas_hoja.append(
			{
				"codigo": numero,
				"nombre": hoja["nombre"],
				"nivel": 4,
				"padre": cadena[-1],
				"es_grupo": False,
				"account": hoja["account"],
				"sintetica": hoja.get("sintetica", False),
				**{campo: hoja[campo] for campo in ("saldo_inicial", "debe", "haber", "saldo_final")},
			}
		)

	hijos: dict[str | None, list[dict]] = defaultdict(list)
	for fila in [*grupos.values(), *filas_hoja]:
		for campo in ("saldo_inicial", "debe", "haber", "saldo_final"):
			fila[campo] = round(fila[campo], 2)
		hijos[fila["padre"]].append(fila)

	def orden(fila):
		return (fila["codigo"] == "—", fila["codigo"] or "~", fila["nombre"])

	ordenadas: list[dict] = []

	def recorrer(padre):
		for fila in sorted(hijos.get(padre, []), key=orden):
			ordenadas.append(fila)
			if fila["es_grupo"]:
				recorrer(fila["codigo"])

	recorrer(None)

	def suma(campo, signo):
		return round(sum(max(signo * h[campo], 0) for h in hojas), 2)

	totales = {
		"saldo_inicial_deudor": suma("saldo_inicial", 1),
		"saldo_inicial_acreedor": suma("saldo_inicial", -1),
		"debe": round(sum(h["debe"] for h in hojas), 2),
		"haber": round(sum(h["haber"] for h in hojas), 2),
		"saldo_deudor": suma("saldo_final", 1),
		"saldo_acreedor": suma("saldo_final", -1),
	}
	return {
		"filas": ordenadas,
		"totales": totales,
		"cuadre": {
			"sumas": abs(totales["debe"] - totales["haber"]) < 0.01,
			"saldos": abs(totales["saldo_deudor"] - totales["saldo_acreedor"]) < 0.01,
		},
		"arrastre_resultados": round(arrastre_resultados, 2),
	}
