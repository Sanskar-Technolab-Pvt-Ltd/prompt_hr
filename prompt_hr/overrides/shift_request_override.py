import frappe
from hrms.hr.doctype.shift_request.shift_request import ShiftRequest
from hrms.hr.utils import validate_active_employee, share_doc_with_approver
from frappe.utils import add_days
from prompt_hr.py.utils import get_reporting_manager_info, create_notification_log
from frappe import _

class CustomShiftRequest(ShiftRequest):
    def before_validate(self):
        if not self.is_new() and self.workflow_state == "Cancelled by Employee":
            shift_request_doc = self.as_dict()
            self.delete(ignore_permissions=True)
            employee = shift_request_doc.employee
            reporting_manager = shift_request_doc.custom_reporting_manager

            # ? Get user IDs and names if present
            employee_user_id = frappe.db.get_value('Employee', employee, "user_id") if employee else None
            reporting_manager_id = frappe.db.get_value("Employee", reporting_manager, "user_id") if reporting_manager else None
            reporting_manager_name = None
            if reporting_manager:
                reporting_manager_name = frappe.db.get_value("Employee", reporting_manager, "employee_name")

            if employee_user_id or reporting_manager_id:
                notification_doc = frappe.get_doc("Notification", "Shift Request Deleted Notification")
                if notification_doc:
                    subject = frappe.render_template(notification_doc.subject, {"docname": shift_request_doc.name})

                    if employee_user_id:
                        message = frappe.render_template(notification_doc.message, {"doc": shift_request_doc, "user": shift_request_doc.employee_name})
                        frappe.sendmail(
                            recipients=[employee_user_id],
                            subject=subject,
                            message=message,
                        )
                        create_notification_log(employee_user_id, subject, message, "Shift Request")

                    if reporting_manager_id:
                        user_display_name = reporting_manager_name or reporting_manager_id
                        message = frappe.render_template(notification_doc.message, {"doc": shift_request_doc, "user": user_display_name})
                        frappe.sendmail(
                            recipients=[reporting_manager_id],
                            subject=subject,
                            message=message,
                        )
                        create_notification_log(reporting_manager_id, subject, message, "Shift Request")

            frappe.db.commit()
            frappe.msgprint(
                _("Shift Request has been deleted successfully. You can go back to the Shift Request List to continue."),
                title=_("Success"),
                indicator="green",
                raise_exception=True,
                primary_action={
                    "label": _("Go to Shift Request List"),
                    "client_action": "frappe.set_route",
                    "args": ["List", "Shift Request"],
                }
            )

    def before_insert(self):
        self.custom_auto_approve = 0

    def validate(self):
        validate_active_employee(self.employee)
        self.validate_from_to_dates("from_date", "to_date")
        self.validate_overlapping_shift_requests()
        self.validate_default_shift()

    def before_save(self):
        # ? === AUTO SET APPROVER BASED ON REPORTING MANAGER ===
		
        if self.employee:
            reporting_manager = frappe.db.get_value(
                "Employee", self.employee, "reports_to"
            )
            if reporting_manager:
                reporting_manager_id = frappe.db.get_value(
                    "Employee", reporting_manager, "user_id"
                )
                if reporting_manager_id:
                    self.approver = reporting_manager_id

            

    def before_submit(self):
        # status sync with workflow
        if self.workflow_state == "Rejected":
            self.status = "Rejected"
        elif self.workflow_state == "Approved":
            align_shift_assignments(self)
            self.status = "Approved"

    def on_cancel(self):
        self.db_set("workflow_state", "Cancelled")
        return super().on_cancel()

    def on_update(self):
        self.notify_approval_status()
        if self.approver:
            share_doc_with_approver(self, self.approver)

        if self.workflow_state == "Pending" and (self.is_new() or self.has_value_changed("workflow_state")):
            manager_info = get_reporting_manager_info(self.employee)
            if manager_info:
                self.db_set("custom_pending_approval_at", f"{manager_info['name']} - {manager_info['employee_name']}")
                if manager_info.get("user_id"):
                    notification = frappe.get_doc("Notification", "Shift Request Pending Approval")
                    if notification:
                        message = frappe.render_template(
                            notification.message,
                            {"doc": self, "manager_name": manager_info.get("employee_name")}
                        )
                        subject = frappe.render_template(
                            notification.subject,
                            {"doc": self, "manager_name": manager_info.get("employee_name")}
                        )
                        frappe.sendmail(
                            recipients=[manager_info.get("user_id")],
                            subject=subject,
                            message=message,
                            reference_doctype=self.doctype,
                            reference_name=self.name,
                        )
                        create_notification_log(manager_info.get("user_id"), subject, message, "Shift Request", self.name)
                        
        else:
            self.db_set("custom_pending_approval_at", "")
            if not self.is_new():
                auto_approve = frappe.db.get_value("Shift Request", self.name, "custom_auto_approve")
                if auto_approve:
                    is_email_sent_allowed = frappe.db.get_single_value("HR Settings", "custom_send_auto_approve_doc_emails") or 0
                    if not is_email_sent_allowed:
                        return
            if (self.workflow_state == "Approved" or self.workflow_state == "Rejected") and self.has_value_changed("workflow_state"):
                manager_info = get_reporting_manager_info(self.employee)
                employee_user_id = frappe.db.get_value("Employee", self.employee, "user_id")
                if manager_info and employee_user_id:
                    notification = frappe.get_doc("Notification", "Shift Request Response To Employee")
                    if notification:
                        message = frappe.render_template(
                            notification.message,
                            {"doc": self, "manager_name": manager_info.get("employee_name")}
                        )
                        subject = frappe.render_template(
                            notification.subject,
                            {"doc": self, "manager_name": manager_info.get("employee_name")}
                        )
                        frappe.sendmail(
                            recipients=[employee_user_id],
                            subject=subject,
                            message=message,
                            reference_doctype=self.doctype,
                            reference_name=self.name,
                        )
                        create_notification_log(employee_user_id, subject, message, "Shift Request", self.name)


import frappe
from frappe.utils import add_days

def align_shift_assignments(doc):
    """
    ! FUNCTION: Align active shift assignments when a new one is created
    ? Flow:
        - Find current active shift assignment (without end_date)
        - Close it by setting end_date = doc.from_date - 1
        - Create a new shift assignment starting from doc.to_date
    """

    # ? === GET CURRENT ACTIVE SHIFT ASSIGNMENT ===
    shift_assignment = frappe.db.get_value(
        "Shift Assignment",
        {"employee": doc.employee, "end_date": ["is","not set"], "status": "Active"},
        ["name", "shift_type"],
    )

    if not shift_assignment:
        frappe.throw(
            ("No active Shift Assignment found for Employee {0}").format(doc.employee)
        )

    shift_assignment_name, existing_shift_type = shift_assignment

    # ? === UPDATE OLD SHIFT ASSIGNMENT TO CLOSE IT ===
    close_date = add_days(doc.from_date, -1)

    frappe.db.set_value(
        "Shift Assignment",
        shift_assignment_name,
        "end_date",
        close_date
    )

    # ? === CREATE NEW SHIFT ASSIGNMENT ===
    new_shift_assignment = frappe.get_doc({
        "doctype": "Shift Assignment",
        "employee": doc.employee,
        "company": doc.company,
        "employee_name": doc.employee_name,
        "department": doc.department,
        "shift_type": existing_shift_type,
        "start_date": add_days(doc.to_date, 1),
        "status": "Active"
    })
    new_shift_assignment.insert(ignore_permissions=True)
    new_shift_assignment.submit()
