# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from frappe import _
from frappe.utils import flt, cint, getdate

def execute(filters=None):
	if not filters: filters = {}

	float_precision = cint(frappe.db.get_default("float_precision")) or 3

	columns = get_columns(filters)
	item_map = get_item_details(filters)
	iwb_map = get_item_warehouse_batch_map(filters, float_precision)

	data = []
	for item in sorted(iwb_map):
		for wh in sorted(iwb_map[item]):
			for batch in sorted(iwb_map[item][wh]):
				qty_dict = iwb_map[item][wh][batch]
				if qty_dict.opening_qty or qty_dict.in_qty or qty_dict.out_qty or qty_dict.bal_qty:
					data.append([item, item_map[item]["item_name"],item_map[item]["item_group"], item_map[item]["description"], wh, batch,
						flt(qty_dict.opening_qty, float_precision), flt(qty_dict.in_qty, float_precision),
						flt(qty_dict.out_qty, float_precision), flt(qty_dict.bal_qty, float_precision),
						item_map[item]["stock_uom"]
					])

	return columns, data

def get_columns(filters):
	"""return columns based on filters"""

	columns = [_("Item") + ":Link/Item:100"] + [_("Item Name") + "::150"] + [_("Item Group") + "::150"] + [_("Description") + "::150"] + \
	[_("Warehouse") + ":Link/Warehouse:100"] + [_("Batch") + ":Link/Batch:100"] + [_("Opening Qty") + ":Float:90"] + \
	[_("In Qty") + ":Float:80"] + [_("Out Qty") + ":Float:80"] + [_("Balance Qty") + ":Float:90"] +\
	[_("UOM") + "::90"]


	return columns

def get_conditions(filters):
	conditions = ""
	
	if not filters.get("from_date"):
		frappe.throw(_("'From Date' is required"))

	if filters.get("to_date"):
		conditions += " and SLE.posting_date <= '%s'" % filters["to_date"]
	else:
		frappe.throw(_("'To Date' is required"))
		
	if filters.get("warehouse"): conditions += " and SLE.warehouse = '%s'" % filters["warehouse"]
	
	if filters.get("item_code"): conditions += " and SLE.item_code = '%s'" % filters["item_code"]
	
	if filters.get("item_group"): conditions += " and I.item_group = '%s'" % filters["item_group"]
	
	return conditions

#get all details
def get_stock_ledger_entries(filters):
	conditions = get_conditions(filters)
	return frappe.db.sql("""select SLE.item_code, SLE.batch_no, SLE.warehouse,
		SLE.posting_date, SLE.actual_qty, I.item_group
		from `tabStock Ledger Entry` SLE join `tabItem` I
		on (SLE.item_code = I.item_code)
		where SLE.docstatus < 2 and ifnull(SLE.batch_no, '') != '' %s order by SLE.item_code, SLE.warehouse""" %
		conditions, as_dict=1)

def get_item_warehouse_batch_map(filters, float_precision):
	sle = get_stock_ledger_entries(filters)
	iwb_map = {}

	from_date = getdate(filters["from_date"])
	to_date = getdate(filters["to_date"])

	for d in sle:
		iwb_map.setdefault(d.item_code, {}).setdefault(d.warehouse, {})\
			.setdefault(d.batch_no, frappe._dict({
				"opening_qty": 0.0, "in_qty": 0.0, "out_qty": 0.0, "bal_qty": 0.0,
			}))
		qty_dict = iwb_map[d.item_code][d.warehouse][d.batch_no]
		if d.posting_date < from_date:
			qty_dict.opening_qty = flt(qty_dict.opening_qty, float_precision) \
				+ flt(d.actual_qty, float_precision)
		elif d.posting_date >= from_date and d.posting_date <= to_date:
			if flt(d.actual_qty) > 0:
				qty_dict.in_qty = flt(qty_dict.in_qty, float_precision) + flt(d.actual_qty, float_precision)
			else:
				qty_dict.out_qty = flt(qty_dict.out_qty, float_precision) \
					+ abs(flt(d.actual_qty, float_precision))

		qty_dict.bal_qty = flt(qty_dict.bal_qty, float_precision) + flt(d.actual_qty, float_precision)		

	return iwb_map

def get_item_details(filters):
	item_map = {}
	for d in frappe.db.sql("select name, item_name, item_group, description, stock_uom from tabItem", as_dict=1):
		item_map.setdefault(d.name, d)

	return item_map