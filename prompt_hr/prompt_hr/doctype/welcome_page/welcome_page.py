# Copyright (c) 2025, Jignasha Chavda and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class WelcomePage(Document):
	def on_update(self):
		frappe.db.set_value("Employee",{"user_id": self.user}, "custom_nps_consent", self.nps_consent)

		if self.pran_no and self.do_you_have_a_pran_no==1:
			frappe.db.set_value("Employee",{"user_id": self.user}, "custom_pran_number", self.pran_no)