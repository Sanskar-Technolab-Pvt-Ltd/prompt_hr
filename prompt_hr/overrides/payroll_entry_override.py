import frappe
from frappe import _
from hrms.payroll.doctype.payroll_entry.payroll_entry import PayrollEntry

class CustomPayrollEntry(PayrollEntry):

    def on_submit(self):
        super().on_submit()

        # * Get PROMPT abbreviation from HR Settings
        prompt_abbr = frappe.db.get_single_value("HR Settings", "custom_prompt_abbr")

        # * Get abbreviation of the company selected in the payroll entry
        company_abbr = frappe.db.get_value("Company", self.company, "abbr")

        # ? APPLY RESTRICTION ONLY FOR PROMPT
        if company_abbr == prompt_abbr:
            restricted_employees = list({
                row.employee for row in self.custom_remaining_payroll_details if row.employee
            })

            if restricted_employees:
                # Update employees list on current doc (self), so it's saved correctly and reflected on frontend
                self.set("employees", [])

                for emp in restricted_employees:
                    self.append("employees", {
                        "employee": emp
                    })

                # Save current doc with updated employee list
                self.save(ignore_permissions=True)


    @frappe.whitelist()
    def fill_employee_details(self):
        # * Get PROMPT abbreviation from HR Settings
        prompt_abbr = frappe.db.get_single_value("HR Settings", "custom_prompt_abbr")

        # * Get abbreviation of the company selected in the payroll entry
        company_abbr = frappe.db.get_value("Company", self.company, "abbr")

        # ? APPLY LOGIC ONLY FOR PROMPT
        if company_abbr == prompt_abbr and self.custom_is_salary_slip_created:
            result = super().fill_employee_details()

            # Get restricted employees from child table
            restricted_employees = {
                row.employee for row in self.custom_remaining_payroll_details if row.employee
            }

            # Filter employees to keep only restricted ones
            self.employees = [
                emp for emp in self.employees if emp.get("employee") in restricted_employees
            ]

            # Update employee count
            self.number_of_employees = len(self.employees)

            return result

        # Fallback to default behavior for other companies
        return super().fill_employee_details()
