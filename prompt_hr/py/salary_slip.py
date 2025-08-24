import frappe
from frappe import _
from frappe.utils import getdate, add_months,cint
from hrms.payroll.doctype.salary_slip.salary_slip_loan_utils import process_loan_interest_accruals,_get_loan_details, set_loan_repayment

def before_validate(doc, method=None):
    if not doc.is_new():
        # Fetch original doc to compare dates
        old_doc = frappe.get_doc(doc.doctype, doc.name)
        if getdate(old_doc.end_date) != getdate(doc.end_date):
            delete_loan_interest_accruals(old_doc)
            process_loan_interest_accruals(doc, True)
            doc.set("loans", [])
            set_loan_repayment(doc)

    elif doc.is_new():
        # Only run on creation
        process_loan_interest_accruals(doc, True)
        doc.set("loans", [])
        set_loan_repayment(doc)

    
def update_loan_principal_amount(salary_slip_doc, method):
    """
    Updates the principal amount in the Loans Component of the Salary Slip.
    
    Args:
        salary_slip_doc: The Salary Slip document
        method: The hook method being called
    """
    # * Early return if no loans exist in salary slip
    if not salary_slip_doc.loans:
        return

    # TODO: Consider batch updating for better performance
    for loan_component in salary_slip_doc.loans:
        # ! Only update if principal amount differs from total payment
        if loan_component.principal_amount != loan_component.total_payment:
            salary_slip_loan_document = frappe.get_doc("Salary Slip Loan", loan_component.name)
            
            if salary_slip_loan_document:
                # * Sync principal amount with total payment
                loan_component.principal_amount = loan_component.total_payment
                salary_slip_loan_document.db_set("principal_amount", loan_component.total_payment)


