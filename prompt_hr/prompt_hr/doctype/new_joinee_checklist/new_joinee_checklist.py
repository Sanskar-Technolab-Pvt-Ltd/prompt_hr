# Copyright (c) 2025, Jignasha Chavda and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from prompt_hr.py.utils import send_notification_email


class NewJoineeChecklist(Document):
	# ? FUNCTION TO DETECT ATTACHMENT CHANGES IN REQUIRED_DOCUMENTS AND SEND A REVERT MAIL
	def on_update(self):
		self.check_attachment_changes()

	# ? FUNCTION TO CHECK FOR ATTACHMENT CHANGES
	def check_attachment_changes(self):
		if not self.get_doc_before_save():
			return

		previous = self.get_doc_before_save()
		for current_row, previous_row in zip(self.required_documents, previous.required_documents):
			if current_row.attachment != previous_row.attachment:
				self.send_revert_mail()
				break

	# ? FUNCTION TO SEND REVERT MAIL
	def send_revert_mail(self):
		# ? CUSTOMIZE THE MAIL CONTENT AS NEEDED
		recipients = [self.job_applicant] if self.job_applicant else [] 
		if recipients:
			send_notification_email(
				recipients=recipients,
				notification_name="New Joinee Checklist HR Revert Mail",
				doctype=self.doctype,
				docname=self.name,
				button_label="View Details",
				fallback_subject="Document Attachment Changed",
				fallback_message="The attachment in the required documents has been changed. Please check your portal.",
			)
			
