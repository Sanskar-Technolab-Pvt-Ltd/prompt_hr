import frappe

from datetime import datetime
from dateutil.relativedelta import relativedelta
from frappe.modules.utils import export_customizations


def get_next_date(start_date_str, months):
    """Method to calculate the next date based on given start date and number of months.
    start_date_str: string in 'YYYY-MM-DD' format
    months: float, e.g. 1.5 means 1 month and 15 days (assuming 30-day avg for fraction)
    """
    try:
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
        
        
        whole_months = int(months)
        fractional_month = months - whole_months
        
        
        intermediate_date = start_date + relativedelta(months=whole_months)
        
        
        next_month = intermediate_date + relativedelta(months=1)
        days_in_month = (next_month - intermediate_date).days
        additional_days = int(fractional_month * days_in_month)

        
        final_date = intermediate_date + relativedelta(days=additional_days)
        
        return {"error": 0, "message":final_date.strftime("%Y-%m-%d")}
    except Exception as e:
        frappe.log_error("Error while calculating next date", frappe.get_traceback())
        return {"error": 1, "message": str(e)}
    
    
@frappe.whitelist()
def export_all_customizations(site_doctypes=None):
    """Export customizations for a list of doctypes. Can be called via API."""
    # Optional security check (e.g., restrict to System Manager)
    if not frappe.session.user == "Administrator":
        frappe.throw("Only Administrator can run this.")
    # Default doctypes if not passed in
    doctypes = site_doctypes or [
    # "Department",
    # "Designation",
    # "Employee",
    # "Employee Boarding Activity",
    # "Employee External Work History",
    # "Employee Grade",
    # "Employee Onboarding",
    # "Employee Skill Map",
    "HR Settings",
    # "Interview",
    # "Interview Detail",
    # "Interview Feedback",
    # "Job Applicant",
    # "Job Offer",
    # "Job Opening",
    # "Job Requisition"
    ]
    module = "Prompt HR"
    results = []
    for dt in doctypes:
        try:
            export_customizations(doctype = dt, module=module, sync_on_migrate=True, with_permissions = 0)
            results.append({"doctype": dt, "status": "success"})
        except Exception as e:
            results.append({"doctype": dt, "status": "error", "error": str(e)})
    return results
