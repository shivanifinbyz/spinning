# -*- coding: utf-8 -*-
# Copyright (c) 2019, FinByz Tech Pvt Ltd and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.utils import nowdate, flt, cint, cstr
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc
from datetime import datetime
from erpnext.stock.get_item_details import get_bin_details, get_default_cost_center, get_conversion_factor, get_reserved_qty_for_so
from erpnext.stock.doctype.stock_entry.stock_entry import get_uom_details, get_warehouse_details
from erpnext.setup.doctype.item_group.item_group import get_item_group_defaults
from erpnext.setup.doctype.brand.brand import get_brand_defaults
from erpnext.stock.doctype.batch.batch import get_batch_no

from spinning.doc_events.work_order import override_work_order_functions


class MaterialTransfer(Document):
	def validate(self):
		date = datetime.strptime(self.posting_date, '%Y-%m-%d').date()
		cd   = datetime.date(datetime.now())
		if date > cd:
			frappe.throw(_('Posting Date Cannot Be After Today Date'))
		self.validate_packages()
		self.validate_transfer()
	
	def validate_packages(self):
		package_list = []
		for row in self.packages:
			if row.package in package_list:
				frappe.throw(_("Row {}: Package {} selected twice".format(row.idx, frappe.bold(row.package))))
			
			doc = frappe.get_doc("Package", row.package)
			
			if cint(doc.is_delivered):
				frappe.throw(_("Row {}: Package {} is already delivered. Please select another package.".format(row.idx, frappe.bold(row.package))))

			if self.s_warehouse != doc.warehouse:
				frappe.throw(_("Row {}: Package {} does not belong to source warehouse {}. Please select another package.".format(row.idx, frappe.bold(row.package), frappe.bold(self.s_warehouse))))
			package_list.append(row.package)
			row.net_weight = doc.remaining_qty

	def validate_transfer(self):
		if cint(self.is_material_transfer_for_manufacture):
			if not self.work_order:
				frappe.throw(_("Work Order is Mandatory!"))

		else:
			self.work_order = None
			self.bom_no = None
			self.merge = None

	def before_save(self):
		self.set_items_as_per_packages()
		self.calculate_totals()

	def set_items_as_per_packages(self):

		to_remove = []
		items_row_dict = {}
		has_packages = False

		if self.get('packages'):
			has_packages = True

		for row in self.items:
			has_batch_no = frappe.db.get_value("Item", row.item_code, 'has_batch_no')
			
			if has_batch_no:
				if not has_packages:
					frappe.throw(_("Please select packages for item {} in Row {}".format(frappe.bold(row.item_code), row.idx)))
					break

				to_remove.append(row)
				items_row_dict.setdefault(row.item_code, row.as_dict())

		else:
			[self.remove(d) for d in to_remove]

		package_items = {}
		to_remove = []

		for row in self.packages:
			if not items_row_dict.get(row.item_code, None):
				to_remove.append(row)
				continue

			key = (row.item_code, row.merge, row.grade, row.batch_no)
			package_items.setdefault(key, frappe._dict({
				'net_weight': 0,
			}))
			package_items[key].update(items_row_dict.get(row.item_code))
			package_items[key].s_warehouse = self.s_warehouse
			package_items[key].t_warehouse = self.t_warehouse
			package_items[key].net_weight += row.net_weight

		else:
			[self.remove(d) for d in to_remove]
		
		for (item_code, merge, grade, batch_no), args in list(package_items.items()):
			amount = flt(args.basic_rate * args.net_weight)

			_args = args.copy()
			_args.pop('idx')
			_args.pop('name')
			_args.qty = args.net_weight
			_args.basic_amount = amount
			_args.amount = amount
			_args.merge = merge
			_args.grade = grade
			_args.batch_no = batch_no

			self.append('items', _args)

		if package_items:
			for idx, row in enumerate(self.items, start = 1):
				row.idx = idx

	def calculate_totals(self):
		self.total_qty = sum([row.qty for row in self.items])
		self.total_amount = sum([row.amount for row in self.items])
		self.total_gross_weight = sum([row.gross_weight for row in self.packages])
		self.total_net_weight = sum([row.net_weight for row in self.packages])

	def get_item_details(self, args=None, for_update=False):
		item = frappe.db.sql("""select i.name, i.stock_uom, i.description, i.image, i.item_name, i.item_group,
				i.has_batch_no, i.sample_quantity, i.has_serial_no,
				id.expense_account, id.buying_cost_center
			from `tabItem` i LEFT JOIN `tabItem Default` id ON i.name=id.parent and id.company=%s
			where i.name=%s
				and i.disabled=0
				and (i.end_of_life is null or i.end_of_life='0000-00-00' or i.end_of_life > %s)""",
			(self.company, args.get('item_code'), nowdate()), as_dict = 1)

		if not item:
			frappe.throw(_("Item {0} is not active or end of life has been reached").format(args.get("item_code")))

		item = item[0]
		item_group_defaults = get_item_group_defaults(item.name, self.company)
		brand_defaults = get_brand_defaults(item.name, self.company)

		ret = frappe._dict({
			'uom'			      	: item.stock_uom,
			'stock_uom'				: item.stock_uom,
			'description'		  	: item.description,
			'image'					: item.image,
			'item_name' 		  	: item.item_name,
			'cost_center'			: get_default_cost_center(args, item, item_group_defaults, brand_defaults, self.company),
			'qty'					: args.get("qty"),
			'transfer_qty'			: args.get('qty'),
			'conversion_factor'		: 1,
			'batch_no'				: '',
			'actual_qty'			: 0,
			'basic_rate'			: 0,
			'serial_no'				: '',
			'has_serial_no'			: item.has_serial_no,
			'has_batch_no'			: item.has_batch_no,
			'sample_quantity'		: item.sample_quantity
		})

		# update uom
		if args.get("uom") and for_update:
			ret.update(get_uom_details(args.get('item_code'), args.get('uom'), args.get('qty')))

		ret["expense_account"] = (item.get("expense_account") or
			item_group_defaults.get("expense_account") or
			frappe.get_cached_value('Company',  self.company,  "default_expense_account"))

		for company_field, field in list({'stock_adjustment_account': 'expense_account',
			'cost_center': 'cost_center'}.items()):
			if not ret.get(field):
				ret[field] = frappe.get_cached_value('Company',  self.company,  company_field)

		args['posting_date'] = self.posting_date
		args['posting_time'] = self.posting_time

		stock_and_rate = get_warehouse_details(args) if args.get('warehouse') else {}
		ret.update(stock_and_rate)

		# automatically select batch for outgoing item
		if (args.get('s_warehouse', None) and args.get('qty') and
			ret.get('has_batch_no') and not args.get('batch_no')):
			args.batch_no = get_batch_no(args['item_code'], args['s_warehouse'], args['qty'])

		return ret

	def get_wo_required_items(self, work_order):
		doc = frappe.get_doc("Work Order", work_order)

		items = []

		for row in doc.required_items:
			if row.transferred_qty < row.required_qty:
				items.append({
					"item_code": row.item_code,
					"qty": flt(row.required_qty - row.transferred_qty),
					"merge": row.get('merge', ''),
				})

		return items

	def get_packages(self, filters):
		fields = ('name', 'spools', 'item_code', 'item_name', 'warehouse', 'batch_no', 'merge', 'grade', 'gross_weight', 'net_weight', 'tare_weight')

		data = frappe.get_list("Package", filters = filters, fields = fields)

		for row in data:
			row.package = row.pop('name')

		return data

	def on_submit(self):
		self.create_stock_entry()

	def on_cancel(self):
		self.consumption_validation()
		self.cancel_stock_entry()

	def create_stock_entry(self):
		def get_stock_entry_doc(source_name, target_doc=None,ignore_permissions= True):
			def set_missing_values(source, target):
				purpose = "Material Transfer"
			
				if cint(self.is_material_transfer_for_manufacture):
					purpose = "Material Transfer for Manufacture"
					target.from_bom = 1
					target.work_order = source.work_order
					target.bom_no = source.bom_no
					target.fg_completed_qty = source.total_qty
				
				if cint(self.is_send_to_subcontractor):
					purpose = "Send to Subcontractor"
					target.purchase_order = source.purchase_order
					target.supplier = source.supplier
					target.supplier_name = source.supplier_name
					target.address_display = source.address
				
				target.stock_entry_type = purpose
				target.purpose = purpose
				target.set_posting_time = 1
				target.reference_doctype = self.doctype
				target.reference_docname = self.name

				target.calculate_rate_and_amount()
				target.set_missing_values()

			doclist = get_mapped_doc("Material Transfer", source_name, {
				"Material Transfer": {
					"doctype": "Stock Entry",
					"field_map": {
						"s_warehouse": "from_warehouse",
						"t_warehouse": "to_warehouse",
						"posting_date": "posting_date",
						"posting_time": "posting_time",
					},
				},
				"Material Transfer Item": {
					"doctype": "Stock Entry Detail",
					"field_map": {
						"batch_no": "batch_no",
						'subcontracted_item': 'subcontracted_item'
					},
				}
			}, target_doc, set_missing_values,ignore_permissions=ignore_permissions)

			return doclist

		se = get_stock_entry_doc(self.name)
		override_work_order_functions()
		se.save(ignore_permissions=True)
		se.calculate_rate_and_amount()
		se.submit()
		#self.db_set('stock_entry_ref', se.name)
		self.update_packages()
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
		
	def consumption_validation(self):
		for row in self.packages:
			remaining_qty = frappe.db.get_value("Package",row.package,'remaining_qty')
			if flt(remaining_qty) != flt(row.net_weight):
				frappe.throw("Row: {} <b>{}</b> Package is already consumed".format(row.idx,row.package))
	
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

	def add_to_mt_detail(self, item_dict, bom_no=None):
		cost_center = frappe.db.get_value("Company", self.company, 'cost_center')

		for d in item_dict:
			stock_uom = item_dict[d].get("stock_uom") or frappe.db.get_value("Item", d, "stock_uom")

			se_child = self.append('items')
			se_child.s_warehouse = item_dict[d].get("s_warehouse")
			se_child.t_warehouse = item_dict[d].get("t_warehouse")
			se_child.item_code = item_dict[d].get('item_code') or cstr(d)
			se_child.item_name = item_dict[d]["item_name"]
			se_child.description = item_dict[d]["description"]
			se_child.basic_rate = item_dict[d]["basic_rate"]
			se_child.basic_amount = item_dict[d]["basic_amount"]
			se_child.amount = item_dict[d]["amount"]
			se_child.subcontracted_item = item_dict[d].get("main_item_code")
			se_child.uom = item_dict[d]["uom"] if item_dict[d].get("uom") else stock_uom
			se_child.stock_uom = stock_uom
			se_child.qty = flt(item_dict[d]["qty"], se_child.precision("qty"))
			se_child.expense_account = item_dict[d].get("expense_account")
			se_child.cost_center = item_dict[d].get("cost_center") or cost_center
			se_child.allow_alternative_item = item_dict[d].get("allow_alternative_item", 0)
			#se_child.original_item = item_dict[d].get("original_item")
			se_child.po_detail = item_dict[d].get("po_detail")

			if item_dict[d].get("idx"):
				se_child.idx = item_dict[d].get("idx")

			if se_child.s_warehouse==None:
				se_child.s_warehouse = self.s_warehouse
			if se_child.t_warehouse==None:
				se_child.t_warehouse = self.t_warehouse

			# in stock uom
			se_child.conversion_factor = flt(item_dict[d].get("conversion_factor")) or 1
			se_child.transfer_qty = flt(item_dict[d]["qty"]*se_child.conversion_factor, se_child.precision("qty"))


			# to be assigned for finished item
			se_child.bom_no = bom_no