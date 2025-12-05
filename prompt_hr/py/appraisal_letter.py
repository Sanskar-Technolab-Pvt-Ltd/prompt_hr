import frappe
from prompt_hr.py.appointment_letter import set_annexure_details
from prompt_hr.py.utils import get_applicable_print_format,send_notification_email, get_prompt_company_name
from frappe.utils.file_manager import save_file
from frappe.utils.pdf import get_pdf
from frappe import _

def before_save(doc, method=None):
    doc.custom_employee = doc.employee
    set_annexure_details(doc)


@frappe.whitelist()
def trigger_apprisal_notification(name, to=None, cc=None):
    """Send appointment letter email with TO & CC support"""

    to = frappe.parse_json(to) if to else []
    cc = frappe.parse_json(cc) if cc else []

    doc = frappe.get_doc("Appraisal", name)
    employee = frappe.get_doc("Employee", doc.employee)

    #  Determine Preferred Email
    preferred = employee.prefered_contact_email
    email = (
        employee.company_email if preferred == "Company Email"
        else employee.personal_email if preferred == "Personal Email"
        else employee.prefered_email if preferred == "User ID"
        else employee.personal_email
    )

    # Ensure applicant email is always in TO
    if email not in to:
        to.append(email)

    #  Check Letter Print Format
    is_prompt = doc.company == get_prompt_company_name()

    print_format = get_applicable_print_format(
        is_prompt=is_prompt, 
        doctype=doc.doctype
    ).get("print_format")

    #  Send Email
    send_notification_email(
        recipients=to,
        cc=cc,
        doctype=doc.doctype,
        docname=doc.name,
        notification_name="Appraisal Letter",
        send_attach=True,
        print_format=print_format
    )

    return "Loan Agreement Sent Successfully"


@frappe.whitelist()
def create_appraisal_letter_approval(employee_id, letter=None, released_by_emp_code_and_name=None,
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
        print("error")
        # fallback to simple html rendering if print format fails
        try:
            html = frappe.render_template("prompt_hr/templates/includes/appraisal_letter.html", {"employee": emp, "letter": letter})
            pdf = get_pdf(html)
            file_doc = save_file(f"{emp.name}-{letter}.pdf", pdf, doc.doctype, doc.name, is_private=False)
            if file_doc:
                try:
                    doc.db_set("attachment", file_doc.file_url)
                except Exception:
                    pass
        except Exception:
            frappe.log_error(frappe.get_traceback(), "create_appraisal_letter_approval: PDF generation failed")

    return {"status": "success", "message": _("Letter recorded: {0}").format(doc.name)}
