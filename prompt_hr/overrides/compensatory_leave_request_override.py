import frappe
from hrms.hr.doctype.compensatory_leave_request.compensatory_leave_request import CompensatoryLeaveRequest
import frappe.utils
from prompt_hr.py.leave_allocation import get_matching_link_field
from frappe import _
from collections import defaultdict
from frappe.utils import getdate

class CustomCompensatoryLeaveRequest(CompensatoryLeaveRequest):

    # ? CALLED ON CANCEL OF COMPENSATORY LEAVE REQUEST
    def on_cancel(self):
        
        # ! SKIP DEFAULT CANCEL IF REJECTED STATES
        if self.get("workflow_state") not in ["Rejected"]:
            super().on_cancel()

        # ? CHANGE WORKFLOW STATE TO CANCELLED WHEN DOCUMENT IS CANCELLED
        if self.get("workflow_state"):
            self.db_set("workflow_state", "Cancelled")

    # ? CALLED ON SUBMIT
    def on_submit(self):
        # ! SKIP DEFAULT SUBMIT IF REJECTED STATES
        if self.get("workflow_state") not in ["Rejected"]:
            super().on_submit()


    def on_update(self):
        if self.has_value_changed("workflow_state"):
            employee = frappe.get_doc("Employee", self.employee)
            employee_id = employee.get("user_id")
            reporting_manager = None
            reporting_manager_name = None
            reporting_manager_id = None
            if employee.reports_to:
                reporting_manager = frappe.get_doc("Employee", employee.reports_to)
                reporting_manager_name = reporting_manager.get("employee_name")
                reporting_manager_id = reporting_manager.get("user_id")
            hr_manager_email = None
            hr_manager_users = frappe.get_all(
                "Employee",
                filters={"company": employee.company},
                fields=["user_id"]
            )

            for hr_manager in hr_manager_users:
                hr_manager_user = hr_manager.get("user_id")
                if hr_manager_user:
                    # Check if this user has the HR Manager role
                    if "HR Manager" in frappe.get_roles(hr_manager_user):
                        hr_manager_email = frappe.db.get_value("User", hr_manager_user, "email")
                        break

                                
            if self.workflow_state == "Pending":
                notification = frappe.get_doc("Notification", "Leave Request Notification")
                if notification:
                    subject = frappe.render_template(notification.subject, {"doc":self,"request_type":"Compensatory Leave Request"})
                    if reporting_manager_id:
                        frappe.sendmail(
                        recipients=reporting_manager_id,
                        message = frappe.render_template(notification.message, {"doc": self,"manager":reporting_manager_name}),
                        subject = subject,
                        reference_doctype=self.doctype,
                        reference_name=self.name,
                    )

            elif self.workflow_state == "Approved":
                employee_notification = frappe.get_doc("Notification", "Leave Request Response By Reporting Manager")
                if employee_notification:
                    subject = frappe.render_template(employee_notification.subject, {"doc":self,"manager":reporting_manager_name,"request_type":"Compensatory Leave Request"})
                    if employee_id:
                        frappe.sendmail(
                        recipients=employee_id,
                        message = frappe.render_template(employee_notification.message, {"doc": self, "manager": reporting_manager_name}),
                        subject = subject,
                        reference_doctype=self.doctype,
                        reference_name=self.name,
                    )

            elif self.workflow_state == "Rejected":
                employee_notification = frappe.get_doc("Notification", "Leave Request Response By Reporting Manager")
                if employee_notification:
                    subject = frappe.render_template(employee_notification.subject, {"doc":self, "manager":reporting_manager_name,"request_type":"Compensatory Leave Request"})
                    if employee_id:
                        frappe.sendmail(
                        recipients=employee_id,
                        message = frappe.render_template(employee_notification.message, {"doc": self, "manager": reporting_manager_name}),
                        subject = subject,
                        reference_doctype=self.doctype,
                        reference_name=self.name,
                    )
                        
    def before_save(self):
        leave_type = frappe.get_doc("Leave Type", self.leave_type)
        employee_doc = frappe.get_doc("Employee", self.employee)
        if leave_type.custom_request_compensatory_within_days_of_working:
            today = frappe.flags.current_date or getdate()
            if (today - getdate(self.work_from_date)).days > leave_type.custom_request_compensatory_within_days_of_working:
                frappe.throw(
                _("You cannot apply for Compensatory Leave for {0}. It must be applied within {1} days of the work date.").format(
                    leave_type.name, leave_type.custom_request_compensatory_within_days_of_working
                )
            )
                
        if leave_type.custom_threshold_limit_for_availing_compensatory:
            apply_dates = defaultdict(list)
            current_date = self.work_from_date
            while current_date <= self.work_end_date:
                month_key = frappe.utils.getdate(current_date).strftime("%b")
                apply_dates[month_key].append(current_date)
                current_date = frappe.utils.add_days(current_date, 1)
            compenstory_leave = frappe.get_all(
                "Compensatory Leave Request",
                filters={"employee": self.employee, "leave_type": self.leave_type, "docstatus": ["!=", 2], "name": ["!=", self.name]},
                fields=["work_from_date", "work_end_date"],
            )
            if compenstory_leave:
                compenstory_leave_dates = defaultdict(list)
                for leave in compenstory_leave:
                    leave_start_date = leave.work_from_date
                    leave_end_date = leave.work_end_date
                    while leave_start_date <= leave_end_date:
                        month_key = frappe.utils.getdate(leave_start_date).strftime("%b")
                        compenstory_leave_dates[month_key].append(leave_start_date)
                        leave_start_date = frappe.utils.add_days(leave_start_date, 1)
                for month in set(list(compenstory_leave_dates.keys()) + list(apply_dates.keys())):
                    total_dates = compenstory_leave_dates[month] + apply_dates[month]
                    if len(total_dates) > leave_type.custom_threshold_limit_for_availing_compensatory:
                        frappe.throw(
                            _(
                                "You cannot apply for more than {0} Compensatory Leave(s) of type {1} in the month of {2}"
                            ).format(
                                leave_type.custom_threshold_limit_for_availing_compensatory,
                                leave_type.name,
                                month
                            )
                        )          
            else:
                for month, dates in apply_dates.items():
                    if len(dates) > leave_type.custom_threshold_limit_for_availing_compensatory:
                        frappe.throw(
                            _(
                                "You cannot apply for more than {0} Compensatory Leave(s) of type {1} in the month of {2}"
                            ).format(
                                leave_type.custom_threshold_limit_for_availing_compensatory,
                                leave_type.name,
                                month
                            )
                        )

        if leave_type.custom_compensatory_applicable_to:
            compensatory_apply = 0
            for compensatory_applicable_to in leave_type.custom_compensatory_applicable_to:
                fieldname = get_matching_link_field(compensatory_applicable_to.document)
                if fieldname:
                    field_value = getattr(employee_doc, fieldname, None)
                    if field_value == compensatory_applicable_to.value:
                        compensatory_apply = 1
                        break
            if compensatory_apply == 0:
                frappe.throw(
                    _("You are not eligible for Compensatory Leave")
                )
