import frappe
from frappe import _
from dateutil.relativedelta import relativedelta  
from frappe.utils import getdate




def on_submit(doc, event):
    validate_payroll_and_update_linked_payroll_entry(doc)

# * METHOD TO CHECK IF THE PAYROLL ENTRY IS LINKED OR NOT IF NOT THEN INFORMING ACCOUNT OTHERWISE ADDING THE FNF ID IN THE LINKED PAYROLL ENTRY FOR THAT EMPLOYEE
def validate_payroll_and_update_linked_payroll_entry(doc):
    if doc.custom_payroll_entry:
        payroll_doc = frappe.get_doc("Payroll Entry", doc.custom_payroll_entry)

        for row in payroll_doc.custom_pending_fnf_details:
            if doc.employee == row.get("employee"):
                row.fnf_record = doc.name                
        payroll_doc.save(ignore_permissions=True)
    else:
        account_user_users = frappe.db.get_all("Has Role", {"role": "S - Payroll Accounting", "parenttype": "User", "parent": ["not in", ["Administrator"]]}, ["parent"])
        if account_user_users:                                                
            account_user_emails = [user.get("parent") for user in account_user_users]
            fnf_link = frappe.utils.get_url_to_form("Full and Final Statement", doc.name)            
            # frappe.sendmail(
            #     recipients=account_user_emails,
            #     subject="Full and Final Statement",
            #     message=f"""Full and Final Statement has been released by HR department. You can view it here: {fnf_link}"""
            # )

# * METHOD TO SEND MAIL WHEN RELEASE FNF BUTTON IS CLICKED
@frappe.whitelist()
def send_release_fnf_mail(fnf_id):
    try:
        account_user_users = frappe.db.get_all("Has Role", {"role": "S - Payroll Accounting", "parenttype": "User", "parent": ["not in", ["Administrator"]]}, ["parent"])
        if account_user_users:           
            account_user_emails = [user.get("parent") for user in account_user_users]                                     
            fnf_link = frappe.utils.get_url_to_form("Full and Final Statement", fnf_id)            
            # frappe.sendmail(
            #     recipients=account_user_emails,
            #     subject="Full and Final Statement",
            #     message=f"""Full and Final Statement has been released by HR department. You can view it here: {fnf_link}"""
            # )
    except Exception as e:
        frappe.log_error("fnf send_release_fnf_email_error", frappe.get_traceback())
        frappe.throw(str(e), title="Error while sending mails to account users")


@frappe.whitelist()
def custom_get_payable_component(doc):
    """
    Get the list of components to be added to the payables table
    """
    return [
        # "Notice Period Recovery", 
        "Expense Claim",
        "Leave Encashment",
    ]





@frappe.whitelist()
def custom_get_receivable_component(doc):
    """
    Modify function to add Imprest Account to the receivables table
    """
    receivables = ["Employee Advance", "Notice Period Recovery"]
    if "lending" in frappe.get_installed_apps():
        receivables.append("Loan")
    company_abbr = frappe.get_doc("Company", doc.company).abbr
    if company_abbr == frappe.db.get_single_value("HR Settings", "custom_indifoss_abbr"):
        receivables.append("Imprest Amount")
    return receivables

