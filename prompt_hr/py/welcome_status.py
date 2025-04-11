
import frappe
import traceback

# ? FUNCTION TO CREATE WELCOME PAGE RECORD FOR NEW USERS
def create_welcome_status(doc):
    try:
        # ? CHECK IF RECORD ALREADY EXISTS
        if frappe.db.exists("Welcome Page", {"user": doc.name}):
            frappe.log_error(
                title="Welcome Page Already Exists",
                message=f"Welcome Page for user {doc.name} already exists. Skipping creation."
            )
            return

        # ? CREATE NEW WELCOME PAGE RECORD
        welcome_status = frappe.new_doc("Welcome Page")
        welcome_status.user = doc.name
        welcome_status.is_completed = 0
        welcome_status.insert(ignore_permissions=True)

        # ? SHARE WELCOME PAGE WITH USER
        frappe.share.add(
            doctype="Welcome Page",
            name=welcome_status.name,
            user=doc.name,
            read=1,
            write=1,
            share=0
        )

        frappe.db.commit()

        frappe.log_error(
            title="Welcome Page Creation",
            message=f"Welcome Page created and shared with user {doc.name}."
        )

    except Exception as e:
        frappe.log_error(
            title="Welcome Page Creation Error",
            message=f"Error creating Welcome Page for user {doc.name}: {str(e)}\n{traceback.format_exc()}"
        )


def after_insert(doc,method):
    # ? CREATE WELCOME PAGE RECORD FOR NEW USERS
    create_welcome_status(doc)