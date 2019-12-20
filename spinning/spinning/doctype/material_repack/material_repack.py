# -*- coding: utf-8 -*-
# Copyright (c) 2019, FinByz Tech Pvt Ltd and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.utils import flt, cstr, cint
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc
from frappe.model.naming import parse_naming_series, getseries
from spinning.controllers.batch_controller import get_batch_no
from datetime import datetime
from spinning.controllers.merge_validation import validate_merge

import json

class MaterialRepack(Document):
	def validate(self):
		validate_merge(self)
		date = datetime.strptime(self.posting_date, '%Y-%m-%d').date()
		cd   = datetime.date(datetime.now())
		if date > cd:
			frappe.throw(_('Posting Date Cannot Be After Today Date'))
		self.calculate_totals()
			
	def before_save(self):
		if not self.is_new():
			self.set_batch()
			self.set_missing_packages()

		self.calculate_totals()
			
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

		self.total_spool = flt(totals.spools, 3)
		self.total_net_weight = flt(totals.net_weight, 3)
		self.total_gross_weight = flt(totals.gross_weight, 3)
		self.total_tare_weight = flt(totals.tare_weight, 3)
		
	def print_row_package(self, child_row, commit=True):
		def get_package_doc(source_name, target_doc=None, ignore_permissions = True):
			def set_missing_values(source, target):
				if source.package_type == "Pallet":
					target.ownership_type = "Company"
					target.ownership = source.company
					
				target.merge = self.merge
				target.grade = self.grade
				target.package_type = self.package_type
				
			return get_mapped_doc("Material Repack", source_name, {
				"Material Repack": {
					"doctype": "Package",
					"field_map": {
						"t_warehouse": "warehouse",
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
		self.validate_total_net_qty()
		self.update_package_details()
		self.create_stock_entry()
		self.update_material_unpack()

	def on_cancel(self):
		self.clear_package_details()
		self.cancel_stock_entry()
		self.update_material_unpack()

	def validate_total_net_qty(self):
		over_repack_allowance_per = flt(frappe.db.get_single_value("Stock Settings", 'over_repack_allowance'))
		total_unpack_net_weight, total_unpack_outstanding_qty = frappe.db.get_value("Material Unpack", self.material_unpack, ['total_net_weight', 'outstanding_qty'])

		tolernace = total_unpack_net_weight * over_repack_allowance_per / 100.0
		diff = flt(total_unpack_outstanding_qty - self.total_net_weight, 4)

		if diff	> tolernace:
			self.consumed_qty = self.total_net_weight

		elif (diff > 0 and diff < tolernace) or (diff <= 0 and abs(diff) < tolernace):
			self.consumed_qty = total_unpack_outstanding_qty

		else:
			frappe.throw(_("Repack quantity is more than allowed tolernace: {} (+/-) {} %".format(total_unpack_net_weight, over_repack_allowance_per)))

		self.db_set('consumed_qty', self.consumed_qty)

	def update_package_details(self):
		for row in self.package_details:
			doc = frappe.get_doc("Package",row.package)
			doc.company = self.company
			doc.merge = self.merge
			doc.grade = self.grade
			doc.item_code = self.item_code
			doc.item = self.item_name
			doc.warehouse = self.t_warehouse
			doc.package_type = self.package_type
			doc.package_item = self.package_item
			doc.paper_tube = self.paper_tube
			doc.spool_weight = self.spool_weight
			doc.purchase_date =  self.posting_date
			doc.purchase_time = self.posting_time			
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
		se = frappe.new_doc("Stock Entry")
		se.stock_entry_type = "Repack"
		se.purpose = "Repack"
		se.set_posting_time = 1
		se.reference_doctype = self.doctype
		se.reference_docname = self.name
		se.posting_date = self.posting_date
		se.posting_time = self.posting_time
		se.company = self.company

		merge, grade, batch_no = frappe.db.get_value("Material Unpack", self.material_unpack, ['merge', 'grade', 'batch_no'])

		# se.append("items",{
		# 	'item_code': self.item_code,
		# 	's_warehouse': self.s_warehouse,
		# 	'merge': frappe.db.get_value('Material Unpack',self.material_unpack,'merge'),
		# 	'grade': frappe.db.get_value('Material Unpack',self.material_unpack,'grade'),
		# 	'batch_no': frappe.db.get_value('Material Unpack',self.material_unpack,'batch_no'),
		# 	'qty': frappe.db.get_value('Material Unpack',self.material_unpack,'total_net_weight'),
		# })

		se.append("items",{
			'item_code': self.item_code,
			's_warehouse': self.s_warehouse,
			'merge': merge,
			'grade': grade,
			'batch_no': batch_no,
			'qty': self.consumed_qty,
		})
		
		if self.package_item:
			se.append("items",{
				'item_code': self.package_item,
				's_warehouse': self.package_warehouse,
				'qty': len(self.package_details),
			})
		se.append("items",{
			'item_code': self.item_code,
			't_warehouse': self.t_warehouse,
			'merge': self.merge,
			'grade': self.grade,
			'batch_no': self.batch_no,
			'qty': self.total_net_weight,
		})
		
		try:
			se.save(ignore_permissions=True)
			se.submit()
		except Exception as e:
			frappe.throw(str(e))
		
	def cancel_stock_entry(self):
		se = frappe.get_doc("Stock Entry",{'reference_doctype': self.doctype,'reference_docname':self.name})
		se.flags.ignore_permissions = True
		try:
			se.cancel()
		except Exception as e:
			raise e

		se.db_set('reference_doctype','')
		se.db_set('reference_docname','')

	def update_material_unpack(self):
		doc = frappe.get_doc("Material Unpack", self.material_unpack)

		if self._action == 'submit':
			self.add_package_consumption(doc)
			doc.consumed_qty += self.consumed_qty

		elif self._action == 'cancel':
			self.remove_package_consumption()
			doc.consumed_qty -= self.consumed_qty

		doc.update_qty_and_status()
		doc.save()
		
	def add_package_consumption(self, doc):
		if not self.material_unpack:
			frappe.throw(_("Material Unpack is Mandatory!"))

		self._consumed_packages = []
		remaining_qty = flt(self.consumed_qty, 3)

		for pkg in doc.packages:
			package = frappe.get_doc("Package", pkg.package)
			if package.status == "Out of Stock":
				continue

			qty = pkg.net_weight if remaining_qty > pkg.net_weight else remaining_qty
			package.add_consumption(self.doctype, self.name, qty)
			package.save(ignore_permissions=True)
			remaining_qty -= qty

			self._consumed_packages.append(package.name)

			if remaining_qty <= 0:
				break

		self._update_consumed_packages()

	def remove_package_consumption(self):
		package_list = self._load_consumed_packages()

		for pkg in package_list:
			package = frappe.get_doc("Package", pkg)
			package.remove_consumption(self.doctype, self.name)
			package.save(ignore_permissions=True)

	def _update_consumed_packages(self):
		consumed_packages = json.dumps(self._consumed_packages or [])
		self.db_set('consumed_packages', consumed_packages)

	def _load_consumed_packages(self):
		return json.loads(self.consumed_packages)

	def set_package_series(self):
		if not (self.company or self.workstation):
			return

		series = self.get_series()
		prefix = self.parse_series(series)
		current_value = cint(frappe.db.get_value("Series", prefix, "current", order_by="name"))

		value = current_value + 1
		self.series_value = value
		self.package_series = prefix

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

		return "{machine_series}.#####".format(company_series = company_series, machine_series = machine_series)

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
