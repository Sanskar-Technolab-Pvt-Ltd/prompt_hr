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


	def before_save(self):

		# * UPDATING LINKED HOLIDAY LIST IF THE DOC IS UPDATED
		old_doc = self.get_doc_before_save()
		if old_doc:
			field_changes = self.has_field_changes(old_doc)
			child_table_changes = self.has_child_table_changed(old_doc)
			if field_changes or child_table_changes:
				self.update_linked_holiday_lists()
			

		
	def validate_days(self):
		if getdate(self.from_date) > getdate(self.to_date):
			throw(_("To Date cannot be before From Date"))

		for day in self.get("holidays"):
			if not (getdate(self.from_date) <= getdate(day.holiday_date) <= getdate(self.to_date)):
				frappe.throw(_("The holiday on {0} is not between From Date and To Date").format(formatdate(day.holiday_date)))

	
	def update_linked_holiday_lists(self):
		"""Method to update all holiday lists where these document is linked if the this document data is updated
		"""
		try:
				import calendar
				from datetime import timedelta
				from dateutil import relativedelta
    
				holiday_lists = frappe.db.get_all("Holiday List", {"custom_festival_holiday_list": self.name}, "name")

				print(f"\n Something updated  {holiday_lists}\n")

				final_date_list = [{"date":getdate(row.holiday_date), "description": row.description, "weekly_off": row.weekly_off, "custom_is_optional_festival_leave": row.custom_is_optional_festival_leave} for row in self.holidays]
    
				start_date = getdate(self.from_date)
				end_date = getdate(self.to_date)
	
				if holiday_lists:
					for holiday_list_id in holiday_lists:
						
						final_date_list = [ date_dict for date_dict in final_date_list if not date_dict.get("weekly_off")]
						print(f"\n\n final_datelist {final_date_list} \n\n")
						holiday_list_doc = frappe.get_doc("Holiday List", holiday_list_id)
						holiday_list_doc.holidays = []
						holiday_list_doc.from_date = self.from_date
						holiday_list_doc.to_date = self.to_date
						
						weeklyoff_type = holiday_list_doc.custom_weeklyoff_type
				
						if weeklyoff_type:
							weeklyoff_days = frappe.get_all("WeekOff Multiselect", {"parenttype": "WeeklyOff Type", "parent": weeklyoff_type}, "weekoff", order_by="weekoff asc", pluck="weekoff")
						else:
							weeklyoff_days = None
							throw("Please Set Employee WeeklyOff Type")

						if weeklyoff_days:
							
							print(f"\n\n weekly_off {weeklyoff_days} {weeklyoff_type} \n\n")
							for weeklyoff_day in weeklyoff_days:
								weekday = getattr(calendar, (weeklyoff_day).upper())
								reference_date = start_date + relativedelta.relativedelta(weekday=weekday)
								
								while reference_date <= end_date:
									if not any(holiday_date.get("date") == reference_date for holiday_date in final_date_list):
										final_date_list.append({
											"date": reference_date,
											"description": weeklyoff_day,
											"weekly_off": 1
										})
									reference_date += timedelta(days=7)
                
						for holiday in final_date_list:
							holiday_list_doc.append("holidays", {"description": holiday.get("description"),"holiday_date": holiday.get("date"), "weekly_off": holiday.get("weekly_off"), "custom_is_optional_festival_leave":holiday.get("custom_is_optional_festival_leave")})

						
						

						holiday_list_doc.save(ignore_permissions=True)


		except Exception as e:
			frappe.log_error("Error while updating Linked Holiday lists", frappe.get_traceback())
			throw(f"{str(e)}")
	def has_field_changes(self, old_doc):
		"""Method to check if the fields are updated or not
		"""
		if (getdate(self.from_date) != old_doc.from_date) or (getdate(self.to_date) != old_doc.to_date):
			return 1
		return 0

	def has_child_table_changed(self, old_doc):
		"""Method to check if the chid table values are changed or not
		"""
		
		if (len(self.holidays) < len(old_doc.holidays)) or len(self.holidays) > len(old_doc.holidays):
			return 1

		old_date = [d.holiday_date for d in old_doc.holidays]
		old_desc = [d.description for d in old_doc.holidays]

		for new in self.holidays:
	
			if (getdate(new.holiday_date) not in old_date) or (new.description not in old_desc):
				return 1
			else:
				return 0
				
