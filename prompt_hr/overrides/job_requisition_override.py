# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from hrms.hr.doctype.job_requisition.job_requisition import JobRequisition


class CustomJobRequisition(JobRequisition):
	# ? VALIDATE HOOK TO UPDATE TIME TO FILL
	def validate(self):
		self.set_time_to_fill()
