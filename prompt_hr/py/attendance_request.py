import frappe

from frappe import throw
from prompt_hr.py.utils import send_notification_email, check_user_is_reporting_manager





def after_insert(doc, event):
    #* NOTIFYING EMPLOYEE'S REPORTING MANAGER WHEN A ATTENDANCE REQUEST IS CREATED
    notify_reporting_manager(doc)



def notify_reporting_manager(doc):
    """Method to send email to employee's reporting manager when employee creates attendance request
    """
    try:
        if doc.employee:
            rh_emp = frappe.db.get_value("Employee", doc.employee, "reports_to")
            if not rh_emp:
                throw(f"No Reporting Head found for employee {doc.employee}")
            
            rh_user_id = frappe.db.get_value("Employee", rh_emp, "user_id")
            if not rh_user_id:
                throw(f"Reporting Head User ID not found from {rh_emp}")
            
            send_notification_email(
                recipients=[rh_user_id],
                notification_name="Attendance Request Creation",
                doctype="Attendance Request",
                docname=doc.name,
                fallback_subject=f"Attendance Request Created",
                fallback_message=f"<p>Dear Reporting Head,<br> An attendance request has been created—please review it at your convenience.</p>"
            )
            
    except Exception as e:
        frappe.log_error(f"Error while sending notification to reporting manager", frappe.get_traceback())
        frappe.throw(str(e))
        