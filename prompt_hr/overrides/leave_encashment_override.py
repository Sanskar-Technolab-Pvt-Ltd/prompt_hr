import frappe
from hrms.hr.doctype.leave_encashment.leave_encashment import LeaveEncashment
from erpnext.controllers.accounts_controller import AccountsController


class CustomLeaveEncashment(LeaveEncashment, AccountsController):
    pass
    