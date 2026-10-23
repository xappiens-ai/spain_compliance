# Copyright (c) 2026, Xappiens and contributors
# License: MIT

from frappe.model.document import Document


class RegistroFiscalIVA(Document):
	"""Fila generada al validar una factura. El cálculo vive en ``registro_fiscal``."""
