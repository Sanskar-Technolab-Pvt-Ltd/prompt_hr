import frappe
from prompt_hr.py.utils import expense_claim_and_travel_request_workflow_email

def on_update(doc, method):
    # ? SEND EMAIL NOTIFICATION FOR EXPENSE CLAIM WORKFLOW
    expense_claim_and_travel_request_workflow_email(doc)

@frappe.whitelist()
def get_eligible_travel_modes(employee,company):
    travel_budget = frappe.db.get_value(
        "Travel Budget",
        {"company": company},
        "name"
    )
    if not travel_budget:
        return None
    
    grade = frappe.db.get_value("Employee", employee, "grade")
    if not grade:
        return None

    travel_modes = frappe.get_all(
        "Travel Mode Table",
        filters={
            "parent": travel_budget,
            "grade": grade,
        },
        fields=["mode_of_travel"],
        pluck = "mode_of_travel"
    ) 
    return travel_modes if travel_modes else None