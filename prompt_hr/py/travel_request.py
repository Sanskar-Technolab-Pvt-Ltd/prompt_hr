import frappe
from prompt_hr.py.utils import expense_claim_and_travel_request_workflow_email


def on_update(doc, method):
    # ? SEND EMAIL NOTIFICATION FOR EXPENSE CLAIM WORKFLOW
    expense_claim_and_travel_request_workflow_email(doc)

def before_save(doc, method):

    attachment_validation(doc)

def attachment_validation(doc):
    grade = frappe.db.get_value("Employee", doc.get("employee"), "grade")

    mandatory_attachment_travel_modes = frappe.db.get_all(
    "Travel Mode Table", {"grade": grade, "attachment_mandatory": True}, "mode_of_travel",
    pluck="mode_of_travel" 
    )

    for row in doc.get("itinerary"):
        print("Hii\n",row.get("custom_attachment"),mandatory_attachment_travel_modes)
        if row.get("custom_travel_mode") in mandatory_attachment_travel_modes and not row.get("custom_attachment"):
            frappe.throw(f"Attachment is Mandatory for Row: {row.get('idx')} in Travel Itinerary Table.")


# ! prompt_hr.py.travel_request.get_eligible_travel_modes
# ? FUNCTION TO GET ELEGIBLE TRAVEL MODE WITH RESEPECT TO EMPLOYEE AND COMPANY
@frappe.whitelist()
def get_eligible_travel_modes(employee, company):
    travel_budget = frappe.db.get_value("Travel Budget", {"company": company}, "name")
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
        pluck="mode_of_travel",
    )
    return travel_modes if travel_modes else None
