__version__ = "0.3.0"

# Parches de informes financieros para el árbol PGC de 9 grupos.
# Se aplican al cargar la app (antes de que se importen los módulos de informes).
try:
	from spain_compliance.monkey_patches import aplicar as _aplicar_parches

	_aplicar_parches()
except Exception:
	# Durante builds/instalaciones parciales erpnext puede no estar disponible.
	pass

try:
	from spain_compliance.contabilidad.chart_loader import patch_erpnext_charts

	patch_erpnext_charts()
except Exception:
	pass
