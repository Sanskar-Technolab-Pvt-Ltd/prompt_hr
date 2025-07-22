import frappe
from lending.loan_management.doctype.loan_interest_accrual.loan_interest_accrual import (
	make_accrual_interest_entry_for_demand_loans,
)
from lending.loan_management.doctype.process_loan_interest_accrual.process_loan_interest_accrual import ProcessLoanInterestAccrual
from prompt_hr.py.loan_application import custom_make_accrual_interest_entry_for_term_loans


class CustomProcessLoanInterestAccrual(ProcessLoanInterestAccrual):
    def on_submit(self):
        open_loans = []
        if self.loan:
            loan_doc = frappe.get_doc("Loan", self.loan)
            if loan_doc:
                open_loans.append(loan_doc)

        if (not self.loan or not loan_doc.is_term_loan) and self.process_type != "Term Loans":
            make_accrual_interest_entry_for_demand_loans(
                self.posting_date,
                self.name,
                open_loans=open_loans,
                loan_product=self.loan_product,
                accrual_type=self.accrual_type,
            )

        if (not self.loan or loan_doc.is_term_loan) and self.process_type != "Demand Loans":
            custom_make_accrual_interest_entry_for_term_loans(
                self.posting_date,
                self.name,
                term_loan=self.loan,
                loan_product=self.loan_product,
                accrual_type=self.accrual_type,
            )
