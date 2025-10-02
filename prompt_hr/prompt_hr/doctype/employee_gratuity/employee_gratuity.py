# Copyright (c) 2025, Jignasha Chavda and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class EmployeeGratuity(Document):
    def before_save(self):
        # Ensure Date of Leaving is set
        if not self.date_of_leaving:
            frappe.throw("Date of Leaving is required")

        # ? GET THE LAST SUBMITTED EMPLOYEE STANDARD SALARY FOR THE EMPLOYEE
        employee_standard_salary = frappe.get_all(
            "Employee Standard Salary",
            filters={"employee": self.employee},
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

        if not employee_standard_salary:
            frappe.throw("No Employee Standard Salary found for this employee.")

        employee_standard_salary_name = employee_standard_salary[0].name

        # Fetch the Employee document
        employee = frappe.get_doc("Employee", self.employee)
        company_abbr = frappe.db.get_value("Company", employee.company, "abbr")

        # Get custom abbreviations from HR Settings
        prompt_abbr = frappe.db.get_single_value("HR Settings", "custom_prompt_abbr")
        indifoss_abbr = frappe.db.get_single_value("HR Settings", "custom_indifoss_abbr")

        total_earning = 0
        last_drawn_basic = 0
        last_drawn_da = 0
        # For Prompt companies: Sum Basic Salary and Dearness Allowance from Salary Detail
        if company_abbr and company_abbr == prompt_abbr:
            salary_components = frappe.get_all(
                "Salary Detail",
                filters={"parent": employee_standard_salary_name, "parentfield": "earnings"},
                fields=["salary_component", "amount"]
            )
            for comp in salary_components:
                salary_component = frappe.get_doc("Salary Component", comp.salary_component)
                if salary_component.custom_salary_component_type == "Basic Salary" or salary_component.custom_salary_component_type == "Dearness Allowance":
                    if salary_component.custom_salary_component_type == "Basic Salary":
                        last_drawn_basic += comp.amount
                    else:
                        last_drawn_da += comp.amount
                    total_earning += comp.amount

        # For Indifoss companies: Basic Salary from Salary Detail
        elif company_abbr and company_abbr == indifoss_abbr:
            salary_components = frappe.get_all(
                "Salary Detail",
                filters={"parent": employee_standard_salary_name, "parentfield": "earnings"},
                fields=["salary_component", "amount"]
            )
            for comp in salary_components:
                salary_component = frappe.get_doc("Salary Component", comp.salary_component)
                if salary_component.custom_salary_component_type == "Basic Salary":
                    total_earning += comp.amount
                    break

        self.last_drawn_salary = round(total_earning)
        self.last_drawn_basic = round(last_drawn_basic)
        self.last_drawn_da = round(last_drawn_da)

        # Calculate gratuity amount if total_earning and total_working_year are set
        if total_earning > 0 and self.total_working_year:
            self.gratuity_amount = self.last_drawn_salary * (15 / 26) * self.total_working_year
            self.gratuity_amount = round(self.gratuity_amount)
        else:
            self.gratuity_amount = 0  # or leave blank if field is Data type


    def on_submit(self):
        #! GET THE NOTIFICATION TEMPLATE DOC
        notification_doc = frappe.get_doc("Notification", "Gratuity Submitted Notification")
        if not notification_doc:
            return

        #! STEP 1: GET ALL USERS WITH 'Accounts User' ROLE
        role_users = frappe.get_all(
            "Has Role",
            filters={"role": "Accounts User"},
            fields=["parent"],
            distinct=True
        )
        user_ids = [user.parent for user in role_users]

        if not user_ids:
            return

        #! STEP 2: GET USER EMAILS
        user_emails = frappe.get_all(
            "User",
            filters={"name": ["in", user_ids], "enabled": 1},
            fields=["email"],
            pluck="email"
        )

        if not user_emails:
            return

        #! STEP 3: BUILD TEMPLATE VARIABLES
        gratuity_link = f"{frappe.utils.get_url()}/app/employee-gratuity/{self.name}"
        #! RENDER SUBJECT AND MESSAGE FROM NOTIFICATION TEMPLATE
        subject = frappe.render_template(notification_doc.subject or "", {"doc": self})
        message = frappe.render_template(notification_doc.message or "", {"doc": self, "link": gratuity_link})
        #! STEP 4: SEND EMAIL TO ACCOUNTS USERS
        frappe.sendmail(
            recipients=user_emails,
            subject=subject,
            content=message
        )
