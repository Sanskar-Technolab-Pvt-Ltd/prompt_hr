import frappe
from erpnext.projects.doctype.timesheet.timesheet import Timesheet
from frappe.model.document import Document
from frappe.utils import flt


class CustomTimesheet(Timesheet):
    def set_status(self):
        # self.status = {"0": "Draft", "1": "Submitted", "2": "Cancelled"}[str(self.docstatus or 0)] OLD
        self.status = {"0":self.workflow_state,"1": "Submitted", "2": "Cancelled"}[str(self.docstatus or 0)] 

        if flt(self.per_billed, self.precision("per_billed")) >= 100.0:
            self.status = "Billed"

        if self.sales_invoice:
            self.status = "Completed"