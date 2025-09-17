# Copyright (c) 2025, Jignasha Chavda and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import now_datetime
from frappe.model.document import Document
import json


class PenaltyEmails(Document):
	pass

@frappe.whitelist()
def send_penalty_emails(docname: str, selected_row_names: str | None = None):
    """
    SEND PENALTY EMAILS FOR ONLY THE SELECTED CHILD ROWS.
    - MARK EACH SELECTED CHILD ROW AS SENT WHEN MAIL SUCCEEDS.
    - UPDATE PARENT DOC STATUS TO "Sent" **ONLY IF ALL CHILD ROWS ARE SENT**.
    - DELETE THE CHILD ROWS THAT WERE SUCCESSFULLY SENT.
    """

    #! FETCH PARENT DOCUMENT
    doc = frappe.get_doc("Penalty Emails", docname)

    #! PARSE SELECTED CHILD ROW NAMES INTO PYTHON LIST
    if selected_row_names:
        try:
            selected_row_names = json.loads(selected_row_names)
        except Exception:
            #? IF ALREADY A LIST OR BAD JSON, LEAVE AS IS
            pass
    else:
        selected_row_names = []

    #! KEEP TRACK OF ROWS THAT WERE SENT SUCCESSFULLY
    successfully_sent_rows = []

    for email_row in doc.email_details:
        #! PROCESS ONLY SELECTED ROWS
        if selected_row_names and email_row.name not in selected_row_names:
            continue

        if email_row.email:
            recipient = email_row.email
            subject = email_row.subject or "Penalty Warning"
            message = email_row.message or "This is a default penalty warning message."

            try:
                frappe.sendmail(
                    recipients=recipient,
                    subject=subject,
                    message=message
                )
                email_row.sent = 1
                successfully_sent_rows.append(email_row)
            except Exception as e:
                email_row.error = f"{str(e)}\n\n{frappe.get_traceback()}"
        else:
            email_row.error = "No Email Found"

    #! IF ALL CHILD ROWS (REMAINING) ARE SENT, MARK PARENT AS SENT
    #? ANY ROW STILL PRESENT IN THE CHILD TABLE IS EITHER UNSENT OR FAILED
    if all(row.sent for row in doc.email_details):
        doc.status = "Sent"

    #! SAVE CHANGES AND COMMIT
    doc.save(ignore_permissions=True)
    frappe.db.commit()
