import frappe
from frappe import _
from dateutil.relativedelta import relativedelta  
from frappe.utils import getdate


@frappe.whitelist()
def on_update(doc, method):
    # Ensure both fields are numbers (0 if None or not set)
    unserved_days = doc.custom_unserved_notice_days or 0
    monthly_salary = doc.custom_monthly_salary or 0

    amount = unserved_days * monthly_salary / 26

    for row in doc.payables:
        if row.component == "Notice Period Recovery":
            row.amount = amount  # Update the amount for the "Notice Period Recovery" row
            break

@frappe.whitelist()
def open_or_create_gratuity(employee):
    """
    Returns the latest Employee Gratuity document name for the given employee.
    If no gratuity exists, returns None.
    """
    if not employee:
        frappe.throw("Employee is required")

    # Fetch latest gratuity record sorted by creation date (descending)
    employee_gratuity = frappe.get_all(
        "Employee Gratuity",
        filters={"employee": employee, "docstatus":["!=","2"]},
        fields=["name"],
        order_by="creation desc",
        limit=1
    )

    # Return the latest gratuity name if found
    if employee_gratuity:
        return employee_gratuity[0].name

    return None

@frappe.whitelist()
def get_gratuity_button_label(employee):
    # Return dynamic button label based on business logic
    if frappe.db.exists("Employee Gratuity", {"employee": employee,"docstatus":["!=","2"]}):
        return _("View Gratuity")
    else:
        return _("Process Gratuity")

def before_submit(doc, method=None):
    # Ensure dates are parsed correctly
    joining_date = getdate(doc.date_of_joining)
    relieving_date = getdate(doc.relieving_date)

    # Get the number of years between joining and relieving
    date_diff = relativedelta(relieving_date, joining_date).years

    # Proceed only if the employee has worked for 5 or more years
    if date_diff >= 5:
        # Try to get or create the Employee Gratuity record
        gratuity = open_or_create_gratuity(doc.employee)

        if gratuity:
            gratuity_doc = frappe.get_doc("Employee Gratuity", gratuity)

            # If gratuity exists but is not submitted, prevent submission
            if gratuity_doc and gratuity_doc.docstatus == 0:
                frappe.throw("Gratuity must be submitted before submitting Full and Final Statement.")
        else:
            # No gratuity record exists; prevent submission
            frappe.throw("Gratuity must be created and submitted before Full and Final Statement submission.")
    

# ? HOOK: BEFORE INSERT FOR FULL AND FINAL STATEMENT
def before_insert(doc, method):
    doc.set(
        "custom_exit_checklist_status",
        get_sorted_exit_checklist_status_from_employee(doc.employee)
    )


# ? FUNCTION TO GET SORTED CHECKLIST STATUS FROM EMPLOYEE
def get_sorted_exit_checklist_status_from_employee(employee):
    if not employee:
        return []

    # ? Fetch existing checklist rows from Employee
    employee_rows = frappe.get_all(
        "Exit Checklist Status",
        filters={"parenttype": "Employee", "parent": employee},
        fields=["department", "status"]
    )

    # ? Hardcoded alphabetical department order
    department_order = [
        "IT",
        "Engineering"
    ]

    # ? Convert fetched rows to a map
    status_map = {row["department"]: row["status"] for row in employee_rows}

    # ? Return sorted checklist rows (fallback to 'Pending')
    return [
        {"department": dept, "status": status_map.get(dept, "Pending")}
        for dept in department_order
    ]