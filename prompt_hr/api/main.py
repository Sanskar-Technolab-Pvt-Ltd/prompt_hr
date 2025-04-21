import frappe

@frappe.whitelist()
def trigger_appointment_notification(name):
    doc = frappe.get_doc("Appointment Letter", name)
    notification_list = frappe.get_all("Notification", filters={
        "document_type": "Appointment Letter",
        "enabled": 1,
        "method": "send_appointment_letter"
    })
    if notification_list:
        notification = frappe.get_doc("Notification", notification_list[0].name)
    else:
        frappe.throw("No Notification found for Appointment Letter")
    if doc.company == "Prompt":
        frappe.db.set_value("Notification", notification.name, "print_format", "Appointment letter - Prompt")
    elif doc.company == "IndiFOSS":
        frappe.db.set_value("Notification", notification.name, "print_format", "Appointment letter - Indifoss")
    frappe.db.commit()
    doc.run_method("send_appointment_letter")

    return "Appointment Letter sent Successfully"
