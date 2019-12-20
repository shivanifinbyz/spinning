# -*- coding: utf-8 -*-
# Copyright (c) 2019, FinByz Tech Pvt Ltd and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.utils import flt, get_link_to_form
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc
from spinning.controllers.batch_controller import get_batch_no
from datetime import datetime
from spinning.controllers.merge_validation import validate_merge

class MaterialUnpack(Document):
	def validate(self):	
		validate_merge(self)
		date = datetime.strptime(self.posting_date, '%Y-%m-%d').date()
		cd   = datetime.date(datetime.now())
		if date > cd:
			frappe.throw(_('Posting Date Cannot Be After Today Date'))
		self.validate_package_merge_grade()
		self.set_batch()
		self.update_outstanding_qty()
	
	def set_batch(self):
		has_batch_no = frappe.db.get_value('Item', self.item_code, 'has_batch_no')

		if has_batch_no:
			if not self.get('merge'):
				frappe.throw(_("Please set Merge"))

			if not self.get('grade'):
				frappe.throw(_("Please set Grade"))

			args = {
				'item_code': self.item_code,
				'merge': self.merge,
				'grade': self.grade,
			}

			batch_no = get_batch_no(args)
			if batch_no:
				self.db_set('batch_no', batch_no)
			else:
				frappe.throw(_('Batch Not found for Merge <b>{}</b> and Grade <b>{}</b>').format(self.merge,self.grade))

	def validate_package_merge_grade(self):
		for row in self.packages:
			merge,grade = frappe.db.get_value("Package",row.package,['merge','grade'])
			if merge != self.merge:
				frappe.throw(_("#Row {}: Package {} has different merge").format(row.idx, row.package))
			elif grade != self.grade:
				frappe.throw(_("#Row {}: Package {} has different grade").format(row.idx, row.package))

	def on_submit(self):
		if not self.batch_no:
			frappe.throw(_("Sufficient quantity for item {} is not available in {} warehouse for merge {}.".format(frappe.bold(self.item_code), frappe.bold(self.warehouse), frappe.bold(self.merge))))
		self.create_stock_entry()

	def on_cancel(self):
		self.cancel_stock_entry()

	def create_stock_entry(self):
		se = frappe.new_doc("Stock Entry")
		se.stock_entry_type = "Material Transfer"
		se.purpose = "Material Transfer"
		se.posting_date = self.posting_date
		se.posting_time = self.posting_time
		se.set_posting_time = 1
		se.reference_doctype = self.doctype
		se.reference_docname = self.name
		se.company = self.company
		abbr = frappe.db.get_value('Company',self.company,'abbr')
	
		se.append("items",{
			'item_code': self.item_code,
			'qty': self.total_net_weight,
			's_warehouse': self.s_warehouse,
			't_warehouse': self.t_warehouse,
			'merge': self.merge,
			'grade': self.grade,
			'batch_no': self.batch_no
		})
		try:
			se.save(ignore_permissions=True)
			se.submit()
			self.update_packages()
		except Exception as e:
			frappe.db.rollback()
			frappe.throw(str(e))
		else:
			frappe.db.commit()

	def cancel_stock_entry(self):
		se = frappe.get_doc("Stock Entry",{'reference_doctype': self.doctype,'reference_docname':self.name})
		se.flags.ignore_permissions = True
		
		try:
			se.cancel()
		except Exception as e:
			raise e

		se.db_set('reference_doctype','')
		se.db_set('reference_docname','')
		
		self.update_packages()
		frappe.db.commit()
		
	def update_packages(self):
		if self._action == "submit":
			for row in self.packages:
				doc = frappe.get_doc("Package", row.package)
				doc.warehouse = self.t_warehouse
				doc.save(ignore_permissions=True)

		elif self._action == "cancel":
			for row in self.packages:
				doc = frappe.get_doc("Package", row.package)
				doc.warehouse = self.s_warehouse
				doc.save(ignore_permissions=True)
	
	def update_qty_and_status(self):
		self.update_outstanding_qty()
		self.update_status()
		self.db_set('consumed_qty', self.consumed_qty)
		
	def update_outstanding_qty(self):
		outstanding_qty = flt(self.total_net_weight) - flt(self.consumed_qty)
		name = get_link_to_form('Material Unpack', self.name)
		if outstanding_qty < 0 :
			frappe.throw(_("Outstanding Qty will become negative for Material Unpack - <b>{}</b>".format(name)))
		
		self.db_set('outstanding_qty',outstanding_qty)

	def update_status(self):
		status = None

		if self.outstanding_qty == self.total_net_weight:
			status = 'Unpacked'

		elif self.outstanding_qty == 0:
			status = 'Repacked'
		else: 
			status = 'Partially Repacked'
		if self.status != status:
			self.db_set("status", status)


@frappe.whitelist()
def make_repack(source_name, target_doc=None):
	return get_mapped_doc("Material Unpack" , source_name,{
		"Material Unpack":{
			"doctype" : "Material Repack",
			"field_map":{
				"batch_no" : "batch_no",
				'name': 'material_unpack',
				's_warehouse':'t_warehouse',
				't_warehouse':'s_warehouse'
			},
			"field_no_map":[
				"naming_series",
				"total_net_weight",
				"total_gross_weight",
				"posting_date",
				"posting_time"
			]
		}
	}, target_doc)
