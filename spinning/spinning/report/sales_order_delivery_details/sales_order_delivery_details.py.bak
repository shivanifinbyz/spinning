# Copyright (c) 2013, FinByz Tech Pvt Ltd and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _

def execute(filters=None):
	columns, data = [], []
	columns = get_columns()
	data = get_data(filters)
	return columns, data

def get_conditions(filters):
	conditions = ""

	if filters.get('pending_so'):
		conditions += " AND so.status not in ('Completed', 'Stopped', 'Closed')"

	if filters.get('sales_order'):
		conditions += " AND so.name = '%s'" % filters.get('sales_order')

	if filters.get('customer'):
		conditions += " AND so.customer = '%s'" % filters.get('customer')

	if filters.get('item_code'):
		conditions += " AND soi.item_code = '%s'" % filters.get('item_code')

	return conditions


def get_data(filters):

	conditions = get_conditions(filters)
	
	data = frappe.db.sql("""
		SELECT 
			so.name as sales_order, so.transaction_date, so.customer, soi.item_code, soi.item_name, soi.qty, soi.base_rate, soi.base_amount, soi.name as so_detail
		FROM 
			`tabSales Order` as so LEFT JOIN `tabSales Order Item` as soi ON (so.name = soi.parent)
		WHERE
			so.docstatus = 1 %s
		ORDER BY
			so.transaction_date
		""" % conditions, as_dict = True)

	data_copy = data[:]
	idx = 0

	for row in data_copy:
		idx = insert_delivery_note(data, row, idx + 1)

	return data

def insert_delivery_note(data, row, idx):

	dn_data = frappe.db.sql("""
		SELECT dni.parent as delivery_note, dn.posting_date, dni.qty as delivery_qty
		FROM `tabDelivery Note` as dn LEFT JOIN `tabDelivery Note Item` as dni ON (dn.name = dni.parent)
		WHERE 
			dn.docstatus = 1
			AND dni.so_detail = '%s' 
		ORDER BY
			dn.posting_date
		""" % row.so_detail, as_dict = 1)

	total_qty_delivered = 0.0
	if dn_data:
		row.delivery_note = dn_data[0].delivery_note
		row.posting_date = dn_data[0].posting_date
		row.delivery_qty = dn_data[0].delivery_qty
		total_qty_delivered += dn_data[0].delivery_qty

	for i in dn_data[1:]:
		data.insert(idx, i)
		total_qty_delivered += i.delivery_qty
		idx += 1

	row.delivered_qty = total_qty_delivered
	row.pending_qty = row.qty - total_qty_delivered

	return idx


def get_columns():
	columns = [
		{
			"fieldname": "sales_order",
			"label": _("Sales Order"),
			"fieldtype": "Link",
			"options": "Sales Order",
			"width": 100
		},
		{
			"fieldname": "transaction_date",
			"label": _("SO Date"),
			"fieldtype": "Date",
			"width": 80
		},
		{
			"fieldname": "customer",
			"label": _("Customer"),
			"fieldtype": "Link",
			"options": "Customer",
			"width": 150
		},
		# {
		# 	"fieldname": "item_code",
		# 	"label": _("Item Code"),
		# 	"fieldtype": "Link",
		# 	"options": "Item",
		# 	"width": 150
		# },
		{
			"fieldname": "item_name",
			"label": _("Item Name"),
			"fieldtype": "Data",
			"width": 180
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
			"fieldname": "delivered_qty",
			"label": _("Delivered Qty"),
			"fieldtype": "Float",
			"width": 80
		},
		{
			"fieldname": "pending_qty",
			"label": _("Pending Qty"),
			"fieldtype": "Float",
			"width": 80
		},
		{
			"fieldname": "delivery_note",
			"label": _("Delivery Note"),
			"fieldtype": "Link",
			"options": "Delivery Note",
			"width": 100
		},
		{
			"fieldname": "posting_date",
			"label": _("Delivery Date"),
			"fieldtype": "Date",
			"width": 90
		},
		{
			"fieldname": "delivery_qty",
			"label": _("Delivery Qty"),
			"fieldtype": "Float",
			"width": 80
		},
	
	]

	return columns

def _get_columns():
	return [
		_("Sales Order") + ":Link/Sales Order:100",
		_("Date") + ":Date:100",
		_("Customer") + ":Link/Customer:100",
		_("Item Code") + ":Link/Item:100",
		_("Item Name") + ":Data:100",
		_("Qty") + ":Float:100",
		_("Rate") + ":Currency:100",
		_("Amount") + ":Currency:100",
		_("Delivered Qty") + ":Float:100",
		_("Pending Qty") + ":Float:100",
		_("Delivery Note") + ":Link/Delivery Note:100",
		_("Delivery Date") + ":Date:100",
		_("Delivery Qty") + ":Float:100",
	]
