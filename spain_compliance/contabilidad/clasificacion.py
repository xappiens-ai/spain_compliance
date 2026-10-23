# Copyright (c) 2026, Xappiens and contributors
# License: MIT

"""Códigos fiscales estables (IVA, retenciones, identificación).

El valor guardado en los Select es ``código - descripción``. ``codigo()``
devuelve solo el código, que es lo que usarán los libros y los modelos.
"""

from __future__ import annotations

TIPO_IVA = "IVA"
TIPO_RE = "Recargo de equivalencia"
TIPO_RETENCION = "Retención IRPF"
TIPO_IGIC = "IGIC"
TIPO_IPSI = "IPSI"
TIPO_OTRO = "Otro"

TIPOS_IVA = (TIPO_IVA, TIPO_RE)
# Llevan clave de operación y, en compras, deducibilidad. La prorrata se aplica a todos.
TIPOS_CON_CLAVE = (TIPO_IVA, TIPO_RE, TIPO_IGIC, TIPO_IPSI)

DEDUCIBLE_CORRIENTE = "Corriente"
DEDUCIBLE_BIEN = "Bien de inversión"
DEDUCIBLE_NO = "No deducible"

LIBRO_EXPEDIDAS = "Expedidas"
LIBRO_RECIBIDAS = "Recibidas"


def etiqueta(codigo: str, nombre: str) -> str:
	return f"{codigo} - {nombre}"


def codigo(valor: str | None) -> str:
	"""``S1 - Sujeta no exenta`` → ``S1``. Vacío si no hay valor."""
	if not valor:
		return ""
	return valor.split(" - ", 1)[0].strip()


def _opciones(pares: list[tuple[str, str]]) -> str:
	return "\n" + "\n".join(etiqueta(codigo, nombre) for codigo, nombre in pares)


CLAVES_IVA: list[tuple[str, str]] = [
	("S1", "Sujeta no exenta"),
	("E1", "Exenta art. 20"),
	("E2", "Exenta art. 21"),
	("E3", "Exenta art. 22"),
	("E4", "Exenta arts. 23 y 24"),
	("E5", "Exenta art. 25"),
	("E6", "Exenta otros"),
	("N1", "No sujeta arts. 7 y 14"),
	("N2", "No sujeta por reglas de localización"),
	("ISP", "Inversión del sujeto pasivo"),
	("AIB", "Adquisición intracomunitaria de bienes"),
	("AIS", "Adquisición intracomunitaria de servicios"),
	("IMP", "Importación"),
	("EIB", "Entrega intracomunitaria"),
	("EXP", "Exportación"),
	("SEU", "Servicios localizados en la UE"),
]

CLAVES_RETENCION: list[tuple[str, str]] = [
	("A", "Rendimientos del trabajo dinerarios"),
	("B", "Rendimientos del trabajo en especie"),
	("F", "Actividades económicas dinerarias"),
	("G", "Actividades económicas en especie"),
	("H", "Arrendamiento de inmuebles urbanos"),
	("C", "Capital mobiliario"),
	("P", "Premios"),
]

TIPO_IMPUESTO_OPTIONS = "\n" + "\n".join([TIPO_IVA, TIPO_RE, TIPO_RETENCION, TIPO_IGIC, TIPO_IPSI, TIPO_OTRO])
CLAVE_IVA_OPTIONS = _opciones(CLAVES_IVA)
CLAVE_RETENCION_OPTIONS = _opciones(CLAVES_RETENCION)
DEDUCIBLE_OPTIONS = "\n" + "\n".join([DEDUCIBLE_CORRIENTE, DEDUCIBLE_BIEN, DEDUCIBLE_NO])

CLAVE_SUJETA = etiqueta("S1", "Sujeta no exenta")
CLAVE_RETENCION_PROFESIONAL = etiqueta("F", "Actividades económicas dinerarias")

REGIMEN_IVA_OPTIONS = "\n".join(
	["General", "Criterio de caja", "Recargo de equivalencia", "Régimen simplificado"]
)
PERIODICIDAD_303_OPTIONS = "\n".join(["Trimestral", "Mensual"])
MODELO_CUENTAS_OPTIONS = "\n".join(["PYMES", "Abreviado", "Normal"])

TIPO_IDENTIFICACION_OPTIONS = "\n" + "\n".join(
	[
		"NIF",
		"NIF-IVA",
		"Pasaporte",
		"Documento oficial",
		"Certificado de residencia",
		"Otro",
	]
)

# No se valida el dígito de control: no son identificadores españoles.
TIPOS_IDENTIFICACION_SIN_NIF = frozenset(
	{"Pasaporte", "Documento oficial", "Certificado de residencia", "Otro"}
)
