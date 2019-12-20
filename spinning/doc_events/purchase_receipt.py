# -*- coding: utf-8 -*-


import frappe
from frappe import _
from frappe.utils import flt, cint
from frappe.model.delete_doc import check_if_doc_is_linked
from spinning.controllers.merge_validation import validate_merge
from spinning.controllers.batch_controller import set_batches

@frappe.whitelist()
def validate(self, method):
	if self._action == 'submit':
		validate_package_qty(self)
		#validate_merge_in_item(self)
		
	set_batches(self, 'warehouse')
	
def validate_merge_in_item(self):
	for row in self.items:
		validate_merge(self,row.merge,row.item_code)
	
@frappe.whitelist()
def before_save(self, method):
	pass
	#update_pallet_item(self)

@frappe.whitelist()
def on_submit(self, method):
	validate_gate_pass(self)
	create_packages(self)
	create_stock_entry(self)
	add_package_consumption(self)
	
@frappe.whitelist()
def on_cancel(self, method):
	clear_package_weight(self)
	cancel_stock_entry(self)
	remove_package_consumption(self)


def validate_package_qty(self):
	for row in self.items:
		has_batch_no = frappe.db.get_value('Item', row.item_code, 'has_batch_no')

		if cint(has_batch_no):
			total_net_weight = sum([d.net_weight for d in self.packages if row.idx == cint(d.row_ref)])

			if flt(row.qty, 4) != flt(total_net_weight, 4):
				frappe.throw(_("#Row {}: Total Net Weight for Item - {} in packages is {}, which doesn't match the Qty {} in Items.".format(row.idx, frappe.bold(row.item_code), total_net_weight, row.qty))(title = "Total Package Error!"))

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
			frappe.throw(_("Item {} is not batch wise in Row {}".format(frappe.bold(row.item_code), row.idx)))

		doc = frappe.new_doc("Package")
		doc.package_no = pkg.package
		doc.package_type = pkg.package_type
		doc.package_item = pkg.package_item
		doc.spools = cint(pkg.spools)
		doc.company = self.company
		doc.warehouse = row.warehouse

		if pkg.package_type == "Pallet":
			doc.is_returnable = pkg.is_returnable
			doc.returnable_by = pkg.returnable_by

		doc.gross_weight = pkg.gross_weight
		doc.net_weight = pkg.net_weight

		doc.batch_no = row.batch_no
		doc.item_code = row.item_code
		doc.item_name = row.item_name
		doc.merge = row.merge
		doc.grade = row.grade

		doc.purchase_document_type = self.doctype
		doc.purchase_document_no = self.name
		doc.purchase_date = self.posting_date
		doc.purchase_time = self.posting_time
		doc.incoming_rate = row.valuation_rate
		doc.ownership_type = "Supplier"
		doc.ownership = self.supplier
		doc.supplier = self.supplier
		doc.supplier_name = frappe.db.get_value("Supplier", self.supplier, 'supplier_name')

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
		doc.save(ignore_permissions=True)

	else:
		frappe.db.commit()
			
def create_stock_entry(self):
	abbr = frappe.db.get_value('Company',self.company,'abbr')
	if self.pallet_item:
		pallet_se = frappe.new_doc("Stock Entry")
		pallet_se.stock_entry_type = "Material Receipt"
		pallet_se.purpose = "Material Receipt"
		pallet_se.posting_date = self.posting_date
		pallet_se.posting_time = self.posting_time
		pallet_se.set_posting_time = self.set_posting_time
		pallet_se.company = self.company
		pallet_se.reference_doctype = self.doctype
		pallet_se.reference_docname = self.name
		
		for row in self.pallet_item:
			pallet_se.append("items",{
				'item_code': row.pallet_item,
				'qty': row.qty,
				'basic_rate': 0,
				't_warehouse': 'Zero Rated Pallet - %s' % abbr,
				'allow_zero_valuation_rate': 1
			})
		try:
			pallet_se.save(ignore_permissions=True)
			pallet_se.submit()
		except Exception as e:
			frappe.throw(str(e))
		else:
			self.db_set('stock_entry_pallet',pallet_se.name)

def cancel_stock_entry(self):
	if self.stock_entry_pallet:
		pallet_se = frappe.get_doc("Stock Entry",self.stock_entry_pallet)
		pallet_se.cancel()
		self.db_set('stock_entry_pallet','')
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
		
def add_package_consumption(self):
	if self.supplier_warehouse and self.supplied_items:
		for row in self.supplied_items:
			remaining_qty = row.required_qty
			package_list = frappe.get_list("Package", {
					'status': ["!=", "Out of Stock"],
					'item_code': row.rm_item_code,
					'batch_no': row.batch_no,
					'warehouse': self.supplier_warehouse,
				}, order_by = "creation DESC")

			for pkg in package_list:
				doc = frappe.get_doc("Package", pkg.name)
				qty = doc.remaining_qty if remaining_qty > doc.remaining_qty else remaining_qty
				doc.add_consumption(self.doctype, self.name, qty)
				doc.save(ignore_permissions=True)
				remaining_qty -= qty

				if remaining_qty <= 0:
					break

def remove_package_consumption(self):
	package_list = frappe.get_list("Package Consumption", filters = {
			'reference_doctype': self.doctype,
			'reference_docname': self.name
		}, fields = 'parent')

	for pkg in package_list:
		doc = frappe.get_doc("Package", pkg.parent)
		doc.remove_consumption(self.doctype, self.name)
		doc.save(ignore_permissions=True)
				