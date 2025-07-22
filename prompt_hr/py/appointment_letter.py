import frappe

def before_save(doc, method=None):
    set_annexure_details(doc)
    if doc.custom_salary_structure and doc.custom_employee_standard_salary:
        employee_standard_salary_doc = frappe.get_doc("Employee Standard Salary",doc.custom_employee_standard_salary)
        doc.custom_monthly_salary = employee_standard_salary_doc.monthly_salary
        if not doc.custom_salary_per_annum or doc.has_value_changed("custom_salary_structure"):
            doc.custom_salary_per_annum = doc.custom_monthly_salary * 12
        if not doc.custom_annual_performance_incentive or  doc.has_value_changed("custom_salary_structure"):
            doc.custom_annual_performance_incentive = employee_standard_salary_doc.annual_performance_incentive
        if not doc.custom_annual_loyalty_bonus or  doc.has_value_changed("custom_salary_structure"):
            doc.custom_annual_loyalty_bonus = employee_standard_salary_doc.annual_loyalty_bonus

def set_annexure_details(doc):
    """
    Set the annexure details in the appointment letter.
    """
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

    # If there is a standard salary record, set related fields
    if employee_standard_salary_list:
        employee_standard_salary_name = employee_standard_salary_list[0]["name"]
        employee_standard_salary_doc = frappe.get_doc("Employee Standard Salary", employee_standard_salary_name)
        old_salary_structure = None
        is_salary_structure_change = False
        # Set custom_employee_standard_salary if not set
        doc.db_set("custom_employee_standard_salary", employee_standard_salary_name)
        # Set custom_salary_structure if not set
        old_salary_structure = doc.custom_salary_structure
        doc.db_set("custom_salary_structure", employee_standard_salary_doc.salary_structure)
        new_salary_structure = employee_standard_salary_doc.salary_structure
        if old_salary_structure != new_salary_structure:
            is_salary_structure_change = True
        # Set earnings and deductions if not set
        if not doc.custom_earnings or is_salary_structure_change:
            if is_salary_structure_change:
                doc.custom_earnings = []
            # Add earnings
            for comp in employee_standard_salary_doc.earnings:
                comp_dict = comp.as_dict().copy()
                comp_dict.pop("name", None)
                comp_dict.pop("parent", None)
                comp_dict.pop("parentfield", None)
                comp_dict.pop("parenttype", None)
                doc.append("custom_earnings", comp_dict)

        if not doc.custom_deductions or is_salary_structure_change:
            # Add deductions
            if is_salary_structure_change:
                doc.custom_deductions = []

            for comp in employee_standard_salary_doc.deductions:
                comp_dict = comp.as_dict().copy()
                comp_dict.pop("name", None)
                comp_dict.pop("parent", None)
                comp_dict.pop("parentfield", None)
                comp_dict.pop("parenttype", None)
                doc.append("custom_deductions", comp_dict)

        if not doc.custom_employer_contribution or is_salary_structure_change:
            # Add deductions
            if is_salary_structure_change:
                doc.custom_employer_contribution = []

            for comp in employee_standard_salary_doc.employer_contribution:
                comp_dict = comp.as_dict().copy()
                comp_dict.pop("name", None)
                comp_dict.pop("parent", None)
                comp_dict.pop("parentfield", None)
                comp_dict.pop("parenttype", None)
                doc.append("custom_employer_contribution", comp_dict)
