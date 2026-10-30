# Copyright (c) 2026, Xappiens and contributors
# License: MIT

"""NIF, NIE, CIF y NIF-IVA. Aviso al guardar el tercero, sin bloquear el alta.

Así una ficha antigua con el identificador mal cargado se puede seguir editando.
"""

from __future__ import annotations

import re

import frappe
from frappe import _

from spain_compliance.contabilidad.clasificacion import TIPOS_IDENTIFICACION_SIN_NIF

_LETRAS_NIF = "TRWAGMYFPDXBNJZSQVHLCKE"
_LETRAS_CIF = "JABCDEFGHI"
# P, Q y S llevan letra de control; A, B, E y H, dígito; el resto admite los dos.
_CIF_LETRA = frozenset("PQS")
_CIF_DIGITO = frozenset("ABEH")
_NIF_IVA = re.compile(r"^[A-Z]{2}[A-Z0-9+*]{2,15}$")


def normalizar_identificador(valor: str | None) -> str:
	if not valor:
		return ""
	return re.sub(r"[\s.\-]", "", valor).upper()


def nif_espanol_valido(valor: str | None) -> bool:
	"""DNI (8 dígitos + letra), NIE (X/Y/Z) o CIF."""
	nif = normalizar_identificador(valor)
	if re.fullmatch(r"\d{8}[A-Z]", nif):
		return nif[-1] == _LETRAS_NIF[int(nif[:8]) % 23]
	if re.fullmatch(r"[XYZ]\d{7}[A-Z]", nif):
		numero = int(nif[:8].replace("X", "0").replace("Y", "1").replace("Z", "2"))
		return nif[-1] == _LETRAS_NIF[numero % 23]
	return _cif_valido(nif)


def _cif_valido(cif: str) -> bool:
	if not re.fullmatch(r"[ABCDEFGHJNPQRSUVW]\d{7}[0-9A-J]", cif):
		return False
	digitos = cif[1:8]
	pares = sum(int(digitos[i]) for i in (1, 3, 5))
	impares = 0
	for i in (0, 2, 4, 6):
		doble = int(digitos[i]) * 2
		impares += doble // 10 + doble % 10
	control = (10 - ((pares + impares) % 10)) % 10
	esperado_digito = str(control)
	esperado_letra = _LETRAS_CIF[control]
	recibido = cif[8]
	if cif[0] in _CIF_LETRA:
		return recibido == esperado_letra
	if cif[0] in _CIF_DIGITO:
		return recibido == esperado_digito
	return recibido in (esperado_digito, esperado_letra)


def nif_iva_valido(valor: str | None) -> bool:
	"""NIF-IVA: prefijo de país + identificador. Si el país es ES, el resto es un NIF."""
	nif = normalizar_identificador(valor)
	if not _NIF_IVA.fullmatch(nif):
		return False
	if nif.startswith("ES"):
		return nif_espanol_valido(nif[2:])
	return True


def validate_party(doc, method=None):
	"""Aviso (no bloqueo) si el tax_id no cuadra con el tipo de identificación."""
	identificador = normalizar_identificador(doc.get("tax_id"))
	if not identificador:
		return

	tipo = doc.get("tipo_identificacion_fiscal")
	if tipo in TIPOS_IDENTIFICACION_SIN_NIF:
		return

	if tipo == "NIF-IVA":
		valido = nif_iva_valido(identificador)
		esperado = _("un NIF-IVA (país + identificador; ES seguido de un NIF válido)")
	elif tipo == "NIF":
		valido = nif_espanol_valido(identificador)
		esperado = _("un NIF, NIE o CIF con el dígito de control correcto")
	else:
		# Sin tipo: solo avisar cuando tiene pinta de identificador español.
		if not re.match(r"^(\d{8}[A-Z]|[XYZ]\d{7}[A-Z]|[ABCDEFGHJNPQRSUVW]\d{7}[0-9A-J])$", identificador):
			return
		valido = nif_espanol_valido(identificador)
		esperado = _("un NIF, NIE o CIF válido, o indica otro tipo de identificación")

	if valido:
		return

	frappe.msgprint(
		_("El identificador fiscal {0} de {1} no parece {2}.").format(
			frappe.bold(identificador), frappe.bold(doc.get("customer_name") or doc.get("supplier_name") or doc.name), esperado
		),
		indicator="orange",
		alert=True,
		title=_("Identificación fiscal"),
	)
