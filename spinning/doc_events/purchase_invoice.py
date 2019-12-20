# -*- coding: utf-8 -*-


import frappe

from spinning.controllers.batch_controller import set_batches

@frappe.whitelist()
def validate(self, method):
	if self.update_stock:
		set_batches(self, 'warehouse')
