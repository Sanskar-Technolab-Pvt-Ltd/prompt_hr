import frappe

@frappe.whitelist()
def send_esic_challan_notification(report_name, url):
    """Send ESIC Challan notification to users with 'Accounts User' or 'Accounts Manager' roles."""

    # ? Step 1: Get all users with the relevant roles
    users_with_roles = frappe.get_all(
        "Has Role",
        filters={
            "role": ["in", ["Accounts User", "Accounts Manager"]],
            "parenttype": "User"
        },
        fields=["parent as user"],
        distinct=True
    )

    if not users_with_roles:
        frappe.throw("No users found with 'Accounts User' or 'Accounts Manager' roles.")

    # ? Step 2: Filter users who are enabled and system users
    user_emails = frappe.get_all(
        "User",
        filters={
            "name": ["in", [u["user"] for u in users_with_roles]],
            "enabled": 1,
            "user_type": "System User"
        },
        fields=["email"]
    )

    # ? Step 3: Extract email addresses
    emails = [u["email"] for u in user_emails if u.get("email")]

    if not emails:
        frappe.throw("No eligible recipients found with valid email addresses.")

    # ? Step 4: Prepare report info and fetch notification template
    base_url = frappe.utils.get_url()
    if url:
        report_url = url
    elif report_name == "ESIC Challan":
        report_url = f"{base_url}/app/query-report/ESIC_Challan"
    elif report_name == "PF ECR Challan Excel":
        report_url = f"{base_url}/app/query-report/PF ECR Challan Excel"
    else:
        report_url = f"{base_url}/app/query-report/{report_name}"

    # ? Step 5: Get Notification Doc
    notification = frappe.get_doc("Notification", "PF-ECR and ESIC Challan Notification")
    if not notification:
        frappe.throw("Notification 'PF/ESIC Challan Notification' not found.")

    # ? Step 6: Render subject and message with context
    subject = frappe.render_template(notification.subject or "", {"report_name": report_name})
    message = frappe.render_template(notification.message or "", {
        "report_name": report_name,
        "report_url": report_url
    })

    # ? Step 7: Send the email
    frappe.sendmail(
        recipients=emails,
        subject=subject,
        message=message,
    )

    return "success"
