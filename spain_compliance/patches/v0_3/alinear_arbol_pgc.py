# Copyright (c) 2026, Xappiens and contributors
# License: MIT

"""Alinea el árbol de cuentas de las compañías PGC con la numeración oficial.

Idempotente. No modifica números de cuenta ni asientos.
"""

from spain_compliance.contabilidad.arbol_pgc import alinear_companias_pgc


def execute():
	alinear_companias_pgc()
