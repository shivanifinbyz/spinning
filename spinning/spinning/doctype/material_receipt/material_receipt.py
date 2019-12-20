# -*- coding: utf-8 -*-
# Copyright (c) 2019, FinByz Tech Pvt Ltd and contributors
# For license information, please see license.txt


import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import nowdate, flt, cint
from erpnext.stock.utils import get_incoming_rate
from frappe.model.delete_doc import check_if_doc_is_linked
from erpnext.stock.stock_ledger import get_previous_sle
from spinning.controllers.batch_controller import set_batches
from erpnext.stock.get_item_details import get_bin_details, get_default_cost_center, get_conversion_factor, get_reserved_qty_for_so
from erpnext.setup.doctype.item_group.item_group import get_item_group_defaults
from erpnext.setup.doctype.brand.brand import get_brand_defaults
from six import string_types
from datetime import datetime

class MaterialReceipt(Document):
	def validate(self):
		date = datetime.strptime(self.posting_date, '%Y-%m-%d').date()
		cd   = datetime.date(datetime.now())
		if date > cd:
			frappe.throw(_('Posting Date Cannot Be After Today Date'))
		if self._action == 'submit':
			self.validate_weights()
			#self.create_packages()
		set_batches(self, 't_warehouse')
		self.calculate_amount()

	def calculate_amount(self):
		for row in self.items:
			row.amount = flt(row.basic_amount)
		
	def before_save(self):

		abbr = frappe.db.get_value('Company',self.company,'abbr')
		if self.is_opening == 'Yes':
			for row in self.items:
				row.expense_account = 'Temporary Opening - %s' %abbr
		if self.adjustment_entry:
			for row in self.items:
				row.expense_account = 'Stock Adjustment - %s' %abbr
		for row in self.packages:
			row.tare_weight = row.gross_weight - row.net_weight
		#self.update_pallet_item()
		
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
		# if (args.get('s_warehouse', None) and args.get('qty') and
			# ret.get('has_batch_no') and not args.get('batch_no')):
			# args.batch_no = get_batch_no(args['item_code'], args['s_warehouse'], args['qty'])

		return ret
			
	def on_submit(self):
		#self.validate_gate_pass()
		self.create_stock_entry()
		self.create_packages()
		
		#frappe.db.commit()
		
	def on_cancel(self):
		self.clear_package_weight()
		self.cancel_stock_entry()
		
	def validate_weights(self):
		for row in self.items:
			has_batch_no = frappe.db.get_value('Item', row.item_code, 'has_batch_no')
			total_net_weight = sum([x.net_weight if x.row_ref == str(row.idx) else 0 for x in self.packages])

			if flt(row.qty, row.precision('qty')) != flt(total_net_weight, row.precision('qty')) and has_batch_no:
				frappe.throw(_("Total Qty does not match with Total Net Weight for Item {} in Row {}".format(row.item_code, row.idx)))
				
	def create_packages(self):
		def validate_package_type():
			if not self.get('package_type'):
				return False
			return True

		def get_row_doc(row_no):
			if len(self.items) < row_no:
				frappe.throw(_("Row Ref in Package List is greater that total rows of Items."))
			return self.items[row_no - 1]

		if self.get('packages'):
			if not validate_package_type():
				frappe.throw(_("Please select Package Type!"))

		for pkg in self.packages:
			row = get_row_doc(cint(pkg.row_ref))

			has_batch_no = frappe.db.get_value('Item', row.item_code, 'has_batch_no')
			
			if not has_batch_no:
				frappe.throw(_("Item <strong>{}</strong> is not batch wise in row {}".format(row.item_code, row.idx)))

			# if has_batch_no and row.idx not in pkg.row_ref:
				# frappe.throw(_("Package is mandatory for <strong>{}</strong> in row {}".format(row.item_code, row.idx)))

			doc = frappe.new_doc("Package")
			doc.package_no = pkg.package
			doc.package_type = pkg.package_type
			doc.package_item = pkg.package_item
			doc.company = self.company

			if pkg.package_type == "Pallet":
				doc.is_returnable = pkg.is_returnable
				doc.returnable_by = pkg.returnable_by

			doc.gross_weight = pkg.gross_weight
			doc.net_weight = pkg.net_weight
			doc.tare_weight = pkg.tare_weight
			doc.spools = pkg.spools
			
			doc.batch_no = row.batch_no
			doc.item_code = row.item_code
			doc.item_name = row.item_name
			doc.merge = row.merge
			doc.grade = row.grade

			doc.purchase_document_type = self.doctype
			doc.purchase_document_no = self.name
			doc.purchase_date = self.posting_date
			doc.purchase_time = self.posting_time
			doc.incoming_rate = row.basic_rate
			doc.warehouse = row.t_warehouse or self.warehouse
			
			doc.save(ignore_permissions=True)

	def clear_package_weight(self):
		package_list = frappe.get_list("Package",filters={'purchase_document_type':self.doctype,'purchase_document_no':self.name})		
		for row in package_list:		
			doc = frappe.get_doc("Package", row.name)	
			if doc.status != "In Stock":
				frappe.throw(_("#Row {}: This Package is Partial Stock or Out of Stock.".format(row.idx)))

			#check_if_doc_is_linked(doc)
			#frappe.delete_doc("Package", doc.name)
			doc.net_weight = 0
			doc.gross_weight = 0
			doc.spool_weight = 0
			doc.tare_weight = 0
			doc.purchase_document_no = ''
			doc.save(ignore_permissions=True)

		else:
			frappe.db.commit()
			
	def create_stock_entry(self):
		se = frappe.new_doc("Stock Entry")
		se.stock_entry_type = "Material Receipt"
		se.purpose = "Material Receipt"
		se.is_opening = self.is_opening
		se.posting_date = self.posting_date
		se.posting_time = self.posting_time
		se.set_posting_time = self.set_posting_time
		se.company = self.company
		se.reference_doctype = self.doctype
		se.reference_docname = self.name
		abbr = frappe.db.get_value('Company',self.company,'abbr')

		for row in self.items:
			if self.is_opening == "Yes":
				se.append("items",{
					'item_code': row.item_code,
					'qty': row.qty,
					'basic_rate': row.basic_rate,
					't_warehouse': row.t_warehouse or self.warehouse,
					'expense_account': 'Temporary Opening - %s' % abbr,
					'merge': row.merge,
					'grade': row.grade,
					'batch_no': row.batch_no
				})
			else:
				se.append("items",{
					'item_code': row.item_code,
					'qty': row.qty,
					'basic_rate': row.basic_rate,
					't_warehouse': row.t_warehouse or self.warehouse,
					'merge': row.merge,
					'grade': row.grade,
					'batch_no': row.batch_no
				})
		if self.pallet_item:
			for d in self.pallet_item:
				if self.is_opening == "Yes":
					se.append("items",{
						'item_code': d.pallet_item,
						'qty': d.qty,
						'basic_rate': 0,
						'expense_account': 'Temporary Opening - %s' % abbr,
						't_warehouse': 'Zero Rated Pallet - %s' % abbr,
						'allow_zero_valuation_rate': 1
					})
				else:
					se.append("items",{
						'item_code': d.pallet_item,
						'qty': d.qty,
						'basic_rate': 0,
						't_warehouse': 'Zero Rated Pallet - %s' % abbr,
						'allow_zero_valuation_rate': 1
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
		frappe.db.commit()

	def update_pallet_item(self):
		count = 0
		if self.package_type == 'Pallet' and self.package_item:
			for d in self.packages:
				if d.package_item == self.package_item:
					count +=1
			if count > 0:
				if self.is_new() and not self.amended_from:				
					self.append("pallet_item",{
						'pallet_item': self.package_item,
						'qty': count
					})
				else:
					for d in self.packages:
						for r in self.pallet_item:
							if d.package_item == r.pallet_item:
								r.qty = count
								break
								
	def validate_gate_pass(self):
		if self.gate_entry_no == 0:
			frappe.throw(_("Please Enter Gate Pass No"))

@frappe.whitelist()
def get_warehouse_details(args):
	if isinstance(args, string_types):
		args = json.loads(args)

	args = frappe._dict(args)

	ret = {}
	if args.warehouse and args.item_code:
		args.update({
			"posting_date": args.posting_date,
			"posting_time": args.posting_time,
		})
		ret = {
			"actual_qty" : get_previous_sle(args).get("qty_after_transaction") or 0,
			"basic_rate" : get_incoming_rate(args)
		}
	return ret