def loan_repayment_amount(salary_slip_doc, method):
    """
    Updates the total_payment in Repayment Schedule for active loans
    within the salary slip period.
    
    Args:
        salary_slip_doc: The Salary Slip document
        method: The hook method being called
    """
    if salary_slip_doc.custom_is_salary_slip_released:
        if salary_slip_doc.employee:
            #! FETCH USER ID OF EMPLOYEE
            user_id = frappe.db.get_value("Employee", salary_slip_doc.employee, "user_id")
            if user_id:
                #! SHARE DOCUMENT WITH READ ONLY PERMISSION
                frappe.share.add(
                    doctype=salary_slip_doc.doctype,
                    name=salary_slip_doc.name,
                    user=user_id,
                    read=1,
                )

    # * Early return if no loans exist in salary slip
    if not salary_slip_doc.loans:
        return

    # * Fetch all loan components from the salary slip
    salary_slip_loan_components = frappe.get_all(
        "Salary Slip Loan",
        filters={"parent": salary_slip_doc.name},
        fields=["loan", "total_payment"]
    )

    # * Process each loan component
    for loan_component in salary_slip_loan_components:
        loan_document = frappe.get_doc("Loan", loan_component.get("loan"))

        # * Fetch Active Repayment Schedules for the current loan
        active_repayment_schedules = frappe.get_all(
            "Loan Repayment Schedule",
            filters={
                "loan": loan_component["loan"],
                "status": "Active",
                "docstatus": 1
            },
            fields=["name"]
        )

        # * Process each active repayment schedule
        for repayment_schedule in active_repayment_schedules:
            # * Fetch all repayment entries for the current schedule
            repayment_entries = frappe.get_all(
                "Repayment Schedule",
                filters={"parent": repayment_schedule["name"], "docstatus": 1},
                fields=["name", "payment_date", "total_payment", "balance_loan_amount"],
                order_by="payment_date asc"
            )

            # * Initialize tracking variables for schedule updates
            is_schedule_updated = 0  # Flag to track if schedule has been updated
            latest_payment_date = max([getdate(entry["payment_date"]) for entry in repayment_entries], default=None)
            is_installment_adjusted = 0  # Flag to track installment adjustment
            max_entry_index = len(repayment_entries)
            remaining_adjustment_amount = 0  # Amount difference to be adjusted in installments
            previous_outstanding_balance = 0  # Running balance for subsequent entries
            adjusted_installment_amount = 0  # New principal amount for adjusted installments

            # * Process each repayment entry in the schedule
            for repayment_entry in repayment_entries:
                entry_payment_date = getdate(repayment_entry["payment_date"])

                # ? Check if payment date falls within salary slip period and not yet updated
                if (getdate(salary_slip_doc.start_date) <= entry_payment_date <= getdate(salary_slip_doc.end_date)
                    and is_schedule_updated == 0):

                    # ! Update entry if payment amounts differ
                    if repayment_entry["total_payment"] != loan_component["total_payment"]:
                        # * Calculate the remaining amount to be adjusted
                        remaining_adjustment_amount = repayment_entry["total_payment"] - loan_component["total_payment"]

                        # * Update the current repayment entry
                        frappe.db.set_value(
                            "Repayment Schedule",
                            repayment_entry["name"],
                            {
                                "total_payment": loan_component["total_payment"],
                                "principal_amount": loan_component["total_payment"],
                                "balance_loan_amount": repayment_entry["balance_loan_amount"] + remaining_adjustment_amount
                            },
                        )

                        is_schedule_updated = 1
                        previous_outstanding_balance = repayment_entry["balance_loan_amount"] + remaining_adjustment_amount

                # * Handle remaining amount adjustment for subsequent entries
                elif is_schedule_updated == 1:
                    loan_product_doc = frappe.get_doc("Loan Product", loan_document.loan_product)
                    if loan_product_doc:
                        # * Handle "Adjust Number of Installments" option
                        if loan_product_doc.custom_remaining_installment_adjustment_type == "Adjust Number of Installments":
                            # ? Create new installment for the first adjustment
                            if is_installment_adjusted == 0:
                                is_installment_adjusted = 1

                                # * Create new repayment schedule entry
                                new_repayment_schedule = frappe.new_doc("Repayment Schedule")
                                new_repayment_schedule.parent = repayment_schedule["name"]
                                new_repayment_schedule.parentfield = "repayment_schedule"
                                new_repayment_schedule.parenttype = "Loan Repayment Schedule"
                                new_repayment_schedule.idx = max_entry_index + 1
                                new_repayment_schedule.payment_date = add_months(latest_payment_date, 1)
                                new_repayment_schedule.principal_amount = remaining_adjustment_amount
                                new_repayment_schedule.total_payment = remaining_adjustment_amount
                                new_repayment_schedule.balance_loan_amount = 0
                                new_repayment_schedule.insert(ignore_permissions=True)
                                new_repayment_schedule.submit()

                            # * Update balance amounts for subsequent entries
                            frappe.db.set_value(
                                "Repayment Schedule",
                                repayment_entry["name"],
                                "balance_loan_amount",
                                repayment_entry["balance_loan_amount"] + remaining_adjustment_amount
                            )

                        # * Handle "Adjust Installment Amount" option
                        elif loan_product_doc.custom_remaining_installment_adjustment_type == "Adjust Installment Amount":
                            if previous_outstanding_balance:
                                # * Calculate new principal amount for remaining entries
                                if not adjusted_installment_amount:
                                    remaining_entries_count = len(repayment_entries) - repayment_entries.index(repayment_entry)
                                    adjusted_installment_amount = previous_outstanding_balance / remaining_entries_count

                                # * Update current entry with adjusted amounts
                                frappe.db.set_value(
                                    "Repayment Schedule",
                                    repayment_entry["name"],
                                    "principal_amount",
                                    adjusted_installment_amount
                                )
                                frappe.db.set_value(
                                    "Repayment Schedule",
                                    repayment_entry["name"],
                                    "total_payment",
                                    adjusted_installment_amount
                                )
                                frappe.db.set_value(
                                    "Repayment Schedule",
                                    repayment_entry["name"],
                                    "balance_loan_amount",
                                    previous_outstanding_balance - adjusted_installment_amount
                                )

                                # * Update running balance for next iteration
                                previous_outstanding_balance = previous_outstanding_balance - adjusted_installment_amount

    # * Commit all database changes
    frappe.db.commit()

