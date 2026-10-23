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

		if (frm.doc.country === "Spain" || frm.doc.pgc_espanol) {
			const puedeReconstruir =
				frappe.user.has_role("Accounts Manager") ||
				frappe.user.has_role("System Manager");
			if (puedeReconstruir) {
				frm.add_custom_button(
					__("Reconstruir registro fiscal de IVA"),
					() => reconstruirRegistroFiscal(frm),
					__("Contabilidad España")
				);
			}
		}

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

function reconstruirRegistroFiscal(frm) {
	frappe.call({
		method: "spain_compliance.contabilidad.registro_fiscal.reconstruir_registro_fiscal",
		args: { company: frm.doc.name, dry_run: 1 },
		freeze: true,
		callback(r) {
			const resumen = r.message || {};
			frappe.confirm(
				__(
					"Vista previa de {0}: {1} facturas, {2} filas de registro, {3} pendientes de clasificar, {4} anuladas y {5} errores.<br><br>Reconstruir sustituye el registro vigente de las facturas validadas. Las que no tengan clasificación en la fila de impuesto la toman de su plantilla. ¿Continuar?",
					[
						frm.doc.name.bold(),
						resumen.facturas || 0,
						resumen.filas || 0,
						resumen.sin_clasificar || 0,
						resumen.anuladas || 0,
						resumen.errores || 0,
					]
				),
				() => {
					frappe.call({
						method: "spain_compliance.contabilidad.registro_fiscal.reconstruir_registro_fiscal",
						args: { company: frm.doc.name, dry_run: 0 },
						freeze: true,
						callback() {
							frappe.show_alert({
								message: __(
									"Reconstrucción del registro fiscal en curso. Recibirás un aviso al terminar."
								),
								indicator: "blue",
							});
						},
					});
				}
			);
		},
	});
}
