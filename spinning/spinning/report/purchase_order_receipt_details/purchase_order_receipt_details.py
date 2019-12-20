# Copyright (c) 2013, FinByz Tech Pvt Ltd and contributors
# For license information, please see license.txt


import frappe
from frappe import _


def execute(filters=None):
	columns, data = [], []
	columns = get_columns()
	data = get_data(filters)
	return columns, data

def get_conditions(filters):
	conditions = ""

	if filters.get('pending_po'):
		conditions += " AND po.status not in ('Stopped', 'Closed')"

	if filters.get('purchase_order'):
		conditions += " AND po.name = '%s'" % filters.get('purchase_order')

	if filters.get('supplier'):
		conditions += " AND po.supplier = '%s'" % filters.get('supplier')

	if filters.get('item_code'):
		conditions += " AND poi.item_code = '%s'" % filters.get('item_code')

	return conditions

def get_data(filters):

	conditions = get_conditions(filters)

	data = frappe.db.sql("""
		SELECT
			po.name as purchase_order, po.transaction_date, po.supplier, poi.item_code, poi.item_name, poi.qty, poi.base_rate, poi.base_amount, poi.received_qty as total_qty_received, poi.name as purchase_order_item
		FROM
			`tabPurchase Order` as po LEFT JOIN `tabPurchase Order Item` as poi ON (po.name = poi.parent)
		WHERE
			po.docstatus = 1 %s
		""" % conditions, as_dict = True)

	data_copy = data[:]
	idx = 0

	for row in data_copy:
		idx = insert_purchase_receipts(data, row, idx + 1)

	return data

def insert_purchase_receipts(data, row, idx):
	pr_data = frappe.db.sql("""
		SELECT pr.name as purchase_receipt, pr.posting_date, pri.qty as received_qty
		FROM `tabPurchase Receipt` as pr LEFT JOIN `tabPurchase Receipt Item` as pri ON (pr.name = pri.parent)
		WHERE 
			pr.docstatus = 1
			AND pri.purchase_order_item = '%s' 
		""" % row.purchase_order_item, as_dict = 1)

	if pr_data:
		row.purchase_receipt = pr_data[0].purchase_receipt
		row.posting_date = pr_data[0].posting_date
		row.received_qty = pr_data[0].received_qty

	for i in pr_data[1:]:
		data.insert(idx, i)
		idx += 1

	return idx


def get_columns():
	columns = [
		{
			"fieldname": "purchase_order",
			"label": _("Purchase Order"),
			"fieldtype": "Link",
			"options": "Purchase Order",
			"width": 150
		},
		{
			"fieldname": "transaction_date",
			"label": _("Date"),
			"fieldtype": "Date",
			"width": 100
		},
		{
			"fieldname": "supplier",
			"label": _("Supplier"),
			"fieldtype": "Link",
			"options": "Supplier",
			"width": 150
		},
		{
			"fieldname": "item_name",
			"label": _("Item Name"),
			"fieldtype": "Data",
			"width": 150
		},
		{
			"fieldname": "qty",
			"label": _("Qty"),
			"fieldtype": "Float",
			"width": 80
		},
		{
			"fieldname": "base_rate",
			"label": _("Rate"),
			"fieldtype": "Float",
			"width": 80
		},
		{
			"fieldname": "base_amount",
			"label": _("Amount"),
			"fieldtype": "Float",
			"width": 100
		},
		{
			"fieldname": "total_qty_received",
			"label": _("Total Qty Received"),
			"fieldtype": "Float",
			"width": 100
		},
		{
			"fieldname": "purchase_receipt",
			"label": _("Purchase Receipt"),
			"fieldtype": "Link",
			"options": "Purchase Receipt",
			"width": 100
		},
		{
			"fieldname": "posting_date",
			"label": _("Purchase Receipt Date"),
			"fieldtype": "Date",
			"width": 100
		},
		{
			"fieldname": "received_qty",
			"label": _("Received Qty"),
			"fieldtype": "Float",
			"width": 100
		},
	]

	return columns
