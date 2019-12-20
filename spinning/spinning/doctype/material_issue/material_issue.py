# -*- coding: utf-8 -*-
# Copyright (c) 2019, FinByz Tech Pvt Ltd and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.utils import nowdate, flt, cint
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc
from datetime import datetime
from erpnext.stock.get_item_details import get_bin_details, get_default_cost_center, get_conversion_factor, get_reserved_qty_for_so
from erpnext.stock.doctype.stock_entry.stock_entry import get_uom_details, get_warehouse_details
from erpnext.setup.doctype.item_group.item_group import get_item_group_defaults
from erpnext.setup.doctype.brand.brand import get_brand_defaults
from erpnext.stock.doctype.batch.batch import get_batch_no


class MaterialIssue(Document):
	def validate(self):
		date = datetime.strptime(self.posting_date, '%Y-%m-%d').date()
		cd   = datetime.date(datetime.now())
		if date > cd:
			frappe.throw(_('Posting Date Cannot Be After Today Date'))
		self.validate_packages()
		if self._action == "submit":
			self.calculate_totals()

	def validate_packages(self):
		for row in self.packages:
			doc = frappe.get_doc("Package", row.package)

			if cint(doc.is_delivered):
				frappe.throw(_("Row {}: Package {} is already delivered. Please select another package.".format(row.idx, frappe.bold(row.package))))

			if self.warehouse != doc.warehouse:
				frappe.throw(_("Row {}: Package {} does not belong to source warehouse {}. Please select another package.".format(row.idx, frappe.bold(row.package), frappe.bold(self.warehouse))))

	def calculate_totals(self):
		self.total_qty = sum([row.qty for row in self.items])
		self.total_amount = sum([row.amount for row in self.items])
		self.total_gross_weight = sum([row.gross_weight for row in self.packages])
		self.total_net_weight = sum([row.net_weight for row in self.packages])
		self.total_packages = sum([row.no_of_packages for row in self.items])

	def before_save(self):
		self.calculate_totals()
	
		abbr = frappe.db.get_value('Company',self.company,'abbr')
		if self.is_opening == 'Yes':
			self.adjustment_entry = 0
			for row in self.items:
				row.expense_account = 'Temporary Opening - %s' %abbr
		if self.adjustment_entry:
			for row in self.items:
				row.expense_account = 'Stock Adjustment - %s' %abbr
				
	def set_items_as_per_packages(self):
		#package_items = list(set(map(lambda x: (x.item_code, x.merge, x.grade, x.batch_no), self.packages)))

		to_remove = []
		items_row_dict = {}
		item_row = None

		for row in self.items:
			has_batch_no = frappe.db.get_value("Item", row.item_code, 'has_batch_no')
			
			if has_batch_no:
				to_remove.append(row)
				items_row_dict.setdefault(row.item_code, row.as_dict())
				# if item_row is None:
					# item_row = row.as_dict()

		else:
			[self.remove(d) for d in to_remove]

		package_items = {}

		for row in self.packages:
			key = (row.item_code, row.merge, row.grade, row.batch_no)
			package_items.setdefault(key, frappe._dict({
				'net_weight': 0,
				'packages': 0,
			}))
			#package_items[key].update(item_row)
			package_items[key].update(items_row_dict.get(row.item_code))
			# package_items[key].s_warehouse = self.warehouse
			package_items[key].net_weight += row.net_weight
			package_items[key].packages += 1
		
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
			_args.no_of_packages = args.packages

			self.append('items', _args)

		for idx, row in enumerate(self.items, start = 1):
			row.idx = idx

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
		if (args.get('warehouse', None) and args.get('qty') and
			ret.get('has_batch_no') and not args.get('batch_no')):
			args.batch_no = get_batch_no(args['item_code'], args['warehouse'], args['qty'])

		return ret

	def before_validate(self):
		self.set_items_as_per_packages()

	def on_submit(self):		
		self.create_stock_entry()

	def on_cancel(self):
		self.cancel_stock_entry()

	def create_stock_entry(self):
		def get_stock_entry_doc(source_name, target_doc=None, ignore_permissions= True):
			def set_missing_values(source, target):
				target.stock_entry_type = "Material Issue"
				target.purpose = "Material Issue"
				target.set_posting_time = 1
				target.reference_doctype = self.doctype
				target.reference_docname = self.name
		
				target.calculate_rate_and_amount()
				target.set_missing_values()

			doclist = get_mapped_doc("Material Issue", source_name, {
				"Material Issue": {
					"doctype": "Stock Entry",
					"field_map": {
						"warehouse": "from_warehouse",
						"posting_date": "posting_date",
						"posting_time": "posting_time",
					},
				},
				"Material Issue Item": {
					"doctype": "Stock Entry Detail",
					"field_map": {
						"batch_no": "batch_no",
					},
				}
			}, target_doc, set_missing_values, ignore_permissions=ignore_permissions)

			return doclist

		se = get_stock_entry_doc(self.name)
		try:
			se.save(ignore_permissions=True)
			se.calculate_rate_and_amount()
			se.submit()
		except Exception as e:
			frappe.db.rollback()
			frappe.throw(e)
		else:
			self.update_packages()
			# #self.db_set('stock_entry_ref', se.name)
			# frappe.db.commit()

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
		# frappe.db.commit()

	def update_packages(self):
		if self._action == "submit":
			for row in self.packages:
				doc = frappe.get_doc("Package", row.package)
				doc.add_consumption(self.doctype, self.name, row.net_weight)
				doc.save(ignore_permissions=True)

		elif self._action == "cancel":
			for row in self.packages:
				doc = frappe.get_doc("Package", row.package)
				doc.remove_consumption(self.doctype, self.name)
				doc.save(ignore_permissions=True)