@frappe.whitelist()
def cancel_loan_repayment_amount(salary_slip_doc, method):
    """
    CANCELS LOAN REPAYMENTS BY REVERSING SALARY SLIP ENTRIES AND UPDATING REPAYMENT SCHEDULES!
    """

    # ? EARLY RETURN IF NO LOANS EXIST IN SALARY SLIP
    if not salary_slip_doc.loans:
        return

    # ? FETCH LOAN COMPONENTS FROM SALARY SLIP
    salary_slip_loan_components = frappe.get_all(
        "Salary Slip Loan",
        filters={"parent": salary_slip_doc.name},
        fields=["loan", "total_payment"]
    )

    # ? ITERATE THROUGH EACH LOAN COMPONENT
    for loan_component in salary_slip_loan_components:
        loan_document = frappe.get_doc("Loan", loan_component.get("loan"))

        # ? FETCH ACTIVE REPAYMENT SCHEDULES FOR CURRENT LOAN
        active_repayment_schedules = frappe.get_all(
            "Loan Repayment Schedule",
            filters={
                "loan": loan_component["loan"],
                "status": "Active",
                "docstatus": 1
            },
            fields=["name", "monthly_repayment_amount", "repayment_periods", "repayment_start_date"]
        )
        loan_product_doc = frappe.get_doc("Loan Product", loan_document.loan_product)

        # ? PROCESS EACH REPAYMENT SCHEDULE
        for repayment_schedule in active_repayment_schedules:
            repayment_entries = frappe.get_all(
                "Repayment Schedule",
                filters={"parent": repayment_schedule["name"], "docstatus": 1},
                fields=["name", "payment_date", "total_payment", "balance_loan_amount"],
                order_by="payment_date asc"
            )

            is_schedule_updated = 0
            is_installment_adjusted = 0
            max_entry_index = len(repayment_entries)

            repayment_start_date = getdate(repayment_schedule.repayment_start_date)
            repayment_periods = cint(repayment_schedule.repayment_periods)
            latest_payment_date = add_months(repayment_start_date, repayment_periods)
            payment_date_of_changed_element = None
            remaining_adjustment_amount = 0
            previous_outstanding_balance = 0
            adjusted_installment_amount = 0
            amount_before_delete = 0
            remaining_loan_amount = loan_document.get("loan_amount") - loan_document.get("total_principal_paid")
            # ? ITERATE OVER EACH REPAYMENT ENTRY
            for i, repayment_entry in enumerate(repayment_entries):
                entry_payment_date = getdate(repayment_entry["payment_date"])

                # ? IF ENTRY DATE IS WITHIN SALARY SLIP RANGE AND NOT UPDATED YET
                if (
                    getdate(salary_slip_doc.start_date) <= entry_payment_date <= getdate(salary_slip_doc.end_date)
                    and is_schedule_updated == 0
                ):
                    # ! IF PAYMENT AMOUNTS DIFFER, APPLY ADJUSTMENT
                    if (
                        repayment_schedule.get("monthly_repayment_amount")
                        and repayment_schedule.get("monthly_repayment_amount") != loan_component["total_payment"]
                    ):
                        remaining_adjustment_amount = (
                            repayment_schedule.get("monthly_repayment_amount") - loan_component["total_payment"]
                        )

                        # ? STORE AMOUNT BEFORE CHANGING TO ORIGINAL

                        amount_before_delete = loan_component["total_payment"]


                        # ? UPDATE CURRENT ENTRY WITH ORIGINAL AMOUNT
                        if loan_product_doc.custom_remaining_installment_adjustment_type == "Adjust Number of Installments":
                            frappe.db.set_value(
                                "Repayment Schedule",
                                repayment_entry["name"],
                                {
                                    "total_payment": repayment_schedule.get("monthly_repayment_amount"),
                                    "principal_amount": repayment_schedule.get("monthly_repayment_amount"),
                                    "balance_loan_amount": repayment_entry["balance_loan_amount"] - remaining_adjustment_amount,
                                    "is_accrued": 0
                                },
                            )
                            previous_outstanding_balance = repayment_entry["balance_loan_amount"] - remaining_adjustment_amount
                        elif loan_product_doc.custom_remaining_installment_adjustment_type == "Adjust Installment Amount":
                            frappe.db.set_value(
                                "Repayment Schedule",
                                repayment_entry["name"],
                                {
                                    "total_payment": repayment_schedule.get("monthly_repayment_amount"),
                                    "principal_amount": repayment_schedule.get("monthly_repayment_amount"),
                                    "balance_loan_amount": repayment_entry["balance_loan_amount"] - remaining_adjustment_amount,
                                    "is_accrued": 0
                                },
                            )
                            previous_outstanding_balance = repayment_entry["balance_loan_amount"] - remaining_adjustment_amount

                        is_schedule_updated = 1

                # ? HANDLE ADJUSTMENTS FOR FOLLOWING ENTRIES
                elif is_schedule_updated == 1:
                    if loan_product_doc:

                        # ? CASE 1: ADJUST NUMBER OF INSTALLMENTS
                        if loan_product_doc.custom_remaining_installment_adjustment_type == "Adjust Number of Installments":
                            if is_installment_adjusted == 0:
                                is_installment_adjusted = 1
                                repayment_entry_to_delete = frappe.get_all(
                                    "Repayment Schedule",
                                    filters={
                                        "parent": repayment_schedule["name"],
                                        "payment_date": [">=", latest_payment_date],
                                        "total_payment": repayment_schedule.get("monthly_repayment_amount") - amount_before_delete,
                                        "principal_amount": repayment_schedule.get("monthly_repayment_amount") - amount_before_delete,
                                        "balance_loan_amount": [">=",0],
                                        "docstatus": 1
                                    },
                                    fields=["name", "payment_date"]
                                )

                                if repayment_entry_to_delete:
                                    payment_date_of_changed_element = repayment_entry_to_delete[0].get("payment_date")
                                    doc = frappe.get_doc("Repayment Schedule", repayment_entry_to_delete[0]["name"])
                                    doc.cancel()
                                    doc.delete()

                            # ? SET REPAYMENT DATES OF ELEMENT AFTER THE DELETED ELEMENT
                            if payment_date_of_changed_element and repayment_entry.get("payment_date") > payment_date_of_changed_element:
                                old_payment_date = frappe.db.get_value("Repayment Schedule", repayment_entry.get("name"), "payment_date")
                                old_idx = frappe.db.get_value("Repayment Schedule", repayment_entry.get("name"), "idx")
                                frappe.db.set_value(
                                    "Repayment Schedule",
                                    repayment_entry["name"],
                                    "payment_date",
                                    add_months(old_payment_date, -1)
                                )
                                frappe.db.set_value(
                                    "Repayment Schedule",
                                    repayment_entry["name"],
                                    "idx",
                                    old_idx-1
                                )
                            else:
                                frappe.db.set_value(
                                    "Repayment Schedule",
                                    repayment_entry["name"],
                                    "balance_loan_amount",
                                    repayment_entry["balance_loan_amount"] - remaining_adjustment_amount
                                )

                        # ? CASE 2: ADJUST INSTALLMENT AMOUNT
                        elif loan_product_doc.custom_remaining_installment_adjustment_type == "Adjust Installment Amount":
                            if previous_outstanding_balance:
                                if not adjusted_installment_amount:
                                    remaining_entries_count = len(repayment_entries) - repayment_entries.index(repayment_entry)
                                    adjusted_installment_amount = previous_outstanding_balance / remaining_entries_count

                                frappe.db.set_value(
                                    "Repayment Schedule",
                                    repayment_entry["name"],
                                    "principal_amount",
                                    adjusted_installment_amount
                                )
                                frappe.db.set_value(
                                    "Repayment Schedule",
                                    repayment_entry["name"],
                                    "total_payment",
                                    adjusted_installment_amount
                                )
                                frappe.db.set_value(
                                    "Repayment Schedule",
                                    repayment_entry["name"],
                                    "balance_loan_amount",
                                    previous_outstanding_balance - adjusted_installment_amount
                                )

                                previous_outstanding_balance = previous_outstanding_balance - adjusted_installment_amount


    # ? COMMIT DATABASE CHANGES
    frappe.db.commit()

    # ? CANCEL ACCRUED INTEREST ENTRIES
    delete_loan_interest_accruals(salary_slip_doc)

