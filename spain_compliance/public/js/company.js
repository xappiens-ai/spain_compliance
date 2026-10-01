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

		const backfill = [
			["crear_cuenta_cliente_auto", "Customer", __("Crear cuentas de clientes pendientes")],
			["crear_cuenta_proveedor_auto", "Supplier", __("Crear cuentas de proveedores pendientes")],
		];
		for (const [field, party_type, label] of backfill) {
			if (!frm.doc.pgc_espanol || !frm.doc[field]) {
				continue;
			}
			frm.add_custom_button(
				label,
				() => {
					frappe.confirm(
						__(
							"Se creará la cuenta contable de cada tercero con movimientos en {0} que aún no la tenga, siguiendo la secuencia configurada. ¿Continuar?",
							[frm.doc.name.bold()]
						),
						() => {
							frappe.call({
								method: "spain_compliance.contabilidad.cuentas_tercero.crear_cuentas_pendientes_desde_company",
								args: { company: frm.doc.name, party_type },
								freeze: true,
								callback() {
									frappe.show_alert({
										message: __("Creación de cuentas en curso. Recibirás un aviso al terminar."),
										indicator: "blue",
									});
								},
							});
						}
					);
				},
				__("Contabilidad España")
			);
		}
	},
});
