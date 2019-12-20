# -*- coding: utf-8 -*-
# Copyright (c) 2019, FinByz Tech Pvt Ltd and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.utils import flt, cstr, cint
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc
from frappe.model.naming import parse_naming_series, getseries
from datetime import datetime
from spinning.doc_events.work_order import override_work_order_functions
from spinning.controllers.batch_controller import get_batch_no, get_fifo_batches
from datetime import datetime
import json
from six import string_types
from spinning.controllers.merge_validation import validate_merge


class WorkOrderFinish(Document):

	def validate(self):
		validate_merge(self)
		date = datetime.strptime(self.posting_date, '%Y-%m-%d').date()
		cd   = datetime.date(datetime.now())
		if date > cd:
			frappe.throw(_('Posting Date Cannot Be After Today Date'))

	def before_save(self):
		if not self.is_new():
			self.set_batch()
			self.set_missing_packages()

		self.calculate_totals()

	def set_batch(self):
		# if self.get('batch_no'):
			# return

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

			if not batch_no:
				batch = frappe.new_doc("Batch")
				batch.item = self.item_code
				batch.grade = cstr(self.grade)
				batch.merge = cstr(self.merge)
				batch.insert(ignore_permissions=True)
				batch_no = batch.name

			self.db_set('batch_no', batch_no)

	def set_missing_packages(self):
		for row in self.package_details:
			if not row.get('package'):
				self.print_row_package(row, False)

	def calculate_totals(self):
		totals = frappe._dict({
			'spools': 0.0,
			'net_weight': 0.0,
			'gross_weight': 0.0,
			'tare_weight': 0.0
		})

		for row in self.package_details:
			totals.spools += row.no_of_spool
			totals.gross_weight += row.gross_weight
			totals.tare_weight += row.tare_weight
			totals.net_weight += row.net_weight

		self.db_set('total_spool', flt(totals.spools, 3))
		self.db_set('total_net_weight', flt(totals.net_weight, 3))
		self.db_set('total_gross_weight', flt(totals.gross_weight, 3))
		self.db_set('total_tare_weight', flt(totals.tare_weight, 3))

	def print_row_package(self, child_row, commit=True):
		def get_package_doc(source_name, target_doc=None, ignore_permissions = True):
			def set_missing_values(source, target):
				if source.package_type == "Pallet":
					target.ownership_type = "Company"
					target.ownership = source.company

				target.merge = self.merge
				target.grade = self.grade
				target.package_type = self.package_type

			return get_mapped_doc("Work Order Finish", source_name, {
				"Work Order Finish": {
					"doctype": "Package",
					"field_map": {
						"target_warehouse": "warehouse",
						"posting_date" : "purchase_date",
						"posting_time" : "purchase_time",
					}
				}
			}, target_doc, set_missing_values, ignore_permissions=ignore_permissions)

		self.set_batch()
		update_series = False

		if isinstance(child_row, dict):
			child_row = frappe._dict(child_row)
			
			if child_row.get('__islocal'):
				child_row = self.get_child_doc(child_row)
				child_row.insert()

			else:
				child_row = frappe.get_doc(child_row)

		if frappe.db.exists("Package", child_row.package):
			package = frappe.get_doc("Package", child_row.package)
			
		else:
			update_series = True
			package = get_package_doc(self.name)

		package.purchase_document_type = self.doctype
		package.purchase_document_no = self.name
		package.package_series = self.get_series()

		try:
			package.save(ignore_permissions=True)
		except Exception as e:
			raise e
		else:
			if update_series:
				value = self.series_value + 1
				self.update_series_value(value)

		child_row.tare_weight = flt(child_row.package_weight + (child_row.no_of_spool * self.spool_weight))
		child_row.net_weight = child_row.gross_weight - child_row.tare_weight

		if not child_row.package:
			child_row.package = package.name

		if commit:
			child_row.save(ignore_permissions=True)

		self.calculate_totals()
		frappe.db.commit()
		return child_row.name

	def get_child_doc(self, child_row):
		def parse_args(child_row):
			child_row.pop('__islocal')
			child_row.pop('__unsaved')
			child_row.pop('__unedited')
			child_row.pop('name')

			return child_row

		child_row = parse_args(child_row)

		doc = frappe.get_doc(child_row)
		return doc

	def on_submit(self):
		self.update_package_details()
		self.create_stock_entry()

	def on_cancel(self):
		self.clear_package_details()
		self.cancel_stock_entry()

	def update_package_details(self):
		for row in self.package_details:
			doc = frappe.get_doc("Package",row.package)
			doc.company = self.company
			doc.merge = self.merge
			doc.grade = self.grade
			doc.item_code = self.item_code
			doc.item_name = self.item_name
			doc.package_item = self.package_item
			doc.package_type = self.package_type
			doc.paper_tube = self.paper_tube
			doc.purchase_date = self.posting_date
			doc.purchase_time = self.posting_time
			doc.warehouse = self.target_warehouse
			doc.spool_weight = self.spool_weight
			doc.gross_weight = row.gross_weight
			doc.net_weight = row.net_weight
			doc.tare_weight = row.tare_weight
			doc.spools = row.no_of_spool
			doc.package_weight = row.package_weight
			doc.purchase_document_type = self.doctype
			doc.purchase_document_no = self.name
			doc.save(ignore_permissions=True)

	def clear_package_details(self):
		for row in self.package_details:
			doc = frappe.get_doc("Package",row.package)
			doc.gross_weight = 0.0
			doc.net_weight = 0.0
			doc.tare_weight = 0.0
			doc.spools = 0.0
			doc.package_weight = 0.0
			doc.purchase_document_no = ''
			doc.save(ignore_permissions=True)

	def create_stock_entry(self):
		wo = frappe.get_doc("Work Order", self.work_order)
		
		se = frappe.new_doc("Stock Entry")
		se.stock_entry_type = "Manufacture"
		se.purpose = "Manufacture"
		se.work_order = self.work_order
		se.bom_no = self.from_bom
		se.set_posting_time = 1
		se.posting_date = self.posting_date
		se.posting_time = self.posting_time
		se.reference_doctype = self.doctype
		se.reference_docname = self.name
		se.from_bom = 1
		se.company = self.company
		se.fg_completed_qty = self.total_net_weight
		se.from_warehouse = wo.wip_warehouse
		
		se.get_items()

		if self.paper_tube:
			se.append("items",{
				'item_code': self.paper_tube,
				's_warehouse': wo.wip_warehouse,
				'qty': self.total_spool,
			})
		if self.package_item:
			se.append("items",{
				'item_code': self.package_item,
				's_warehouse': self.package_warehouse or self.source_warehouse,
				'qty': len(self.package_details),
			})

		for d in se.items:
			if d.t_warehouse and d.item_code == self.item_code:
				d.merge = self.merge
				d.grade = self.grade

			if d.s_warehouse:
				merge = frappe.db.sql("select merge from `tabWork Order Item` where parent = %s and item_code = %s", (self.work_order, d.item_code))
				if merge:
					d.merge = merge[0][0]

		override_work_order_functions()
		items = []

		for d in se.items:
			if not d.s_warehouse:
				continue

			elif not d.merge:
				continue

			has_batch_no = frappe.db.get_value('Item', d.item_code, 'has_batch_no')

			if not has_batch_no:
				continue

			batches = get_fifo_batches(d.item_code, d.s_warehouse, d.merge)
			
			if not batches:
				frappe.throw(_("Sufficient quantity for item {} is not available in {} warehouse for merge {}.".format(frappe.bold(d.item_code), frappe.bold(d.s_warehouse), frappe.bold(d.merge))))

			remaining_qty = d.qty

			for i, batch in enumerate(batches):
				if i == 0:
					if batch.qty >= remaining_qty:
						d.batch_no = batch.batch_id
						break

					else:
						if len(batches) == 1:
							frappe.throw(_("Sufficient quantity for item {} is not available in {} warehouse for merge {}.".format(frappe.bold(d.item_code), frappe.bold(d.s_warehouse), frappe.bold(d.merge))))

						remaining_qty -= flt(batch.qty)
						d.qty = batch.qty
						d.batch_no = batch.batch_id

						items.append(frappe._dict({
							'item_code': d.item_code,
							's_warehouse': wo.wip_warehouse,
							'qty': remaining_qty,
						}))

				else:
					flag = 0
					for x in items[:]:
						if x.get('batch_no'):
							continue

						if batch.qty >= remaining_qty:
							x.batch_no = batch.batch_id
							flag = 1
							break
						
						else:
							remaining_qty -= flt(batch.qty)
							
							x.qty = batch.qty
							x.batch_no = batch.batch_id
							
							items.append(frappe._dict({
								'item_code': d.item_code,
								's_warehouse': wo.wip_warehouse,
								'qty': remaining_qty,
							}))

					if flag:
						break

			else:
				if remaining_qty:
					frappe.throw(_("Sufficient quantity for item {} is not available in {} warehouse for merge {}.".format(frappe.bold(d.item_code), frappe.bold(d.s_warehouse), frappe.bold(d.merge))))

		se.extend('items', items)

		# for row in se.items:
			# if row.s_warehouse:
				# frappe.msgprint("Row {} : Item Code - {}, Batch No - {}, Merge - {}".format(row.idx, row.item_code, row.batch_no, row.merge))

		se.save(ignore_permissions=True)
		se.submit()
		self.add_package_consumption(se)

	def cancel_stock_entry(self):
		se = frappe.get_doc("Stock Entry",{'reference_doctype': self.doctype,'reference_docname':self.name})
		override_work_order_functions()
		se.flags.ignore_permissions = True
		try:
			se.cancel()
		except Exception as e:
			raise e
		
		self.remove_package_consumption(se)
		se.db_set('reference_doctype','')
		se.db_set('reference_docname','')

	def add_package_consumption(self, se):
		for row in se.items:
			if row.batch_no and row.s_warehouse and not row.t_warehouse:
				remaining_qty = row.qty
				package_list = frappe.get_list("Package", {
						'status': ["!=", "Out of Stock"],
						'item_code': row.item_code,
						'batch_no': row.batch_no,
						'warehouse': row.s_warehouse,
					}, order_by = "creation DESC")

				for pkg in package_list:
					doc = frappe.get_doc("Package", pkg.name)
					qty = doc.remaining_qty if remaining_qty > doc.remaining_qty else remaining_qty
					doc.add_consumption(self.doctype, self.name, qty)
					doc.save(ignore_permissions=True)
					remaining_qty -= qty
					
					if remaining_qty <= 0:
						break

	def remove_package_consumption(self, se):
		package_list = frappe.get_list("Package Consumption", filters = {
				'reference_doctype': self.doctype,
				'reference_docname': self.name
			}, fields = 'parent')

		for pkg in package_list:
			doc = frappe.get_doc("Package", pkg.parent)
			doc.remove_consumption(self.doctype, self.name)
			doc.save(ignore_permissions=True)

	def set_package_series(self):
		if not (self.company or self.workstation):
			return

		series = self.get_series()
		prefix = self.parse_series(series)
		current_value = cint(frappe.db.get_value("Series", prefix, "current", order_by="name"))

		value = current_value + 1
		self.series_value = value
		self.package_series = prefix

		# next_value = getseries(prefix, 5)
		next_value = "%05d" % value
		description = "Next Package Number : " + frappe.bold(prefix + next_value)

		if not self.is_new():
			self.update_series_value(value)

		return description

	def get_series(self):
		company_series = cstr(frappe.db.get_value("Company", self.company, "default_package_series"))

		if not company_series:
			frappe.throw(_("Please set Default Package Series in company."))

		machine_series = cstr(frappe.db.get_value("Workstation", self.workstation, "package_series"))

		if not machine_series:
			frappe.throw(_("Please set Package Series in Workstation: %s." % frappe.bold(self.workstation)))

		#return "{company_series}.YY.{machine_series}.#####".format(company_series = company_series, machine_series = machine_series)
		return "{machine_series}.#####".format(machine_series = machine_series)

	@staticmethod
	def parse_series(series):
		parts = series.split('.')

		if parts[-1] == "#" * len(parts[-1]):
			del parts[-1]

		prefix = parse_naming_series(parts)
		return prefix

	def update_series_number(self):
		series = self.get_series()
		prefix = self.parse_series(series)

		if not frappe.db.get_value('Series', prefix, 'name', order_by="name"):
			frappe.db.sql("insert into tabSeries (name, current) values (%s, 0)", (prefix))

		frappe.db.sql("update `tabSeries` set current = %s where name = %s", (cint(self.series_value) - 1, prefix))
		self.update_series_value(self.series_value)
		frappe.msgprint(_("Series Updated Successfully!"))

	def update_series_value(self, value):
		if self.series_value != value:
			self.db_set('series_value', value)