@frappe.whitelist()
def send_salary_slip(salary_slip_id, from_date, to_date, company):
    try:
        account_user_users = frappe.db.get_all("Has Role", {"role": "Accounts User", "parenttype": "User", "parent": ["not in", ["Administrator"]]}, ["parent"])
        if account_user_users:                                                
            account_user_emails = [user.get("parent") for user in account_user_users]
            payroll_entry_link = frappe.utils.get_url_to_form("Salary Slip", salary_slip_id)

            salary_report_link = frappe.utils.get_url(f"/app/query-report/Salary%20Register?from_date={from_date}&to_date={to_date}&currency=INR&company={company.replace(' ', '+')}&docstatus=Submitted")            
            
            frappe.sendmail(
                recipients=account_user_emails,
                subject="Salary Slip Notification",
                message=f"""A new Salary Slip has been created. You can view it here: {payroll_entry_link}<br><br>View the Salary Register report with applied filters here: {salary_report_link}"""                
            )
            
            frappe.db.set_value("Salary Slip", salary_slip_id, "custom_account_user_informed", 1)            
    except Exception as e:
        frappe.db.set_value("Salary Slip", salary_slip_id, "custom_account_user_informed", 0)
        frappe.log_error("Error while sending Payroll Entry notification", frappe.get_traceback())
        frappe.throw(_("Error while sending Payroll Entry notification: {0}").format(str(e)))


