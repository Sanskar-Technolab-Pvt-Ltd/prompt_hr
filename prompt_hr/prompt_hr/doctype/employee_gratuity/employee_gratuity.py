# Copyright (c) 2025, Jignasha Chavda and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class EmployeeGratuity(Document):
    def before_save(self):
        # Ensure Date of Leaving is set
        if not self.date_of_leaving:
            frappe.throw("Date of Leaving is required")

        # Get the last submitted salary slip for the employee
        last_salary_slip = frappe.get_all(
            "Salary Slip",
            filters={"employee": self.employee, "docstatus": 1},
            fields=["name"],
            order_by="creation desc",
            limit=1
        )

        already_exists = frappe.get_all(
            "Employee Gratuity",
            filters={"employee": self.employee, "docstatus":["<", 2], "name": ["!=", self.name]},
            fields=["name"],
            order_by="creation desc",
            limit=1
        )

        if already_exists:
            frappe.throw("Employee Gratuity already exists for this employee.", title="Employee Gratuity Exists")

        if not last_salary_slip:
            frappe.throw("No submitted Salary Slip found for this employee.")

        last_salary_slip_name = last_salary_slip[0].name
        self.last_salary_slip = last_salary_slip_name

        # Fetch the Employee document
        employee = frappe.get_doc("Employee", self.employee)
        company_abbr = frappe.db.get_value("Company", employee.company, "abbr")

        # Get custom abbreviations from HR Settings
        prompt_abbr = frappe.db.get_single_value("HR Settings", "custom_prompt_abbr")
        indifoss_abbr = frappe.db.get_single_value("HR Settings", "custom_indifoss_abbr")

        total_earning = 0
    
        # For Prompt companies: Sum Basic Salary and Dearness Allowance from Salary Detail
        if company_abbr and company_abbr == prompt_abbr:
            salary_components = frappe.get_all(
                "Salary Detail",
                filters={"parent": last_salary_slip_name, "parentfield": "earnings"},
                fields=["salary_component", "amount"]
            )
            for comp in salary_components:
                if comp.salary_component in ["Basic Salary", "Dearness Allowance"]:
                    total_earning += comp.amount

        # For Indifoss companies: Sum Basic + DA from Salary Detail
        elif company_abbr and company_abbr == indifoss_abbr:
            salary_components = frappe.get_all(
                "Salary Detail",
                filters={"parent": last_salary_slip_name, "parentfield": "earnings"},
                fields=["salary_component", "amount"]
            )
            for comp in salary_components:
                if comp.salary_component == "Basic + DA":
                    total_earning += comp.amount

        self.last_drawn_salary = total_earning

        # Calculate gratuity amount if total_earning and total_working_year are set
        if total_earning > 0 and self.total_working_year:
            self.gratuity_amount = self.last_drawn_salary * (15 / 26) * self.total_working_year
        else:
            self.gratuity_amount = 0  # or leave blank if field is Data type



