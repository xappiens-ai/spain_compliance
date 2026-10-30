// Copyright (c) 2026, Xappiens and contributors
// License: MIT

const LOSS_STATUSES = ["Dudoso Cobro", "Pérdida"];

frappe.ui.form.on("Sales Invoice", {
	is_return(frm) {
		apply_return_naming_series(frm);
	},
	company(frm) {
		if (frm.doc.is_return) {
			apply_return_naming_series(frm);
		}
	},
	refresh(frm) {
		if (frm.doc.docstatus === 0 && frm.doc.is_return) {
			apply_return_naming_series(frm);
		}
		if (frm.doc.docstatus !== 1 || frm.doc.is_return) {
			return;
		}

		const outstanding = flt(frm.doc.outstanding_amount);
		const group = __("Estado de cobro");

		if (outstanding > 0.01 && !LOSS_STATUSES.includes(frm.doc.status)) {
			frm.add_custom_button(__("Dudoso Cobro"), () => set_cobro_status(frm, "Dudoso Cobro"), group);
			frm.add_custom_button(__("Pérdida"), () => set_cobro_status(frm, "Pérdida"), group);
		}

		if (LOSS_STATUSES.includes(frm.doc.status)) {
			frm.add_custom_button(__("Restaurar estado de cobro"), () => set_cobro_status(frm, "clear"), group);
		}
	},
});

async function apply_return_naming_series(frm) {
	if (!frm.doc.is_return || !frm.doc.company || frm.doc.docstatus !== 0 || !frm.is_new()) {
		return;
	}

	const { message } = await frappe.db.get_value("Company", frm.doc.company, "serie_rectificativas");
	const target = (message && message.serie_rectificativas || "").trim();
	if (!target) {
		return;
	}

	const current = (frm.doc.naming_series || "").trim();
	if (current === target) {
		return;
	}

	const default_series = get_default_naming_series(frm);
	let original_series = null;
	if (frm.doc.return_against) {
		const r = await frappe.db.get_value("Sales Invoice", frm.doc.return_against, "naming_series");
		original_series = r.message && r.message.naming_series;
	}

	if (!current || current === original_series || current === default_series) {
		frm.set_value("naming_series", target);
	}
}

function get_default_naming_series(frm) {
	const df = frappe.meta.get_docfield("Sales Invoice", "naming_series", frm.doc.name);
	if (!df) {
		return null;
	}
	if (df.default) {
		return df.default;
	}
	const options = (df.options || "").split("\n").filter(Boolean);
	return options.length ? options[0] : null;
}

function set_cobro_status(frm, status) {
	return frappe
		.call({
			method: "spain_compliance.overrides.sales_invoice.set_cobro_status",
			args: { name: frm.doc.name, status },
			freeze: true,
		})
		.then((r) => {
			if (r.message) {
				frappe.show_alert({
					message: __("Estado: {0}", [__(r.message.status)]),
					indicator: "green",
				});
				frm.reload_doc();
			}
		});
}
