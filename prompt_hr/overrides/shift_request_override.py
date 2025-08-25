import frappe
from hrms.hr.doctype.shift_request.shift_request import ShiftRequest
from hrms.hr.utils import validate_active_employee

class CustomShiftRequest(ShiftRequest):
	def validate(self):
		validate_active_employee(self.employee)
		self.validate_from_to_dates("from_date", "to_date")
		self.validate_overlapping_shift_requests()
		self.validate_default_shift()

	def before_save(self):
		if self.employee:
			reporting_manager = frappe.db.get_value("Employee", self.employee, "reports_to")
			if reporting_manager:
				reporting_manager_id  = frappe.db.get_value("Employee", reporting_manager, "user_id")
				if reporting_manager_id:
					self.approver = reporting_manager_id
			
				if self.workflow_state == "Approved by Reporting Manager":
					self.status = "Approved"
				elif self.workflow_state == "Rejected by Reporting Manager":
					self.status = "Rejected"
	
	def before_submit(self):
		if self.workflow_state == "Rejected by HR":
			self.status = "Rejected"

	def on_cancel(self):
		self.db_set("workflow_state", "Cancelled")
		return super().on_cancel()

	def on_update(self):
		self.notify_approval_status()
