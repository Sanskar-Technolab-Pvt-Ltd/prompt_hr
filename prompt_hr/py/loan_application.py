import frappe

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
                    "docstatus": ["<", 2],
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
                    "status": "Approved",
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
            if len(total_loan_applications) >= loan_product.custom_maximum_lioan_applications_approved_within_month:
                frappe.throw(
                    "Maximum number of loan applications approved for this product within the month has been reached."
                )

def on_cancel(doc, method):
    # Check if the loan application is cancelled
    if doc.get("workflow_state"):
        doc.db_set("workflow_state", "Cancelled")