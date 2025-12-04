import frappe
from frappe.utils import getdate,cint, flt, add_days,nowdate
from hrms.payroll.doctype.salary_slip.salary_slip_loan_utils import if_lending_app_installed, _get_loan_details
from typing import TYPE_CHECKING
from frappe import _
from frappe.utils.file_manager import save_file
from frappe.utils.pdf import get_pdf


if TYPE_CHECKING:
	from hrms.payroll.doctype.salary_slip.salary_slip import SalarySlip

def on_update(doc, method):
    if doc.loan_product:
        loan_product = frappe.get_doc("Loan Product", doc.loan_product)
        if loan_product.custom_work_tenure_to_apply_for_loan:
            employee_joining_date = frappe.get_value(
                "Employee",
                doc.applicant,
                "date_of_joining",
            )
            if employee_joining_date:
                # Calculate the difference in months between the two dates
                difference_in_months = frappe.utils.month_diff(frappe.utils.nowdate(), employee_joining_date)
                difference_in_years = difference_in_months / 12
                # Check that Employee Tenure is greater than or equal to the minimum work tenure to apply for the loan
                if difference_in_years < loan_product.custom_work_tenure_to_apply_for_loan:
                    frappe.throw(
                        "You are not eligible for this loan as you have not completed the minimum work tenure of {} years.".format(
                            loan_product.custom_work_tenure_to_apply_for_loan
                        )
                    )
        if loan_product.custom_is_guarantor_required:
            if not doc.custom_guarantor:
                frappe.throw("Guarantor is required for this loan product.")
        # Check if the employee has any existing loans that are either Disbursed or Sanctioned
        employee_exists_loans = frappe.get_all(
            "Loan",
            filters={
                "applicant": doc.applicant,
                "status": ["in", ["Disbursed", "Sanctioned"]],
                "docstatus": 1,
            },
            fields=["name"],
        )

        if employee_exists_loans:
            frappe.throw("You already have an existing loan that is either Disbursed or Sanctioned.")

        if loan_product.custom_loan_avail_criteria:
            employee_total_loan_applications = frappe.get_all(
                "Loan Application",
                filters={
                    "applicant": doc.applicant,
                    "loan_product": doc.loan_product,
                    "name": ["!=", doc.name],
                    "workflow_state": ["not in", ["Cancelled", "Rejected", "Rejected By HR", "Rejected By BU Head"]],
                },
                fields=["name"],
            )
            if len(employee_total_loan_applications) >= loan_product.custom_loan_avail_criteria:
                frappe.throw("You have already availed the maximum number of loans available for this product.")
        if loan_product.custom_maximum_lioan_applications_approved_within_month:
            total_loan_applications = frappe.get_all(
                "Loan Application",
                filters={
                    "loan_product": doc.loan_product,
                    "workflow_state": ["in", ["Approved", "Approved By HR", "Approved By BU Head"]],
                    "name": ["!=", doc.name],
                    "creation": [
                        "between",
                        [
                            frappe.utils.get_first_day(frappe.utils.nowdate()),
                            frappe.utils.nowdate(),
                        ],
                    ],
                },
                fields=["name"],
            )
            if len(total_loan_applications) >= loan_product.custom_maximum_lioan_applications_approved_within_month and doc.workflow_state == "Approved":
                frappe.throw(
                    "Maximum number of loan applications approved for this product within the month has been reached."
                )

def on_cancel(doc, method):
    # Check if the loan application is cancelled
    if doc.get("workflow_state"):
        doc.db_set("workflow_state", "Cancelled")


# ! OVERRIDDEN FUNCTION: GET_ACCRUED_INTEREST_ENTRIES
# ! LOCATION: OVERRIDDEN IN __INIT__.PY
def custom_get_accrued_interest_entries(against_loan, posting_date=None):
    if not posting_date:
        posting_date = getdate()

    # * GET DECIMAL PRECISION FOR FINANCIAL FIELDS
    precision = cint(frappe.db.get_default("currency_precision")) or 2

    # ? MODIFIED TO GET ONLY SINGLE (LATEST) UNPAID ENTRY
    unpaid_accrued_entries = frappe.db.sql(
        """
        SELECT
            name,
            due_date,
            interest_amount AS interest_amount,
            payable_principal_amount AS payable_principal_amount,
            accrual_type
        FROM
            `tabLoan Interest Accrual`
        WHERE
            loan = %s
            AND due_date <= %s
            AND (
                interest_amount > 0
                OR payable_principal_amount > 0
            )
            AND docstatus = 1
        ORDER BY
            due_date DESC
        LIMIT 1;
        """,
        (against_loan, posting_date),
        as_dict=1,
    )

    # ! FILTER ENTRIES: SKIP RECORDS WITH ZERO PAYABLES
    unpaid_accrued_entries = [
        d for d in unpaid_accrued_entries
        if flt(d.interest_amount, precision) > 0 or flt(d.payable_principal_amount, precision) > 0
    ]

    return unpaid_accrued_entries

