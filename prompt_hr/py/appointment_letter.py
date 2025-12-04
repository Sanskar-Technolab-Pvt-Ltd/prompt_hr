import frappe
from frappe.utils.file_manager import save_file
from frappe.utils.pdf import get_pdf


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


@frappe.whitelist()
def create_appointment_letter_approval(employee_id, letter=None, released_by_emp_code_and_name=None,
                                    send_company_email=False, send_personal_email=False, record= None,
                                    record_link=None):
    """
    Create an Employee Letter Approval record, generate PDF and attach it.
    """
    emp = frappe.get_doc("Employee", employee_id)

    doc = frappe.get_doc({
        "doctype": "Employee Letter Approval",
        "employee": emp.name,
        "employee_name": emp.employee_name,
        "department": emp.department,
        "letter": letter,
        "company_email": emp.company_email,
        "personal_email": emp.personal_email,
        "released_on_company_email": 1 if str(send_company_email).lower() in ("true", "1") else 0,
        "released_on_personal_email": 1 if str(send_personal_email).lower() in ("true", "1") else 0,
        "pending_approval_emp_code_and_name": None,
        "record": record,
        "record_link": record_link,
        "released_by_emp_code_and_name": released_by_emp_code_and_name
    })
    doc.insert(ignore_permissions=True)

    # generate PDF using print format (use frappe.get_print)
    try:
        company_abbr = frappe.db.get_value("Company", emp.company, "abbr")
        # choose print format based on company if you keep different names
        if company_abbr == frappe.db.get_single_value("HR Settings", "custom_prompt_abbr"):
            letter_name = letter
    
        # get PDF bytes from print
        pdf_content = frappe.get_print("Employee", emp.name, print_format=letter_name, as_pdf=True)

        # save file and attach to Employee Letter Approval doc
        file_doc = save_file(f"{emp.name}-{letter_name}.pdf", pdf_content, doc.doctype, doc.name, is_private=False)
        if file_doc:
            try:
                doc.db_set("attachment", file_doc.file_url)
            except Exception:
                pass

    except Exception:
        # fallback to simple html rendering if print format fails
        try:
            html = frappe.render_template("prompt_hr/templates/includes/appointment_letter.html", {"employee": emp, "letter": letter})
            pdf = get_pdf(html)
            file_doc = save_file(f"{emp.name}-{letter}.pdf", pdf, doc.doctype, doc.name, is_private=False)
            if file_doc:
                try:
                    doc.db_set("attachment", file_doc.file_url)
                except Exception:
                    pass
        except Exception:
            frappe.log_error(frappe.get_traceback(), "create_employee_letter_approval: PDF generation failed")

    return {"status": "success", "message": _("Letter recorded: {0}").format(doc.name)}
