# Copyright (c) 2025, Jignasha Chavda and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class MeetingRequest(Document):
	def on_update(self):
		share_doc_to_users(self)

def share_doc_to_users(doc):
    """This automatically assigns and shares the document on the on_update event, based on the user set
    in the User table. If a user is removed, their read permission and assignment are also revoked.
    """
    # ? IF DOCUMENT IS NOT NEW THAT TIME ONLY RUN THIS SCRIPT
    if not doc.is_new():
        users = doc.table_qygi
 
        # ? GET LIST OF ALL CURRENT USER SETTED IN THE CHILD TABLE
        current_users = {row.participant for row in users if row.related_to == "User"}
 
        # ? GET A LIST OF ALL open STATUS TODO(ASSIGNMENTS) FOR THIS PARTICULAR DOCUMENT
        assigned_todos = frappe.get_all(
            "ToDo",
            filters={
                "reference_type": "Meeting Request",
                "reference_name": doc.name,
                "status": "Open",
            },
            fields=["name", "allocated_to"],
        )
 
        # ? GET ALL DOCUMENT SHARE FOR THIS CURRENT DOCUMENT (PERMISSIONS WE GIVEN IN THE SIDEBAR)
        shared_users = frappe.get_all(
            "DocShare",
            filters={
                "share_doctype": "Meeting Request",
                "share_name": doc.name,
            },
            fields=["name", "user"],
        )
 
        # ? REMOVE ASSIGNED IF USER IS NOT AVAILABLE IN THE USER CHILD TABLE
        for todo in assigned_todos:
            # ? VALIDATE THE USER IS AVAILABLE OR NOT IN THE USERLIST
            if todo.allocated_to not in current_users:
                frappe.delete_doc(
                    "ToDo", todo.name, force=True, ignore_permissions=True
                )
 
        # ? REMOVE SHARE PERMISSIONS IF USER IS NOT AVAILABLE IN THE USER CHILD TABLE
        for share in shared_users:
            if share.user not in current_users:
                frappe.delete_doc(
                    "DocShare", share.name, force=True, ignore_permissions=True
                )
 
        # ? AUTO ASSIGN AND SHARE TO USER IF USER IS ADD IN USER CHILD TABLE
        for user in users:
            if user.related_to == "User":
                user = user.participant
 
                # ? CHECK OPEN TODO(ASSIGNMENT) ALREADY EXISTS OR NOT BASED ON THE OPEN STATUS
                existing_todo = frappe.db.get_value(
                    "ToDo",
                    {
                        "allocated_to": user,
                        "reference_type": "Meeting Request",
                        "reference_name": doc.name,
                        "status": "Open",
                    },
                    "name"
                )
                # ? IF NOT EXISTS TODO(ASSIGNMENT) FOR ADDED NEW USER IN CHILD TABLE
                if not existing_todo:
                    # ? create new todo(Assignment) if any open todo is not exists
                    todo = frappe.new_doc("ToDo")
                    todo.update(
                        {
                            "reference_type": doc.doctype,
                            "reference_name": doc.name,
                            "allocated_to": user,
                            "assigned_by": frappe.session.user,
                            "description": doc.meeting_title,
                        }
                    )
                    # ? INSERT DOCUMENT
                    todo.insert(ignore_permissions=True)
 
                # ? IF SHARE PERMISSION NOT EXISTS THATTIME ONLY RUN THIS
                if not frappe.db.exists(
                    "DocShare",
                    {"user": user, "share_doctype": "Campaign", "share_name": doc.name},
                ):
                # ? IF THE USER HAS THE 'Marketing User' ROLE, ONLY GRANT READ-ONLY ACCESS TO THE CAMPAIGN DOCUMENT
                    frappe.share.add(
                        "Meeting Request",
                        doc.name,
                        user,
                        read=1,
                        write=0,
                        share=0,
                        everyone=0,
                    )
        # ? RELOAD DOC
        doc.reload()