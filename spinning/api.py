# -*- coding: utf-8 -*-


import frappe
from frappe import _
from frappe.utils import flt
from frappe.contacts.doctype.address.address import get_company_address

@frappe.whitelist()
def company_address(company):
	return get_company_address(company)

@frappe.whitelist()
def make_stock_entry(work_order_id, purpose, qty=None):
	from erpnext.stock.doctype.stock_entry.stock_entry import get_additional_costs

	work_order = frappe.get_doc("Work Order", work_order_id)
	if not frappe.db.get_value("Warehouse", work_order.wip_warehouse, "is_group") \
			and not work_order.skip_transfer:
		wip_warehouse = work_order.wip_warehouse
	else:
		wip_warehouse = None

	stock_entry = frappe.new_doc("Stock Entry")
	stock_entry.purpose = purpose
	stock_entry.work_order = work_order_id
	stock_entry.company = work_order.company
	stock_entry.from_bom = 1
	stock_entry.bom_no = work_order.bom_no
	stock_entry.use_multi_level_bom = work_order.use_multi_level_bom
	stock_entry.fg_completed_qty = qty or (flt(work_order.qty) - flt(work_order.produced_qty))
	if work_order.bom_no:
		stock_entry.inspection_required = frappe.db.get_value('BOM',
			work_order.bom_no, 'inspection_required')

	if purpose=="Material Transfer for Manufacture":
		stock_entry.to_warehouse = wip_warehouse
		stock_entry.project = work_order.project
	else:
		stock_entry.from_warehouse = wip_warehouse
		stock_entry.to_warehouse = work_order.fg_warehouse
		stock_entry.project = work_order.project
		if purpose=="Manufacture":
			additional_costs = get_additional_costs(work_order, fg_qty=stock_entry.fg_completed_qty)
			stock_entry.set("additional_costs", additional_costs)

	stock_entry.get_items()

	if purpose == "Manufacture":
		stock_entry.items[-1].merge = work_order.merge

	return stock_entry.as_dict()

@frappe.whitelist()
def make_workorder_finish(work_order_id):
	work_order = frappe.get_doc("Work Order", work_order_id)
	
	wof = frappe.new_doc("Work Order Finish")
	wof.work_order = work_order_id
	wof.company = work_order.company
	wof.item_code = work_order.production_item
	wof.merge = work_order.merge
	wof.package_type = work_order.package_type
	wof.package_item = work_order.package_item
	wof.is_returnable = work_order.is_returnable
	wof.fg_completed_qty = work_order.qty
	wof.paper_tube = work_order.paper_tube
	wof.spool_weight = work_order.spool_weight
	wof.target_warehouse = work_order.fg_warehouse
	wof.source_warehouse = work_order.source_warehouse
	wof.workstation = work_order.workstation
	# wof.series = work_order.series
	
	return wof

@frappe.whitelist()
def get_merge_wise_package_details(batch_no, warehouse):
	return frappe.get_list("Package", filters={
		'batch_no': batch_no, 
		'warehouse': warehouse, 
		'status': ['!=', "Out of Stock"]
	}, fields = ['name', 'package_type', 'gross_weight', 'net_weight', 'spools', 'remaining_qty', 'status'])
