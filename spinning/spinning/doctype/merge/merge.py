# -*- coding: utf-8 -*-
# Copyright (c) 2019, FinByz Tech Pvt Ltd and contributors
# For license information, please see license.txt


import frappe
from frappe.model.document import Document

class Merge(Document):
	pass
	# def autoname(self):
		# merge = self.merge
		
		# i = 1
		# while frappe.db.exists("Merge", merge):
			# merge = merge + "-" + str(i)
			# i += 1
		# self.name = merge