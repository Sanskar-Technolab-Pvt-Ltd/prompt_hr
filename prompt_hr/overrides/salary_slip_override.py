import frappe
from frappe import _
from hrms.payroll.doctype.salary_slip.salary_slip import SalarySlip

# * CustomSalarySlip overrides the default SalarySlip class to include penalty leaves and custom overtime
class CustomSalarySlip(SalarySlip):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    # * Override the get_payment_days method to subtract custom penalties and LOPs
    def get_payment_days(self, include_holidays_in_total_working_days):
        # Call the parent class method to get the base payment days
        payment_days = super().get_payment_days(include_holidays_in_total_working_days)

        # Get additional deductions if available
        custom_lop_days = self.custom_lop_days or 0
        penalty_leaves = self.custom_penalty_leave_days or 0

        # * Modify payment days to exclude penalties and add custom LOPs
        modified_payment_days = self.total_working_days  + custom_lop_days - penalty_leaves
        return modified_payment_days

    # * Override set_salary_structure_doc to fetch penalty leaves and overtime
    def set_salary_structure_doc(self) -> None:
        penalty_leaves = 0

        # * Fetch penalties for the employee within the payroll period
        employee_penalty = frappe.get_all(
            "Employee Penalty",
            filters={
                "employee": self.employee,
                "company": self.company,
                "penalty_date": ["between", [self.start_date, self.end_date]]
            },
            fields=["name", "deduct_leave_without_pay"]
        )

        # Sum up penalty leaves
        if employee_penalty:
            for penalty in employee_penalty:
                penalty_leaves += penalty.deduct_leave_without_pay

        # Store penalty leaves in a custom field on the salary slip
        self.custom_penalty_leave_days = penalty_leaves

        overtime = 0

        # * Fetch attendance records with custom overtime values for the payroll period
        attendance = frappe.get_all(
            "Attendance",
            filters={
                "employee": self.employee,
                "company": self.company,
                "docstatus": ["!=", 2],  # ! Skip cancelled attendance
                "attendance_date": ["between", [self.start_date, self.end_date]]
            },
            fields=["name", "custom_overtime"]
        )

        # Sum up custom overtime values
        if attendance:
            for att in attendance:
                overtime += att.custom_overtime

        # Store overtime in a custom field
        self.custom_overtime = overtime
        # * Finally, call the parent method to continue standard processing
        super().set_salary_structure_doc()
