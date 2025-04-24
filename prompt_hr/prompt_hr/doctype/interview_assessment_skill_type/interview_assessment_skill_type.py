# Copyright (c) 2025, Jignasha Chavda and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class InterviewAssessmentSkillType(Document):
	def before_save(self):
		skill_types = frappe.get_all("Interview Assessment Skill Type", filters={"company":self.company,"name":["!=",self.name]},fields=["name","weightage"])
		sum_weightage = 0
		for skill_type in skill_types:
			sum_weightage += skill_type.weightage

		if sum_weightage + self.weightage > 100:
			frappe.throw("Sum of weightage cannot be greater than 100")
