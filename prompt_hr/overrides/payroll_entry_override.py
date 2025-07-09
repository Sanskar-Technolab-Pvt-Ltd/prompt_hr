import frappe
from frappe import _
from hrms.payroll.doctype.payroll_entry.payroll_entry import PayrollEntry, get_employee_list

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
            result = self.update_fill_employee_details()

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
        return self.update_fill_employee_details()
    
    def update_fill_employee_details(self):
        filters = self.make_filters()
        # ! Add custom employment type and custom business unit filter if available
        if filters:
            filters.update(dict(employment_type=self.custom_employment_type))
            filters.update(dict(custom_business_unit=self.custom_business_unit))

        employees = get_employee_list(filters=filters, as_dict=True, ignore_match_conditions=True)
        self.set("employees", [])

        if not employees:
            error_msg = _(
                "No employees found for the mentioned criteria:<br>Company: {0}<br> Currency: {1}<br>Payroll Payable Account: {2}"
            ).format(
                frappe.bold(self.company),
                frappe.bold(self.currency),
                frappe.bold(self.payroll_payable_account),
            )
            if self.branch:
                error_msg += "<br>" + _("Branch: {0}").format(frappe.bold(self.branch))
            if self.department:
                error_msg += "<br>" + _("Department: {0}").format(frappe.bold(self.department))
            # ? ADD ERROR MESSAGE FOR EMPLOYMENT TYPE
            if self.custom_employment_type:
                error_msg += "<br>" + _("Employment Type: {0}").format(frappe.bold(self.custom_employment_type))
            # ? ADD ERROR MESSAGE FOR BUSINESS UNIT
            if self.custom_business_unit:
                error_msg += "<br>" + _("Business Unit: {0}").format(frappe.bold(self.custom_business_unit))
            if self.designation:
                error_msg += "<br>" + _("Designation: {0}").format(frappe.bold(self.designation))
            if self.start_date:
                error_msg += "<br>" + _("Start date: {0}").format(frappe.bold(self.start_date))
            if self.end_date:
                error_msg += "<br>" + _("End date: {0}").format(frappe.bold(self.end_date))
            frappe.throw(error_msg, title=_("No employees found"))

        self.set("employees", employees)
        self.number_of_employees = len(self.employees)
        self.update_employees_with_withheld_salaries()

        return self.get_employees_with_unmarked_attendance()

def custom_set_filter_conditions(query, filters, qb_object):
    """Append optional filters to employee query"""

    if filters.get("employees"):
        query = query.where(qb_object.name.notin(filters.get("employees")))
        print("employees filter:", filters.get("employees"))
    # ? ADD EMPLOYMENT TYPE AND BUSINESS UNIT in LIST
    for fltr_key in ["branch", "department", "designation", "grade", "employment_type", "custom_business_unit"]:
        if filters.get(fltr_key):
            query = query.where(qb_object[fltr_key] == filters[fltr_key])

    return query
