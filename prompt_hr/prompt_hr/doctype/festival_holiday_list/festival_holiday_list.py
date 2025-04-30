# Copyright (c) 2025, Jignasha Chavda and contributors
# For license information, please see license.txt

import frappe
from frappe import _, throw
from frappe.model.document import Document
from frappe.utils import formatdate, getdate, today



class FestivalHolidayList(Document):
	
	def validate(self):
		self.validate_days()
		# self.total_holidays = len(self.holidays)
		# self.validate_duplicate_date()
		# self.sort_holidays()

	def validate_days(self):
		if getdate(self.from_date) > getdate(self.to_date):
			throw(_("To Date cannot be before From Date"))

		for day in self.get("holidays"):
			if not (getdate(self.from_date) <= getdate(day.holiday_date) <= getdate(self.to_date)):
				frappe.throw(_("The holiday on {0} is not between From Date and To Date").format(formatdate(day.holiday_date)))
