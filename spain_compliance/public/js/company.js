// Copyright (c) 2026, Xappiens and contributors
// License: MIT

frappe.ui.form.on("Company", {
	refresh(frm) {
		if (frm.is_new() || !frm.has_perm("write")) {
			return;
		}

		frm.add_custom_button(
			__("Convertir plan a PGC (9 grupos)"),
			() => {
				frappe.confirm(
					__(
						"Se crearán los grupos 1-9 y subgrupos del Plan General Contable, se recolocarán las cuentas numeradas por prefijo y se eliminarán (o desactivarán) las cuentas heredadas del plan estándar de ERPNext.<br><br><b>Haz una copia de seguridad antes.</b> ¿Continuar con {0}?",
						[frm.doc.name.bold()]
					),
					() => {
						frappe.call({
							method: "spain_compliance.contabilidad.plan_contable.convertir_plan_a_pgc",
							args: { company: frm.doc.name },
							freeze: true,
							callback() {
								frappe.show_alert({
									message: __("Conversión al PGC en curso. Recibirás un aviso al terminar."),
									indicator: "blue",
								});
							},
						});
					}
				);
			},
			__("Contabilidad España")
		);
	},
});
