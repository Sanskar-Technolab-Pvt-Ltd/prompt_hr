import frappe
import firebase_admin
from firebase_admin import credentials, messaging


@frappe.whitelist()
def register_device_token(token=None):
    """Save FCM token for current logged-in user"""
    try:
        if not token:
            return
        
        user = frappe.session.user
        
        # Check if any token exists for this user
        existing = frappe.get_all(
            "Notification Token",
            filters={"user": user},
            fields=["name", "fcm_token"],
            limit=1
        )
        
        if existing:
            doc = frappe.get_doc("Notification Token", existing[0].name)
            if doc.fcm_token != token:
                old_token = doc.fcm_token
                doc.fcm_token = token
                doc.save(ignore_permissions=True)
                frappe.db.commit()
                
        else:
            doc = frappe.get_doc({
                "doctype": "Notification Token",
                "user": user,
                "fcm_token": token,
            })
            doc.insert(ignore_permissions=True)
            frappe.db.commit()
            
        frappe.log_error("register_device_token",f"[DEBUG] Token saved for {user} : token={token}")
        return {"status": "ok"}
    except Exception as e:
        frappe.log_error("Error in register_device_token", frappe.traceback())
        return str(e)


firebase_app = None
def get_firebase_app():
    """Initialize Firebase once and reuse"""
    global firebase_app
    if not firebase_app:
        cred = credentials.Certificate(frappe.get_site_path('private/files', 'firebase.json'))
        firebase_app = firebase_admin.initialize_app(cred)
    return firebase_app


def send_push_notification(token, title, body, data=None):
    """Send notification to a single device"""
    get_firebase_app()
    frappe.log_error("send_push_notification",f"[DEBUG] Sending notification via Firebase app: {firebase_app.name}")
    message = messaging.Message(
        notification=messaging.Notification(title=title, body=body),
        data=data or {},
        token=token,
    )
    response = messaging.send(message)
    frappe.log_error("send_push_notification",f"[DEBUG] Firebase response: {response}")
    return response


def push_notification_handler(doc, method):
    """Send Firebase push when Notification Log is created"""
    tokens = frappe.get_all("Notification Token", filters={"user": doc.for_user}, pluck="fcm_token")
    frappe.log_error("push_notification_handler",f"[DEBUG] Found {len(tokens)} tokens for user {doc.for_user}: {tokens}")
    if not tokens:
        return

    for token in tokens:
        try:
            send_push_notification(
                token,
                title=doc.subject or "ERPNext Notification",
                body=doc.email_content or "",
                data={"doctype": doc.document_type, "docname": doc.document_name}
            )
        except Exception as e:
            frappe.log_error("Firebase Push",f"Push notification error: {str(e)}",)




def clear_token_for_user():
    """Clear all FCM tokens for a user (e.g. on logout)"""
    try:
        user = frappe.session.user
        frappe.db.delete("Notification Token", {"user": user})
        frappe.db.commit()
    except Exception as e:
        frappe.log_error("Error in clear_tokens_for_user", frappe.traceback())
        