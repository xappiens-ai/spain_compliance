# Copyright (c) 2026, Xappiens and contributors
# License: MIT

"""Árbol de cuentas coherente con la numeración del PGC.

El padre de una cuenta numerada es el grupo cuyo número es el prefijo más
largo del suyo. Las cuentas auxiliares de 10 dígitos (el desarrollo que llega
de la migración) no cuelgan de un grupo que solo rellena con ceros un código
más corto: 4300000161 cuelga de 430, no de 4300. El cuadro (hasta 7 dígitos)
sí conserva esos grupos intermedios: 43100 cuelga de 4310.

Los grupos de 1, 2 y 3 dígitos toman el nombre del cuadro oficial
(``pgc.CUADRO``). No se cambia ``account_number``, ``root_type`` ni el mayor.
La operación es idempotente.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import frappe

from spain_compliance.contabilidad.pgc import CUADRO
from spain_compliance.contabilidad.plan_contable import GRUPOS, SUBGRUPOS, es_compania_pgc
from spain_compliance.setup.custom_fields import COMPANY_PGC_FIELDNAME

_META_PLANTILLA = {
	"account_name",
	"account_number",
	"account_type",
	"account_category",
	"root_type",
	"is_group",
	"tax_rate",
	"account_currency",
}
_CAMPOS_NODO = ("account_type", "tax_rate", "account_currency", "account_category")
_LARGO_AUXILIAR = 10
_LARGO_NOMBRE = 140

_PLANTILLA = Path(__file__).resolve().parent / "charts" / "es_pgce_con_numeros.json"


def es_codigo_relleno(codigo: str, grupos: set[str]) -> bool:
	"""True si ``codigo`` solo añade ceros a un grupo más corto ya existente.

	4300 es relleno de 430. 4301 no lo es. Un código de 3 dígitos o menos es
	cuenta del PGC y nunca se trata como relleno.
	"""
	if not codigo.isdigit() or len(codigo) <= 3:
		return False
	for largo in range(3, len(codigo)):
		base = codigo[:largo]
		if base in grupos and codigo[largo:] == "0" * (len(codigo) - largo):
			return True
	return False


def prefijos_obligatorios(numero: str) -> list[str]:
	"""Grupos 1, 2 y 3 dígitos que tienen que existir para colgar ``numero``."""
	if not numero.isdigit():
		return []
	prefs = []
	if len(numero) >= 2:
		prefs.append(numero[:1])
	if len(numero) >= 3:
		prefs.append(numero[:2])
	if len(numero) >= 4:
		prefs.append(numero[:3])
	return prefs


def padre_canonico(numero: str, grupos: set[str]) -> str | None:
	"""Número del grupo padre, o None si la cuenta es raíz (grupo 1-9)."""
	if not numero or not numero.isdigit() or len(numero) <= 1:
		return None
	candidatos = [numero[:i] for i in range(1, len(numero)) if numero[:i] in grupos]
	if len(numero) >= _LARGO_AUXILIAR and candidatos:
		bases = set(candidatos)
		candidatos = [c for c in candidatos if not es_codigo_relleno(c, bases)]
	if candidatos:
		return max(candidatos, key=len)
	if len(numero) <= 3:
		return numero[:-1]
	return numero[:3]


def nombre_de_grupo(codigo: str) -> str:
	"""Nombre oficial del grupo. Si el código no está en el cuadro, uno neutro."""
	if codigo in CUADRO:
		return CUADRO[codigo]
	if len(codigo) == 2 and codigo in SUBGRUPOS:
		return SUBGRUPOS[codigo][0]
	if len(codigo) == 1 and codigo in GRUPOS:
		return GRUPOS[codigo][0]
	return f"Cuenta {codigo}"


def root_type_de(codigo: str) -> str:
	"""root_type nominal del grupo. Los hijos pueden llevar otro."""
	if codigo in GRUPOS:
		return GRUPOS[codigo][1]
	sub = codigo[:2]
	if sub in SUBGRUPOS:
		return SUBGRUPOS[sub][1]
	raiz = codigo[:1]
	if raiz in GRUPOS:
		return GRUPOS[raiz][1]
	return "Asset"


def nombre_documento(numero: str, account_name: str, abbr: str) -> str:
	return f"{numero} - {account_name.strip()} - {abbr}"


def cabe_en_nombre(numero: str, account_name: str, abbr: str) -> bool:
	nombre = account_name.strip()
	return len(nombre) <= _LARGO_NOMBRE and len(nombre_documento(numero, nombre, abbr)) <= _LARGO_NOMBRE


def planificar(filas: list[dict], abbr: str) -> dict:
	"""Plan de altas, renombres y recolocaciones. No escribe en la base de datos.

	Cada fila lleva ``name``, ``number``, ``account_name``, ``is_group`` y
	``parent_number`` (vacío si el padre no tiene número o la cuenta es raíz).
	"""
	existentes: dict[str, dict] = {}
	duplicados: set[str] = set()
	for fila in filas:
		numero = fila["number"]
		if not numero.isdigit():
			continue
		if numero in existentes:
			duplicados.add(numero)
		existentes[numero] = fila

	necesarios: list[str] = []
	vistos: set[str] = set()
	for fila in filas:
		for pref in prefijos_obligatorios(fila["number"]):
			if pref in existentes or pref in vistos:
				continue
			vistos.add(pref)
			necesarios.append(pref)

	pedidos = set(vistos)
	for fila in filas:
		pedidos.update(prefijos_obligatorios(fila["number"]))

	promover = sorted(
		numero
		for numero, fila in existentes.items()
		if len(numero) <= 3 and not fila["is_group"] and numero in pedidos and numero not in duplicados
	)

	grupos = {numero for numero, fila in existentes.items() if fila["is_group"] and numero not in duplicados}
	grupos.update(necesarios)
	grupos.update(promover)

	renombrar = []
	choques = sorted(duplicados)
	for numero, fila in existentes.items():
		if numero not in CUADRO or numero in duplicados:
			continue
		canon = CUADRO[numero]
		if not cabe_en_nombre(numero, canon, abbr):
			choques.append(numero)
			continue
		if fila["account_name"] != canon or fila["name"] != nombre_documento(numero, canon, abbr):
			renombrar.append({"name": fila["name"], "number": numero, "account_name": canon})

	recolocar = []
	coherentes = 0
	omitidos = 0
	for fila in filas:
		numero = fila["number"]
		if not numero or not numero.isdigit():
			omitidos += 1
			continue
		if numero in duplicados:
			continue
		padre = padre_canonico(numero, grupos)
		if padre == numero:
			choques.append(numero)
			continue
		actual = fila["parent_number"] or None
		if actual == padre:
			coherentes += 1
			continue
		recolocar.append({"name": fila["name"], "number": numero, "parent_number": padre})

	renombrar.sort(key=lambda r: (len(r["number"]), r["number"]))
	recolocar.sort(key=lambda r: (len(r["number"]), r["number"]))
	return {
		"crear": necesarios,
		"promover": promover,
		"renombrar": renombrar,
		"recolocar": recolocar,
		"coherentes": coherentes,
		"omitidos": omitidos,
		"choques": choques,
		"recolocados_por_longitud": dict(Counter(len(r["number"]) for r in recolocar)),
	}


def resumen_plan(plan: dict) -> dict:
	return {
		"creados": len(plan["crear"]),
		"promovidos": len(plan["promover"]),
		"renombrados": len(plan["renombrar"]),
		"recolocados": len(plan["recolocar"]),
		"coherentes": plan["coherentes"],
		"omitidos": plan["omitidos"],
		"choques": plan["choques"],
		"recolocados_por_longitud": plan["recolocados_por_longitud"],
	}


def _filas(company: str) -> list[dict]:
	rows = frappe.db.sql(
		"""
		select a.name, a.account_number, a.account_name, a.is_group,
			ifnull(p.account_number, '') as parent_number
		from `tabAccount` a
		left join `tabAccount` p on p.name = a.parent_account
		where a.company = %s
		""",
		company,
		as_dict=True,
	)
	return [
		{
			"name": row.name,
			"number": (row.account_number or "").strip(),
			"account_name": (row.account_name or "").strip(),
			"is_group": int(row.is_group or 0),
			"parent_number": (row.parent_number or "").strip(),
		}
		for row in rows
	]


def _mapa_grupos(company: str) -> dict[str, str]:
	"""account_number → name, solo grupos con número."""
	rows = frappe.get_all(
		"Account",
		filters={"company": company, "is_group": 1},
		fields=["name", "account_number"],
	)
	return {
		(row.account_number or "").strip(): row.name for row in rows if (row.account_number or "").strip()
	}


def _crear_grupo(company: str, numero: str, mapa: dict[str, str]):
	padre = padre_canonico(numero, set(mapa) | {numero})
	parent_name = mapa.get(padre) if padre else None
	if padre and not parent_name:
		frappe.throw(f"No existe el grupo {padre} para crear {numero} en {company}")
	root_type = root_type_de(numero)
	doc = frappe.get_doc(
		{
			"doctype": "Account",
			"company": company,
			"account_name": nombre_de_grupo(numero),
			"account_number": numero,
			"is_group": 1,
			"root_type": root_type,
			"report_type": "Profit and Loss" if root_type in ("Income", "Expense") else "Balance Sheet",
			"parent_account": parent_name,
		}
	)
	doc.flags.ignore_permissions = True
	if not parent_name:
		doc.flags.ignore_mandatory = True
	doc.insert(ignore_permissions=True)
	mapa[numero] = doc.name


def _renombrar(company: str, item: dict, abbr: str) -> str:
	numero = item["number"]
	canon = item["account_name"]
	nuevo = nombre_documento(numero, canon, abbr)
	actual = item["name"]
	if frappe.db.get_value("Account", actual, "account_name") != canon:
		frappe.db.set_value("Account", actual, "account_name", canon, update_modified=False)
	if actual == nuevo:
		return actual
	if frappe.db.exists("Account", nuevo):
		frappe.throw(f"Ya existe la cuenta {nuevo}; no se renombra {numero} para no fusionar saldos")
	from frappe.model.rename_doc import rename_doc

	return rename_doc(
		doctype="Account",
		old=actual,
		new=nuevo,
		force=True,
		merge=False,
		ignore_permissions=True,
		show_alert=False,
		rebuild_search=False,
	)


def _aplicar(company: str, plan: dict, abbr: str):
	for numero in plan["promover"]:
		name = frappe.db.get_value("Account", {"company": company, "account_number": numero}, "name")
		if name:
			frappe.db.set_value("Account", name, "is_group", 1, update_modified=False)

	mapa = _mapa_grupos(company)
	for numero in sorted(plan["crear"], key=lambda n: (len(n), n)):
		if numero in mapa:
			continue
		_crear_grupo(company, numero, mapa)

	for indice, item in enumerate(plan["renombrar"], start=1):
		_renombrar(company, item, abbr)
		if indice % 50 == 0:
			frappe.db.commit()

	# Los nombres ya son los definitivos: se recalcula el padre y se mueve.
	filas = _filas(company)
	pendiente = planificar(filas, abbr)
	if pendiente["crear"] or pendiente["renombrar"] or pendiente["promover"] or pendiente["choques"]:
		frappe.throw(
			f"La alineación de {company} no pudo dejar los grupos listos ({resumen_plan(pendiente)})"
		)

	mapa = _mapa_grupos(company)
	movidos = 0
	for item in pendiente["recolocar"]:
		padre = item["parent_number"]
		parent_name = mapa.get(padre) if padre else None
		if padre and not parent_name:
			frappe.throw(f"No existe el grupo {padre} para recolocar {item['number']} en {company}")
		if parent_name:
			frappe.db.set_value("Account", item["name"], "parent_account", parent_name, update_modified=False)
		else:
			frappe.db.sql("update `tabAccount` set parent_account=null where name=%s", item["name"])
		movidos += 1
		if movidos % 400 == 0:
			frappe.db.commit()

	if pendiente["recolocar"] or plan["crear"] or plan["promover"]:
		from frappe.utils.nestedset import rebuild_tree

		rebuild_tree("Account")
	frappe.db.commit()
	frappe.clear_cache(doctype="Account")


def alinear_arbol_pgc(company: str, aplicar: bool = True) -> dict:
	"""Alinea el árbol de ``company`` con el PGC. Con ``aplicar=False`` solo informa."""
	if not es_compania_pgc(company):
		return {"company": company, "omitida": True}

	abbr = frappe.get_cached_value("Company", company, "abbr")
	plan = planificar(_filas(company), abbr)
	resultado = {"company": company, **resumen_plan(plan)}
	if not aplicar:
		return resultado
	if plan["choques"]:
		frappe.throw(
			f"No se alinea {company}: hay números duplicados o nombres que no caben ({', '.join(plan['choques'])})"
		)
	if not (plan["crear"] or plan["promover"] or plan["renombrar"] or plan["recolocar"]):
		return resultado

	_aplicar(company, plan, abbr)
	resto = planificar(_filas(company), abbr)
	resultado["pendiente"] = resumen_plan(resto)
	if any(resto[clave] for clave in ("crear", "promover", "renombrar", "recolocar", "choques")):
		frappe.throw(f"El árbol de {company} sigue incoherente tras alinearlo ({resultado['pendiente']})")
	return resultado


def alinear_companias_pgc(aplicar: bool = True) -> list[dict]:
	"""Alinea todas las compañías marcadas como PGC. No hace nada si ya cuadra."""
	if not frappe.db.has_column("Company", COMPANY_PGC_FIELDNAME):
		return []
	companies = frappe.get_all(
		"Company",
		filters={COMPANY_PGC_FIELDNAME: 1},
		pluck="name",
		order_by="name asc",
	)
	return [alinear_arbol_pgc(company, aplicar=aplicar) for company in companies]


# Plantilla -----------------------------------------------------------------


def _hijos_plantilla(nodo: dict) -> dict:
	return {k: v for k, v in nodo.items() if k not in _META_PLANTILLA and isinstance(v, dict)}


def _aplanar_plantilla(arbol: dict) -> list[dict]:
	nodos = []

	def walk(nodo):
		for nombre, hijo in _hijos_plantilla(nodo).items():
			nodos.append(
				{
					"number": str(hijo.get("account_number") or "").strip(),
					"name": nombre,
					"root_type": hijo.get("root_type"),
					"is_group": hijo.get("is_group") or 0,
					"extra": {campo: hijo.get(campo) for campo in _CAMPOS_NODO if hijo.get(campo)},
				}
			)
			walk(hijo)

	walk(arbol)
	return nodos


def plantilla_coherente(data: dict) -> dict:
	"""Reconstruye la plantilla anidando por número y con los nombres del cuadro."""
	nodos = {nodo["number"]: nodo for nodo in _aplanar_plantilla(data["tree"]) if nodo["number"]}
	for numero in list(nodos):
		for pref in prefijos_obligatorios(numero):
			if pref in nodos:
				continue
			nodos[pref] = {
				"number": pref,
				"name": nombre_de_grupo(pref),
				"root_type": root_type_de(pref),
				"is_group": 1,
				"extra": {},
			}

	grupos = set(nodos)
	hijos: dict[str | None, list[str]] = {}
	for numero in nodos:
		padre = padre_canonico(numero, grupos)
		hijos.setdefault(padre, []).append(numero)

	def construir(padre: str | None) -> dict:
		arbol = {}
		usados: set[str] = set()
		for numero in sorted(hijos.get(padre) or [], key=lambda n: (len(n), n)):
			nodo = nodos[numero]
			base = CUADRO[numero] if numero in CUADRO else nodo["name"]
			clave = base if base not in usados else f"{base} ({numero})"
			usados.add(clave)
			entrada = construir(numero)
			entrada.update(nodo["extra"])
			entrada["account_number"] = numero
			if nodo.get("root_type"):
				entrada["root_type"] = nodo["root_type"]
			else:
				entrada["root_type"] = root_type_de(numero)
			entrada["is_group"] = 1 if _hijos_plantilla(entrada) or nodo.get("is_group") else 0
			arbol[clave] = entrada
		return arbol

	return {
		"country_code": data.get("country_code"),
		"name": data.get("name"),
		"tree": construir(None),
	}


def auditar_plantilla(data: dict) -> list[str]:
	"""Incoherencias de la plantilla: prefijo, nombre oficial y claves repetidas."""
	problemas = []
	numeros = [nodo["number"] for nodo in _aplanar_plantilla(data["tree"])]
	if len(numeros) != len(set(numeros)):
		problemas.append("hay números de cuenta repetidos")
	grupos = set(numeros)

	def walk(nodo, padre: str):
		claves = []
		for clave, hijo in _hijos_plantilla(nodo).items():
			numero = str(hijo.get("account_number") or "")
			claves.append(clave)
			esperado = padre_canonico(numero, grupos) or ""
			if esperado != padre:
				problemas.append(
					f"{numero} cuelga de {padre or 'raíz'} y debería colgar de {esperado or 'raíz'}"
				)
			if numero in CUADRO and clave not in (CUADRO[numero], f"{CUADRO[numero]} ({numero})"):
				problemas.append(f"{numero} se llama {clave}")
			if _hijos_plantilla(hijo) and hijo.get("is_group") != 1:
				problemas.append(f"{numero} tiene hijos y no es grupo")
			walk(hijo, numero)
		if len(claves) != len(set(claves)):
			problemas.append(f"nombres repetidos bajo {padre or 'raíz'}")

	walk(data["tree"], "")
	return problemas


def escribir_plantilla(ruta: str | None = None) -> dict:
	"""Regenera la plantilla del repositorio. La deja igual si ya es coherente."""
	path = Path(ruta) if ruta else _PLANTILLA
	data = json.loads(path.read_text())
	nuevo = plantilla_coherente(data)
	problemas = auditar_plantilla(nuevo)
	if problemas:
		frappe.throw(f"La plantilla regenerada no es coherente: {'; '.join(problemas[:8])}")
	path.write_text(json.dumps(nuevo, ensure_ascii=False, indent=1) + "\n")
	return {"ruta": str(path), "nodos": len(_aplanar_plantilla(nuevo["tree"])), "problemas": 0}
