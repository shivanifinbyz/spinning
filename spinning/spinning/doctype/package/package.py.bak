# -*- coding: utf-8 -*-
# Copyright (c) 2019, FinByz Tech Pvt Ltd and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import flt, cint
from frappe.model.document import Document
from frappe.model.naming import make_autoname
from frappe.desk.reportview import get_filters_cond

from spinning.controllers.batch_controller import get_batch_no

import json
from datetime import datetime
from six import string_types

class Package(Document):
	def autoname(self):
		if self.package_series:
			series = self.package_series
			
			# name = None
			# while not name:
			# 	name = make_autoname(series, "Package", self)
			# 	if frappe.db.exists('Package', name):
			# 		name = None

			name = make_autoname(series, "Package", self)
			self.name = name
			self.package_no = name
		else:
			package_no = self.package_no
			new_package_no = package_no
			
			i = 1
			while frappe.db.exists("Package", new_package_no):
				new_package_no = package_no + "-" + str(i)
				i += 1
				
			self.name = new_package_no			

	def validate(self):
		if isinstance(self.purchase_date, string_types):
			date = datetime.strptime(self.purchase_date, '%Y-%m-%d').date()

		else:
			date = self.purchase_date

		cd   = datetime.date(datetime.now())
		if date > cd:
			frappe.throw(_('Posting Date Cannot Be After Today Date'))
		self.set_batch_no()
		self.calculate_consumption()

	def set_batch_no(self):
		
		args = frappe._dict()
		args.item_code = self.item_code
		args.grade = self.grade
		args.merge = self.merge

		batch_no = get_batch_no(args)

		if not batch_no:
			frappe.throw(_("No related batch found for Grade {} and Merge {}".format(frappe.bold(self.grade), frappe.bold(self.merge))))

		self.batch_no = batch_no
		
	def before_save(self):
		self.update_status()

	def calculate_consumption(self):
		self.total_consumed_qty = sum([flt(row.consumed_qty) for row in self.consumptions])
		self.remaining_qty = flt(flt(self.net_weight) - flt(self.total_consumed_qty), 4)
		
	def update_status(self):
		if self.remaining_qty < 0:
			frappe.throw(_("Remaining Qty cannot be less than 0 in Package {} for Item {}.").format(self.name,self.item_code))

		status = None
		
		if self.remaining_qty == 0:
			status = "Out of Stock"
		
		elif self.remaining_qty >= self.net_weight:
			status = "In Stock"

		else:
			status = "Partial Stock"

		if self.status != status:
			self.db_set("status", status)

	def add_consumption(self, doctype, docname, qty):
		for row in self.consumptions:
			if row.reference_doctype == doctype and row.reference_docname == docname:
				frappe.throw(_("Package already consumed for %s : %s" % (doctype, docname)))

		self.append('consumptions', {
			'reference_doctype': doctype,
			'reference_docname': docname,
			'consumed_qty': flt(qty, 4)
		})

	def remove_consumption(self, doctype, docname):
		to_remove = []

		for row in self.consumptions:
			if row.reference_doctype == doctype and row.reference_docname == docname:
				to_remove.append(row)

		else:
			[self.remove(d) for d in to_remove]

		self.calculate_consumption()
		
	def on_trash(self):
		if self.net_weight != 0.0:
			frappe.throw(_("Not allowed to delete any packages where net_weight is not 0"))
		else:
			# self.purchase_document_type = ""
			# self.purchase_document_no = ""
			doc_dict={'Work Order Finish':'Work Order Finish Detail','Other Production':'Other Production Package Details','Material Repack':'Material Repack Package Detail'}
			child_doctype = doc_dict[self.purchase_document_type]
			child_table_name = frappe.db.sql_list("""select name from `tab{0}` where package = {1}""".format(child_doctype,self.name))
			for r in child_table_name:
				frappe.db.set_value(child_doctype,r,"package","")
			frappe.db.commit()
			
			#frappe.db.sql("""update `tab{0}` set `package` = NULL where `name` = {1}""".format(child_doctype,r))
			
				# from frappe.desk.form.linked_with import get_linked_doctypes
				# from frappe.desk.form.linked_with import get_linked_docs
				
				
				
				# linked_doctypes = get_linked_doctypes('Package')
				# 
				# for key in d:
					# child_doctype = doc_dict[key]
					# doc = d[key]
					# doc_dict = doc[0]
					# doc_pkg = doc_dict['name']
					# if child_doctype:
						# frappe.db.sql("""update `tab{0}` set package = NULL where name = {1}""".format((child_doctype,self.name))
						
					
		#  remove reference here

		# if self.purchase_document_no:
		# 	wof_doc = frappe.get_doc("Work Order Finish",self.purchase_document_no)
		# 	for pkg in wof_doc.package_details:
		# 		if pkg.package == self.package_no:

		# 	wof_doc.db_set('sales_order', '')	

# @frappe.whitelist()
# def get_packages(filters):
# 	fields = ('name', 'spools', 'item_code', 'item_name', 'warehouse', 'batch_no', 'merge', 'grade', 'gross_weight', 'net_weight', 'tare_weight')

# 	if isinstance(filters, string_types):
# 		filters = json.loads(filters)

# 	filters['status'] = ["!=", "Out of Stock"]

# 	data = frappe.get_list("Package", filters = filters, fields = fields)

# 	for row in data:
# 		row.package = row.pop('name')

# 	return data


@frappe.whitelist()
def get_packages(filters, raw_filters = None):
	fields = ('name as package', 'spools', 'item_code', 'item_name', 'warehouse', 'batch_no', 'merge', 'grade', 'gross_weight', 'remaining_qty as net_weight', 'tare_weight')

	if isinstance(filters, string_types):
		filters = json.loads(filters)

	# filters['status'] = ["!=", "Out of Stock"]

	data = frappe.db.sql("""
		SELECT 
			{fields}
		FROM 
			`tabPackage`
		WHERE
			status != "Out of Stock" 
			{fcond} {raw_filters} """.format(
				fields = ", ".join(fields),
				fcond = get_filters_cond("Package", filters, []).replace('%', '%%'),
				raw_filters = raw_filters,
			), as_dict = True)

	# data = frappe.get_list("Package", filters = filters, fields = fields)

	# for row in data:
	# 	row.package = row.pop('name')

	return data

@frappe.whitelist()
def get_dist_grade_list(filters):
	return frappe.db.sql_list("""
		SELECT DISTINCT grade from `tabPackage` 
		where status != 'Out of Stock' {fcond} """.format(fcond=get_filters_cond("Package", filters, []).replace('%', '%%')))
