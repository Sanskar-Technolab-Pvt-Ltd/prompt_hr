import frappe

def before_save(doc, method=None):
    set_annexure_details(doc)

def set_annexure_details(doc):
    """
    Set the annexure details in the appointment letter.
    """
    print(doc.custom_employee, doc.custom_monthly_salary, doc.custom_employee_standard_salary, doc.custom_salary_structure)
    if not doc.custom_employee:
        return

    # Fetch the latest Employee Standard Salary for the employee and company
    employee_standard_salary_list = frappe.get_all(
        "Employee Standard Salary",
        filters={"employee": doc.custom_employee, "company": doc.company},
        fields=["name"],
        order_by="creation desc",
        limit=1
    )
    employee = frappe.get_doc("Employee", doc.custom_employee)

    # Set custom_monthly_salary if not set
    if not doc.custom_monthly_salary:
        if getattr(doc, "custom_salary_structure_based_on", None) == "CTC Based":
            doc.db_set("custom_monthly_salary", getattr(employee, "ctc", 0))
        else:
            doc.db_set("custom_monthly_salary", getattr(employee, "custom_gross_salary", 0))

    # If there is a standard salary record, set related fields
    if employee_standard_salary_list:
        employee_standard_salary_name = employee_standard_salary_list[0]["name"]
        employee_standard_salary_doc = frappe.get_doc("Employee Standard Salary", employee_standard_salary_name)

        # Set custom_employee_standard_salary if not set
        if not doc.custom_employee_standard_salary:
            doc.db_set("custom_employee_standard_salary", employee_standard_salary_name)
        # Set custom_salary_structure if not set
        if not doc.custom_salary_structure:
            doc.db_set("custom_salary_structure", employee_standard_salary_doc.salary_structure)
        # Set earnings and deductions if not set
        if not doc.custom_earnings:
            # Add earnings
            for comp in employee_standard_salary_doc.earnings:
                comp_dict = comp.as_dict().copy()
                comp_dict.pop("name", None)
                comp_dict.pop("parent", None)
                comp_dict.pop("parentfield", None)
                comp_dict.pop("parenttype", None)
                doc.append("custom_earnings", comp_dict)

        if not doc.custom_deductions:
            # Add deductions
            for comp in employee_standard_salary_doc.deductions:
                comp_dict = comp.as_dict().copy()
                comp_dict.pop("name", None)
                comp_dict.pop("parent", None)
                comp_dict.pop("parentfield", None)
                comp_dict.pop("parenttype", None)
                doc.append("custom_deductions", comp_dict)