from frappe.utils import getdate

def delete_loan_interest_accruals(doc):
    """
    CANCELS LINKED PROCESS LOAN INTEREST ACCRUALS AND THEIR DEPENDENCIES!
    """

    loans = _get_loan_details(doc)
    if not loans:
        return

    for loan in loans:
        if loan.get("is_term_loan"):
            accrual_doc = frappe.get_all(
                "Process Loan Interest Accrual",
                filters={
                    "loan": loan.name,
                    "loan_product": loan.loan_product,
                    "posting_date": getdate(doc.end_date),
                    "process_type": "Term Loans",
                    "docstatus": 1
                },
                fields=["name"]
            )
            if accrual_doc:
                try:
                    doc_to_delete = frappe.get_doc("Process Loan Interest Accrual", accrual_doc[0]["name"])
                    doc_to_delete.flags.ignore_permissions = True

                    # ? CANCEL AND DELETE LINKED INTEREST ACCRUALS FIRST
                    linked_docs = frappe.get_all(
                        "Loan Interest Accrual",
                        filters={"process_loan_interest_accrual": doc_to_delete.name, "docstatus": 1},
                        fields=["name"]
                    )
                    for linked in linked_docs:
                        linked_doc = frappe.get_doc("Loan Interest Accrual", linked.name)
                        linked_doc.flags.ignore_permissions = True
                        linked_doc.cancel()

                    # ? NOW CANCEL AND DELETE MAIN PROCESS LOAN INTEREST ACCRUAL
                    doc_to_delete.cancel()

                except Exception as e:
                    frappe.log_error(
                        title="LOAN ACCRUAL DELETION ERROR",
                        message=f"ERROR DELETING PROCESS LOAN INTEREST ACCRUAL FOR LOAN {loan.name}:\n{frappe.get_traceback()}"
                    )

def salary_slip_view_and_access_permissions(user):
    """
    RETURNS CONDITIONS TO CONTROL VIEW/ACCESS FOR SALARY SLIPS.

    - HR / Accounts roles can view all Salary Slips without restrictions.
    - Employees can only view their own Salary Slips when:
        1. The Salary Slip is submitted (docstatus = 1), AND
        2. The Salary Slip is marked as released (custom_is_salary_slip_released = 1).
    """

    #! USE SESSION USER IF USER NOT PROVIDED
    if not user:
        user = frappe.session.user

    #? FETCH ALL ROLES FOR THE GIVEN USER
    roles = frappe.get_roles(user)

    #? HR & ACCOUNTS ROLES HAVE FULL ACCESS TO SALARY SLIPS
    if any(role in roles for role in ["S - HR Director (Global Admin)", "S - Accounts User", "S - Accounts Manager", "System Manager"]):
        return

    #? EMPLOYEES CAN ONLY VIEW SALARY SLIPS THAT ARE SUBMITTED AND RELEASED
    return """(`tabSalary Slip`.`docstatus` = 1 AND `tabSalary Slip`.`custom_is_salary_slip_released` = 1)"""
