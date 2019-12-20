# -*- coding: utf-8 -*-
# Copyright (c) 2019, FinByz Tech Pvt Ltd and contributors
# For license information, please see license.txt


import frappe
from frappe.model.document import Document
from spinning.controllers.batch_controller import get_batch_no
from frappe.model.rename_doc import rename_doc

class CombineMerge(Document):
	def before_save(self):
		# if self.from_merge_item_code != self.to_merge_item_code:
			# frappe.throw(_("Not allowed to combine merge with different item"))
		self.get_batch_detail()

	def get_batch_detail(self):
		batches = frappe.get_list("Batch",{'item':self.from_merge_item_code,'merge':self.from_merge})
		
		self.details = ''
		for d in batches:
			doc = frappe.get_doc('Batch',d)
			self.append('details',({
				'batch_no': doc.name,
				'item_code': doc.item,
				'grade': doc.grade,
			}))
		for row in self.details:
			has_batch_no = frappe.db.get_value('Item', row.item_code, 'has_batch_no')
			if has_batch_no:
				args = {}
				args['item_code'] = row.item_code
				args['merge'] = self.to_merge
				args['grade'] = row.grade
				row.to_merge_batch = get_batch_no(args)
				

	def on_submit(self):
		for row in self.details:
			if row.to_merge_batch:
				try:
					rename_doc("Merge", self.from_merge, self.to_merge, merge=True, ignore_permissions=True)
					rename_doc("Batch", row.batch_no, row.to_merge_batch, merge=True, ignore_permissions=True)
					frappe.db.sql("""
					 update `tabStock Ledger Entry` set batch_no = %s where batch_no = %s;
					""",(row.to_merge_batch,row.batch_no))
				except Exception as e:
					frappe.throw(str(e))
					
	def on_cancel(self):
		frappe.throw(_("Not allowed to cancel the document"))
		
	