

import frappe
from frappe.utils import nowdate, add_days

# ! prompt_hr.py.employee_changes_approval.daily_check_employee_changes_approval
# ? FETCH ALL APPROVED EMPLOYEE CHANGES APPROVAL RECORDS WITH EFFECTIVE_DATE AS TODAY
@frappe.whitelist()
def daily_check_employee_changes_approval():
    employee_changes = frappe.get_all(
        "Employee Changes Approval",
        filters={
            "effective_date": add_days(nowdate(), 1),
            "workflow_state": "Approved"  # ? ENSURE ONLY APPROVED RECORDS ARE PROCESSED
        },
        fields=["name"]
    )

    # ? ITERATE THROUGH THE RECORDS AND APPLY CHANGES
    for change in employee_changes:
        try:
            doc = frappe.get_doc("Employee Changes Approval", change.name)
            doc.apply_changes_to_employee()
        except Exception as e:
            # ? LOG ERRORS IF ANY RECORD FAILS TO PROCESS
            frappe.log_error(f"Error applying changes for {change.name}: {str(e)}", 
                             "Employee Changes Approval Cron Job")
