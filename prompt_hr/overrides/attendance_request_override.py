import frappe
from frappe import _
from hrms.hr.doctype.attendance_request.attendance_request import AttendanceRequest



class CustomAttendanceRequest(AttendanceRequest):
    def before_submit(self):
        if self.workflow_state == "Approved":
            self.custom_status = "Approved"
        elif self.workflow_state == "Rejected":
            self.custom_status = "Rejected"

    def on_submit(self):
        pass
