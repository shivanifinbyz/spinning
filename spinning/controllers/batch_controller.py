# -*- coding: utf-8 -*-


import frappe
from frappe import _
from frappe.utils import cstr

import json
from six import string_types

def set_batches(self, warehouse_field):
	if self._action == 'submit':
		for row in self.items:
			if not row.get(warehouse_field):
				continue

			has_batch_no = frappe.db.get_value('Item', row.item_code, 'has_batch_no')
			
			if has_batch_no:
				if not row.get('merge'):
					frappe.throw(_("Please set Merge in row {}".format(row.idx)))

				if not row.get('grade'):
					frappe.throw(_("Please set Grade in row {}".format(row.idx)))

				batch_no = get_batch_no(row.as_dict())

				if batch_no:
					row.batch_no = batch_no

				else:
					batch = frappe.new_doc("Batch")
					batch.item = row.item_code
					batch.supplier = getattr(self, 'supplier', None)
					batch.grade = cstr(row.grade)
					batch.merge = cstr(row.merge)
					# batch.reference_doctype = self.doctype
					# batch.reference_name = self.name
					batch.insert(ignore_permissions=True)
					row.batch_no = batch.name

			elif row.grade or row.merge:
				frappe.throw(_("Please clear Grade and Merge for Item {} as it is not batch wise item in row {}".format(row.item_code, row.idx)))

@frappe.whitelist()
def get_batch_no(args):
	"""
	Returns the batch according to Item Code, Merge and Grade

		args = {
			"item_code": "",
			"merge": "",
			"grade": "",
		}
	"""
	def process_args(args):
		if isinstance(args, string_types):
			args = json.loads(args)

		args = frappe._dict(args)
		return args

	def validate_args(args):
		if not args.item_code:
			frappe.throw(_("Please specify Item Code"))

		elif not args.merge:
			frappe.throw(_("Please specify Merge"))

		elif not args.grade:
			frappe.throw(_("Please specify Grade"))

	args = process_args(args)

	validate_args(args)

	batch_nos = frappe.db.sql_list(""" select name from `tabBatch` 
		where grade = %s and merge = %s and item = %s """, (args.grade, args.merge, args.item_code))

	batch_no = None
	if batch_nos:
		batch_no = batch_nos[0]

	return batch_no


def get_fifo_batches(item_code, warehouse, merge):
	batches = frappe.db.sql("""
		select 
			batch_id, sum(actual_qty) as qty from `tabBatch` join `tabStock Ledger Entry` ignore index (item_code, warehouse) 
			on (`tabBatch`.batch_id = `tabStock Ledger Entry`.batch_no )
		where 
			`tabStock Ledger Entry`.item_code = %s 
			and `tabStock Ledger Entry`.warehouse = %s 
			and `tabBatch`.merge = %s 
			and (`tabBatch`.expiry_date >= CURDATE() or `tabBatch`.expiry_date IS NULL)
		group by `tabStock Ledger Entry`.batch_no
		having sum(actual_qty) > 0 
		order by `tabBatch`.creation """, (item_code, warehouse, merge), as_dict=True)

	return batches
