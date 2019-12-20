# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from . import __version__ as app_version

app_name = "spinning"
app_title = "Spinning"
app_publisher = "FinByz Tech Pvt Ltd"
app_description = "Custom app for spinning app"
app_icon = "/public/files/cone-yarn.png"
app_color = "Orange"
app_email = "info@finbyz.com"
app_license = "GPL 3.0"

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/spinning/css/spinning.css"
# app_include_js = "/assets/spinning/js/spinning.js"

app_include_js = [
	"/assets/spinning/js/report_actions.js"
]

# include js, css files in header of web template
# web_include_css = "/assets/spinning/css/spinning.css"
# web_include_js = "/assets/spinning/js/spinning.js"

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

doctype_js = {
	"Purchase Receipt": "public/js/doctype_js/purchase_receipt.js",
	"Purchase Invoice": "public/js/doctype_js/purchase_invoice.js",
	"Sales Invoice": "public/js/doctype_js/sales_invoice.js",
	"Delivery Note": "public/js/doctype_js/delivery_note.js",
	"Stock Reconciliation": "public/js/doctype_js/stock_reconciliation.js",
	"Purchase Order": "public/js/doctype_js/purchase_order.js",
	"Quality Inspection": "public/js/doctype_js/quality_inspection.js"
}

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
#	"Role": "home_page"
# }

# Website user home page (by function)
# get_website_user_home_page = "spinning.utils.get_home_page"

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Installation
# ------------

# before_install = "spinning.install.before_install"
# after_install = "spinning.install.after_install"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "spinning.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
#	}
# }

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"spinning.tasks.all"
# 	],
# 	"daily": [
# 		"spinning.tasks.daily"
# 	],
# 	"hourly": [
# 		"spinning.tasks.hourly"
# 	],
# 	"weekly": [
# 		"spinning.tasks.weekly"
# 	]
# 	"monthly": [
# 		"spinning.tasks.monthly"
# 	]
# }

doc_events = {
	"Stock Entry": {
		"validate": "spinning.doc_events.stock_entry.validate",
		'before_save': "spinning.doc_events.stock_entry.before_save",
	},

	"Batch": {
		'before_naming': "spinning.doc_events.batch.before_naming",
	},

	"Purchase Receipt": {
		"validate": "spinning.doc_events.purchase_receipt.validate",
		"on_submit": "spinning.doc_events.purchase_receipt.on_submit",
		"on_cancel": "spinning.doc_events.purchase_receipt.on_cancel",
		"before_save": "spinning.doc_events.purchase_receipt.before_save",
	},
	
	"Purchase Invoice": {
		"validate": "spinning.doc_events.purchase_invoice.validate",
	},

	"BOM": {
		"before_naming": "spinning.doc_events.bom.before_naming",
		"validate": "spinning.controllers.merge_validation.validate_merge",
		"on_submit":  "spinning.doc_events.bom.on_submit",
	},

	"Delivery Note": {
		"before_validate": "spinning.doc_events.delivery_note.before_validate",
		"before_save": "spinning.doc_events.delivery_note.before_save",
		"on_submit": "spinning.doc_events.delivery_note.on_submit",
		"on_cancel": "spinning.doc_events.delivery_note.on_cancel",
	},

	"Work Order": {
		"validate": "spinning.controllers.merge_validation.validate_merge",
		"before_save": "spinning.doc_events.work_order.before_save",
		"on_submit": "spinning.doc_events.work_order.on_submit",
	},

	"Item": {
		"validate": "spinning.doc_events.item.validate",
	},

	"Stock Reconciliation": {
		"validate": "spinning.doc_events.stock_reconciliation.validate",
		"on_submit": "spinning.doc_events.stock_reconciliation.on_submit",
		"on_cancel": "spinning.doc_events.stock_reconciliation.on_cancel",
	},

}


# Testing
# -------

# before_tests = "spinning.install.before_tests"

# Overriding Whitelisted Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "spinning.event.get_events"
# }

