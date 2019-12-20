// Copyright (c) 2016, FinByz Tech Pvt Ltd and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Purchase Order Receipt Details"] = {
	"filters": [
		{
			"fieldname":"purchase_order",
			"label": __("Purchase Order"),
			"fieldtype": "Link",
			"options": "Purchase Order",
		},
		{
			"fieldname":"supplier",
			"label": __("Supplier"),
			"fieldtype": "Link",
			"options": "Supplier",
		},
		{
			"fieldname":"item_code",
			"label": __("Item Code"),
			"fieldtype": "Link",
			"options": "Item",
		},
		{
			"fieldname":"pending_po",
			"label": __("Pending Purchase Orders"),
			"fieldtype": "Check",
			"default": 1,
		},
	]
};
