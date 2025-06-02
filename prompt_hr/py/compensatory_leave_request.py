import frappe
import frappe.utils
from prompt_hr.py.leave_allocation import get_matching_link_field
from frappe import _
from collections import defaultdict
from frappe.utils import getdate, flt, add_days, date_diff

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
            
    if leave_type.custom_threshold_limit_for_availing_compensatory:
        apply_dates = defaultdict(list)
        current_date = doc.work_from_date
        while current_date <= doc.work_end_date:
            month_key = frappe.utils.getdate(current_date).strftime("%b")
            apply_dates[month_key].append(current_date)
            current_date = frappe.utils.add_days(current_date, 1)
        compenstory_leave = frappe.get_all(
            "Compensatory Leave Request",
            filters={"employee": doc.employee, "leave_type": doc.leave_type, "docstatus": ["!=", 2], "name": ["!=", doc.name]},
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
    # Get compensatory leave types that have custom validity defined
    leave_types = frappe.get_all(
        "Leave Type",
        filters={"is_compensatory": 1, "custom_leave_validity_days": [">", 0]},
        fields=["name"]
    )

    # Fetch all approved compensatory leave requests for those leave types
    compensatory_leave_requests = frappe.get_all(
        "Compensatory Leave Request",
        filters={
            "docstatus": 1,
            "leave_type": ["in", [lt.name for lt in leave_types]]
        },
        fields=["*"]
    )

    for alloc in compensatory_leave_requests:
        leave_type = frappe.get_doc("Leave Type", alloc.leave_type)

        # Calculate expiry based on the modified date and custom validity days
        expiry_date = add_days(alloc.modified, leave_type.custom_leave_validity_days)
        print(expiry_date)
        # Skip if not yet expired
        if getdate(expiry_date) >= getdate():
            continue

        # Get the original leave allocation linked to the request
        leave_allocation = frappe.get_doc("Leave Allocation", alloc.leave_allocation)

        # Fetch leave applications made under this allocation
        leaves_taken = frappe.get_all(
            "Leave Application",
            filters={
                "employee": alloc.employee,
                "leave_type": alloc.leave_type,
                "docstatus": 1,
                "from_date": [">=", leave_allocation.from_date],
                "to_date": ["<=", leave_allocation.to_date]
            },
            fields=["*"]
        )

        # Calculate total leave days taken
        leave_days_taken = sum(flt(leave.total_leave_days) for leave in leaves_taken)

        # Total allocated leave based on the request duration
        total_allocated = date_diff(alloc.work_end_date, add_days(alloc.work_from_date, -1))

        # Calculate unused leave
        unused_leaves = total_allocated - leave_days_taken

        # If unused leave exists, expire it by adding a negative ledger entry
        if unused_leaves > 0:
            ledger_entry = frappe.get_doc({
                "doctype": "Leave Ledger Entry",
                "employee": alloc.employee,
                "leave_type": alloc.leave_type,
                "company": alloc.company,
                "leaves": -1 * unused_leaves,
                "transaction_type": "Leave Allocation",
                "transaction_name": leave_allocation.name,
                "from_date": getdate("2025-06-12"),
                "to_date": getdate(leave_allocation.to_date)
            })
            ledger_entry.insert(ignore_permissions=True)
            ledger_entry.submit()
