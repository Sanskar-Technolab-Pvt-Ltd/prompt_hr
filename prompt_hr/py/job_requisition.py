import frappe

@frappe.whitelist()
def on_update(doc, method):
    if doc.custom_target_hiring_duration:
        if doc.custom_target_hiring_duration == "Custom Date":
            doc.custom_target_hiring_date = doc.expected_by if doc.expected_by else frappe.utils.nowdate()
        else:
            days = int(doc.custom_target_hiring_duration.split()[0]) if doc.custom_target_hiring_duration else 0
            doc.custom_target_hiring_date = frappe.utils.add_days(doc.posting_date, days)

