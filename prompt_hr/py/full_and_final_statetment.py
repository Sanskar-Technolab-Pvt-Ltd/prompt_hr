import frappe

@frappe.whitelist()
def on_update(doc, method):
    # Ensure both fields are numbers (0 if None or not set)
    unserved_days = doc.custom_unserved_notice_days or 0
    monthly_salary = doc.custom_monthly_salary or 0

    amount = unserved_days * monthly_salary / 26

    for row in doc.payables:
        if row.component == "Notice Period Recovery":
            row.amount = amount  # Update the amount for the "Notice Period Recovery" row
            break
