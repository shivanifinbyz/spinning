
import json
import frappe
from frappe import _
from frappe.utils import cstr, flt, cint
from six import string_types

@frappe.whitelist()
def create_transfer(purchase_order, rm_items):
	if isinstance(rm_items, string_types):
		rm_items_list = json.loads(rm_items)
	else:
		frappe.throw(_("No Items available for transfer"))

	if rm_items_list:
		fg_items = list(set(d["item_code"] for d in rm_items_list))
	else:
		frappe.throw(_("No Items selected for transfer"))

	if purchase_order:
		purchase_order = frappe.get_doc("Purchase Order", purchase_order)

	if fg_items:
		items = tuple(set(d["rm_item_code"] for d in rm_items_list))
		item_wh = get_item_details(items)

		mt = frappe.new_doc("Material Transfer")
		mt.is_send_to_subcontractor = 1
		mt.purchase_order = purchase_order.name
		mt.supplier = purchase_order.supplier
		mt.supplier_name = purchase_order.supplier_name
		mt.address = purchase_order.address_display
		mt.company = purchase_order.company
		mt.t_warehouse = purchase_order.set_warehouse

		for item_code in fg_items:
			for rm_item_data in rm_items_list:
				if rm_item_data["item_code"] == item_code:
					rm_item_code = rm_item_data["rm_item_code"]
					
					items_dict = {
						rm_item_code: {
							"po_detail": rm_item_data.get("name"),
							"item_name": rm_item_data["item_name"],
							"description": item_wh.get(rm_item_code, {}).get('description', ""),
							'qty': rm_item_data["qty"],
							's_warehouse': purchase_order.set_warehouse,
							't_warehouse': purchase_order.supplier_warehouse,
							'stock_uom': rm_item_data["stock_uom"],
							'basic_rate':rm_item_data["rate"],
							'basic_amount':rm_item_data["amount"],
							'amount':rm_item_data["amount"],
							'main_item_code': rm_item_data["item_code"],
							'allow_alternative_item': item_wh.get(rm_item_code, {}).get('allow_alternative_item')
						}
					}
					mt.add_to_mt_detail(items_dict)
		return mt.as_dict()
	else:
		frappe.throw(_("No Items selected for transfer"))
	return purchase_order.name

def get_item_details(items):
	item_details = {}
	for d in frappe.db.sql("""select item_code, description, allow_alternative_item from `tabItem`
		where name in ({0})""".format(", ".join(["%s"] * len(items))), items, as_dict=1):
		item_details[d.item_code] = d

	return item_details