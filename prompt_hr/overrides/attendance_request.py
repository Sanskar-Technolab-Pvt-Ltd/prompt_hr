import frappe
from frappe import _
from hrms.hr.doctype.attendance_request.attendance_request import AttendanceRequest



class CustomAttendanceRequest(AttendanceRequest):
    
    def on_submit(self):
        pass