# ! OVERRIDDEN FUNCTION: PROCESS_LOAN_INTEREST_ACCRUALS
# ! LOCATION: OVERRIDDEN IN __INIT__.PY
# ? ORIGINAL LOCATION: SALARY_SLIP_LOAN_UTILS.PY
@if_lending_app_installed
def custom_process_loan_interest_accruals(doc: "SalarySlip", is_proccessed=False):
    from lending.loan_management.doctype.process_loan_interest_accrual.process_loan_interest_accrual import (
        process_loan_interest_accrual_for_term_loans,
    )

    loans = _get_loan_details(doc)
    if not loans:
        return
    for loan in loans:
        # ? PROCESS ONLY TERM LOANS WITH VALID END DATE
        if loan.get("is_term_loan") and doc.end_date and is_proccessed:
            process_loan_interest_accrual_for_term_loans(
                posting_date=doc.end_date,
                loan_product=loan.loan_product,
                loan=loan.name
            )

# ! OVERRIDDEN FUNCTION: MAKE_ACCRUAL_INTEREST_ENTRY_FOR_TERM_LOANS
# ! LOCATION: OVERRIDDEN IN __INIT__.PY
# ? ORIGINAL LOCATION: loan_interest_accrual.py
def custom_make_accrual_interest_entry_for_term_loans(posting_date, process_loan_interest, term_loan=None, loan_product=None, accrual_type="Regular"):
	from lending.loan_management.doctype.loan_interest_accrual.loan_interest_accrual import (
		make_loan_interest_accrual_entry,
		get_term_loans
	)


	curr_date = posting_date or add_days(nowdate(), 1)
	term_loans = get_term_loans(curr_date, term_loan, loan_product)

	accrued_entries = []

	for loan in term_loans:
		# ? Only accrue if due in same month as posting date
		if getdate(loan.payment_date).month == getdate(posting_date).month:
			accrued_entries.append(loan.payment_entry)

			args = frappe._dict({
				"loan": loan.name,
				"applicant_type": loan.applicant_type,
				"applicant": loan.applicant,
				"interest_income_account": loan.interest_income_account,
				"loan_account": loan.loan_account,
				"interest_amount": loan.interest_amount,
				"payable_principal": loan.principal_amount,
				"process_loan_interest": process_loan_interest,
				"repayment_schedule_name": loan.payment_entry,
				"posting_date": posting_date,
				"accrual_type": accrual_type,
				"due_date": loan.payment_date,
			})

			make_loan_interest_accrual_entry(args)

	# ? Update Repayment Schedule to mark accrual status
	if accrued_entries:
		frappe.db.sql(
			"""
			UPDATE `tabRepayment Schedule`
			SET is_accrued = 1 
			WHERE name IN (%s)
			""" % ", ".join(["%s"] * len(accrued_entries)),
			tuple(accrued_entries),
		)

from prompt_hr.py.utils import get_applicable_print_format,send_notification_email, get_prompt_company_name


@frappe.whitelist()
def trigger_loan_notification(name, to=None, cc=None):
    """Send appointment letter email with TO & CC support"""

    to = frappe.parse_json(to) if to else []
    cc = frappe.parse_json(cc) if cc else []

    doc = frappe.get_doc("Loan", name)
    employee = frappe.get_doc("Employee", doc.applicant)

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
        notification_name="Loan Agreement",
        send_attach=True,
        print_format=print_format
    )

    return "Loan Agreement Sent Successfully"


@frappe.whitelist()
def create_loan_agreement_letter_approval(employee_id, letter=None, released_by_emp_code_and_name=None,
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
        print("file_doc", file_doc)
        if file_doc:
            try:
                doc.db_set("attachment", file_doc.file_url)
            except Exception:
                pass

    except Exception:
        print("error")
        # fallback to simple html rendering if print format fails
        try:
            html = frappe.render_template("prompt_hr/templates/includes/loan_agreement.html", {"employee": emp, "letter": letter})
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