@frappe.whitelist()
def custom_create_component_row(doc, components, component_type):
    """
    Modified function to create component rows in the payables table
    - Added custom logic for Notice Period Recovery component
    - Added custom logic for Expense Claim component
    - Added custom logic for Gratuity component
    - Added custom logic for Leave Encashment component
    - Added custom logic for Employee Advance component
    - Added custom logic for Loan component
    """
    for component in components:
        if component == "Notice Period Recovery":
            doc.append(
                component_type,
                {
                    "status": "Unsettled",
                    "component": component,
                    "amount": (
                            0
                            if not doc.custom_unserved_notice_days or not doc.custom_monthly_salary
                            else round((doc.custom_unserved_notice_days * doc.custom_monthly_salary) / 30)
                        ),

                },
            )
        elif component == "Expense Claim":
            expense_claim_docs = frappe.get_all(
                "Expense Claim",
                fields=["name", "total_claimed_amount"],
                filters={"docstatus": ["!=", 2], "employee": doc.employee, "status": ["in",["Unpaid","Draft"]], "workflow_state": ["in",["Sent to Accounting Team","Expense Claim Submitted"]]},
            )
            if expense_claim_docs:
                for expense_claim in expense_claim_docs:
                        doc.append(
                        component_type,
                        {
                            "status": "Unsettled",
                            "component": component,
                            "reference_document_type": "Expense Claim",
                            "reference_document": expense_claim.name,
                            "amount": round(expense_claim.total_claimed_amount),
                        },
                    )
        elif component == "Leave Encashment":
            leave_encashment_docs = frappe.get_all(
                "Leave Encashment",
                fields=["name", "encashment_amount"],
                filters={"docstatus": 1, "employee": doc.employee, "status": "Unpaid"},
            )
            if leave_encashment_docs:
                for leave_encashment_doc in leave_encashment_docs:
                    doc.append(
                        component_type,
                        {
                            "status": "Unsettled",
                            "component": component,
                            "reference_document_type": "Leave Encashment",
                            "reference_document": leave_encashment_doc.name,
                            "amount": round(leave_encashment_doc.encashment_amount),
                        },
                    )
        elif component == "Employee Advance":
            employee_advance_docs = frappe.get_all(
                "Employee Advance",
                fields=["name", "advance_amount"],
                filters={"docstatus": 1, "employee": doc.employee, "status": "Unpaid"},
            )
            if employee_advance_docs:
                for employee_advance_doc in employee_advance_docs:
                    doc.append(
                        component_type,
                        {
                            "status": "Unsettled",
                            "component": component,
                            "reference_document_type": "Employee Advance",
                            "reference_document": employee_advance_doc.name,
                            "amount": round(employee_advance_doc.advance_amount),
                        },
                    )
        elif component == "Loan":
            loan_docs = frappe.get_all(
                "Loan",
                fields=["name", "total_payment", "total_amount_paid"],
                filters={"docstatus": 1, "applicant": doc.employee, "status": "Disbursed"},
            )
            if loan_docs:
                for loan_doc in loan_docs:
                    doc.append(
                        component_type,
                        {
                            "status": "Unsettled",
                            "component": component,
                            "reference_document_type": "Loan",
                            "reference_document": loan_doc.name,
                            "amount": round(loan_doc.total_payment - loan_doc.total_amount_paid),
                        },
                    )

        elif component == "Imprest Amount":
            imprest_allocations = frappe.get_all(
                "Imprest Allocation",
                fields=["*"],
                filters={"docstatus": 1, "company": doc.company},
                order_by="creation desc",
                limit = 1,
            )
            if imprest_allocations:
                imprest_details = frappe.get_all(
                    "Imprest Details",
                    fields=["*"],
                    filters={"parent": imprest_allocations[0].name},
                )
                if imprest_details:
                    employee_grade = frappe.get_value(
                        "Employee",
                        doc.employee,
                        "grade",
                    )
                    if employee_grade:
                        for detail in imprest_details:
                            if detail.grade == employee_grade:
                                doc.append(
                                    component_type,
                                    {
                                        "status": "Unsettled",
                                        "component": component,
                                        "amount": round(detail.imprest_amount),
                                    },
                                )

        else:
            doc.append(
                component_type,
                {
                    "status": "Unsettled",
                    "reference_document_type": component if component != "Bonus" else "Additional Salary",
                    "component": component,
                },
            )

@frappe.whitelist()
def on_update(doc, method):
    # Ensure both fields are numbers (0 if None or not set)
    unserved_days = doc.custom_unserved_notice_days or 0
    monthly_salary = doc.custom_monthly_salary or 0

    amount = unserved_days * monthly_salary / 30

    for row in doc.receivables:
        if row.component == "Notice Period Recovery":
            row.amount = round(amount)  # Update the amount for the "Notice Period Recovery" row
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