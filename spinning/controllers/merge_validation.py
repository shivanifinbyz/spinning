
import frappe
from frappe import _
from frappe.utils import cstr

@frappe.whitelist()
def validate_merge(self, merge_field = 'merge',item_field = "item_code"):
    if self.doctype == "BOM":
        item_field = "item"
    elif self.doctype == "Work Order":
        item_field = "production_item"
    #merge = self.get(merge_field)
    merge_item = frappe.db.get_value("Merge", self.merge, 'item_code')
    doc_item = self.get(item_field)
    if merge_item != doc_item:
        frappe.throw(_("Please select correct merge for the item {0}".format(doc_item)))

@frappe.whitelist()
def validate_merge_with_doc(doc, merge,item_code):
    merge_item = frappe.db.get_value("Merge", merge, 'item_code')
    if merge_item != item_code:
        frappe.throw(_("Please select correct merge for the item {0}".format(item_code)))
        return merge