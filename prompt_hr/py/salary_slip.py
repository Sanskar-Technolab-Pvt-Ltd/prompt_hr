import frappe
from frappe.utils import getdate, add_months

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
                                "balance_loan_amount": loan_document.get(
                                    "total_payment"
                                )
                                - loan_document.get("total_amount_paid")
                            },
                        )

                        is_schedule_updated = 1
                        previous_outstanding_balance = loan_document.get(
                            "total_payment"
                        ) - loan_document.get("total_amount_paid")

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
                            elif is_installment_adjusted == 1:
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
