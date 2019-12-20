# -*- coding: utf-8 -*-


import frappe
from frappe import _

@frappe.whitelist()
def before_naming(self, method):
	override_bom_autoname(self)

def override_bom_autoname(self):
	from erpnext.manufacturing.doctype.bom.bom import BOM
	BOM.autoname = bom_autoname

def bom_autoname(self):
	self.name = 'BOM-' + self.merge + "-" + self.item
	
def on_submit(self, method):
	for row in self.items:
		has_batch_no = frappe.db.get_value('Item', row.item_code, 'has_batch_no')
		if has_batch_no:
			if not row.get('merge'):
				frappe.throw(_("Please set Merge in row {}").format(row.idx))