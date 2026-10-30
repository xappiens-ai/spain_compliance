# Copyright (c) 2026, Xappiens and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.translate import get_messages_for_boot
from frappe.utils import cint, get_system_timezone

no_cache = 1


def get_context():
	from spain_compliance.api.permission import has_app_permission

	if frappe.session.user == "Guest":
		frappe.local.flags.redirect_location = "/login?redirect-to=/contabilidad"
		raise frappe.Redirect

	if not has_app_permission():
		frappe.throw(_("No tienes permiso para acceder a Contabilidad"), frappe.PermissionError)

	context = frappe._dict()
	context.boot = get_boot()
	return context


@frappe.whitelist(methods=["POST"], allow_guest=True)
def get_context_for_dev():
	if not frappe.conf.developer_mode:
		frappe.throw(_("This method is only meant for developer mode"))
	return get_boot()


def get_boot():
	csrf_token = ""
	if getattr(frappe.local, "session_obj", None):
		csrf_token = frappe.sessions.get_csrf_token()

	return frappe._dict(
		{
			"frappe_version": frappe.__version__,
			"default_route": "/contabilidad",
			"site_name": frappe.local.site,
			"socketio_port": frappe.conf.socketio_port,
			"csrf_token": csrf_token,
			"setup_complete": cint(frappe.get_system_settings("setup_complete")),
			"sysdefaults": frappe.defaults.get_defaults(),
			"translated_messages": get_messages_for_boot(),
			"user": {
				"name": frappe.session.user,
				"full_name": frappe.utils.get_fullname(),
				"user_image": frappe.db.get_value("User", frappe.session.user, "user_image"),
			},
			"timezone": {
				"system": get_system_timezone(),
				"user": frappe.db.get_value("User", frappe.session.user, "time_zone")
				or get_system_timezone(),
			},
		}
	)
