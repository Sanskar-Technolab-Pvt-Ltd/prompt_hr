import frappe
from hrms.hr.doctype.full_and_final_statement.full_and_final_statement import FullandFinalStatement

class CustomFullAndFinalStatement(FullandFinalStatement):
    @frappe.whitelist()
    def get_payable_component(doc):
            """
            Get the list of components to be added to the payables table
            """
            components = super().get_payable_component()
            components.insert(0, "Notice Period Recovery")

            if "Bonus" in components:
                components.remove("Bonus")

            if "Gratuity" in components:
                components.remove("Gratuity")
            
            return components
    

    @frappe.whitelist()
    def create_component_row(doc, components, component_type):
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
                                else (doc.custom_unserved_notice_days * doc.custom_monthly_salary) / 26
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
                                "amount": expense_claim.total_claimed_amount,
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
                                "amount": leave_encashment_doc.encashment_amount,
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
                                "amount": employee_advance_doc.advance_amount,
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
                                "amount": loan_doc.total_payment - loan_doc.total_amount_paid,
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
                                            "amount": detail.imprest_amount,
                                        },
                                    )

            else:
                super().create_component_row([component], component_type)

    @frappe.whitelist()
    def get_receivable_component(doc):
        """
        Modify function to add Imprest Account to the receivables table
        """
        receivables = super().get_receivable_component()
        company_abbr = frappe.get_doc("Company", doc.company).abbr
        if company_abbr == frappe.db.get_single_value("HR Settings", "custom_indifoss_abbr"):
            receivables.append("Imprest Amount")
        return receivables
