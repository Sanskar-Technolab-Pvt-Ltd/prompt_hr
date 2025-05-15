import frappe
import frappe.utils
from prompt_hr.py.leave_allocation import get_matching_link_field
from frappe import _
from frappe.utils import getdate

@frappe.whitelist()
def before_save(doc, method):
    leave_type = frappe.get_doc("Leave Type", doc.leave_type)
    employee_doc = frappe.get_doc("Employee", doc.employee)
    if leave_type.custom_request_compensatory_within_days_of_working:
        today = frappe.flags.current_date or getdate()
        if (today - getdate(doc.work_from_date)).days > leave_type.custom_request_compensatory_within_days_of_working:
            frappe.throw(
            _("You cannot apply for Compensatory Leave for {0}. It must be applied within {1} days of the work date.").format(
                leave_type.name, leave_type.custom_request_compensatory_within_days_of_working
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
                _("You are not eligible for Compensatory Leave for {0}")
            )


def on_cancel(doc, method):
    if doc.get("workflow_state"):
        doc.db_set("workflow_state", "Cancelled")

def on_update(doc, method):
    if doc.has_value_changed("workflow_state"):
        employee = frappe.get_doc("Employee", doc.employee)
        employee_id = employee.get("user_id")
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

                            
        if doc.workflow_state == "Pending":
            notification = frappe.get_doc("Notification", "Leave Request Notification")
            if notification:
                subject = frappe.render_template(notification.subject, {"doc":doc,"request_type":"Compensatory Leave Request"})
                if reporting_manager_id:
                    frappe.sendmail(
                    recipients=reporting_manager_id,
                    message = frappe.render_template(notification.message, {"doc": doc,"role":"Reporting Manager"}),
                    subject = subject,
                    reference_doctype=doc.doctype,
                    reference_name=doc.name,
                )

        elif doc.workflow_state == "Approved":
            employee_notification = frappe.get_doc("Notification", "Leave Request Response By Reporting Manager")
            hr_notification = frappe.get_doc("Notification", "Leave Request Status Update to HR Manager")
            if employee_notification:
                subject = frappe.render_template(employee_notification.subject, {"doc":doc,"manager":reporting_manager_name,"request_type":"Compensatory Leave Request"})
                if employee_id:
                    frappe.sendmail(
                    recipients=employee_id,
                    message = frappe.render_template(employee_notification.message, {"doc": doc}),
                    subject = subject,
                    reference_doctype=doc.doctype,
                    reference_name=doc.name,
                )
            if hr_notification:
                frappe.sendmail(
                    recipients=hr_manager_email,
                    message = frappe.render_template(hr_notification.message, {"doc": doc, "manager":reporting_manager_name}),
                    subject = frappe.render_template(hr_notification.subject, {"doc":doc,"manager":reporting_manager_name, "request_type":"Compensatory Leave Request"}),
                    reference_doctype=doc.doctype,
                    reference_name=doc.name,
                )

                if not hr_manager_email:
                    frappe.throw("HR Manager email not found.")

        elif doc.workflow_state == "Rejected":
            employee_notification = frappe.get_doc("Notification", "Leave Request Response By Reporting Manager")
            if employee_notification:
                subject = frappe.render_template(employee_notification.subject, {"doc":doc, "manager":reporting_manager_name,"request_type":"Compensatory Leave Request"})
                if employee_id:
                    frappe.sendmail(
                    recipients=employee_id,
                    message = frappe.render_template(employee_notification.message, {"doc": doc}),
                    subject = subject,
                    reference_doctype=doc.doctype,
                    reference_name=doc.name,
                )

        elif doc.workflow_state == "Confirmed":
            employee_notification = frappe.get_doc("Notification", "Leave Status Update to Employee")
            if employee_notification:
                subject = frappe.render_template(employee_notification.subject, {"doc":doc,"request_type":"Compensatory Leave Request"})
                if employee_id:
                    frappe.sendmail(
                    recipients=employee_id,
                    message = frappe.render_template(employee_notification.message, {"doc": doc}),
                    subject = subject,
                    reference_doctype=doc.doctype,
                    reference_name=doc.name,
                )


@frappe.whitelist()
def expire_compensatory_leave_after_confirmation():
    # Fetch compensatory leave types with custom validity days
    leave_types = frappe.get_all("Leave Type", filters={"is_compensatory": 1, "custom_leave_validity_days": [">", 0]}, fields=["name"])

    if not leave_types:
        frappe.msgprint("No compensatory leave types with validity defined.")
        return

    # Fetch leave allocations for employees with approved compensatory leave types
    allocations = frappe.get_all("Leave Allocation",
        filters={
            "docstatus": 1,
            "leave_type": ["in", [lt.name for lt in leave_types]]
        },
        fields=["*"]
    )
    # Check each allocation for usage and validity
    for alloc in allocations:
        # Check if any leave has been taken within the allocated period
        leave_taken = frappe.db.exists("Leave Application", {
            "employee": alloc.employee,
            "leave_type": alloc.leave_type,
            "docstatus": 1,
            "from_date": ["between", [alloc.from_date, alloc.to_date]]
        })
        if not leave_taken:
           leave_type = frappe.get_doc("Leave Type", alloc.leave_type)
           expiry_days = frappe.utils.add_days(alloc.from_date, leave_type.custom_leave_validity_days)
           if expiry_days < frappe.utils.getdate():
                ledger_entry = frappe.get_doc({
                    "doctype": "Leave Ledger Entry",
                    "employee": alloc.employee,
                    "leave_type": alloc.leave_type,
                    "company": alloc.company,
                    "leaves": -1*abs(frappe.utils.flt(alloc.total_leaves_allocated)),
                    "transaction_type": "Leave Allocation",
                    "transaction_name": alloc.name,
                    "from_date": getdate(),
                    "to_date": alloc.to_date
                })
                ledger_entry.insert(ignore_permissions=True)
                ledger_entry.submit()