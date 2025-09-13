# Copyright (c) 2025, Jignasha Chavda and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import now_datetime
from frappe.model.document import Document


class PenaltyEmails(Document):
	pass

@frappe.whitelist()
def send_penalty_emails(docname):
	doc = frappe.get_doc("Penalty Emails", docname)

	for email_row in doc.email_details:
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
				except Exception as e:
					email_row.error = f" {str(e)} \n\n {frappe.get_traceback()}"
			else:
				email_row.error = f"No Email Found"
	
	doc.status = "Sent"
	doc.save()
	frappe.db.commit()
	
		
	
		
    