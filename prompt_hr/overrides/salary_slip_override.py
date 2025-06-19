import frappe
from frappe import _
from hrms.payroll.doctype.salary_slip.salary_slip import SalarySlip

# ? CustomSalarySlip enhances SalarySlip by including:
# ! - Penalty leave calculation
# ! - Overtime computation
# ! - Custom payment day logic
class CustomSalarySlip(SalarySlip):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def calculate_component_amounts(self, component_type):
        # * Step 1: Apply penalty leave logic (from LOP Summary or Penalty records)
        self._set_lop_and_penalty()

        # * Step 2: Compute total overtime from Attendance
        self._set_overtime()

        super().calculate_component_amounts(component_type)

    # * Recalculates LOP and penalty days either from Payroll Entry or Employee Penalty
    def _set_lop_and_penalty(self):
        penalty_leaves = 0

        if self.payroll_entry:
            # ? Use LOP Summary if linked to a Payroll Entry
            payroll_entry = frappe.get_doc("Payroll Entry", self.payroll_entry)

            for entry in payroll_entry.get("custom_lop_summary", []):
                summary = frappe.get_doc("LOP Summary", entry.name)
                if summary.employee == self.employee:
                    self.leave_without_pay = (
                        summary.lop_adjustment
                        if summary.lop_adjustment
                        else (summary.actual_lop or 0) + (summary.penalty_leave_days or 0)
                    )
                    self.custom_penalty_leave_days = summary.penalty_leave_days or 0
                    self._set_payment_days()
                    return  # ! Exit early if matched
        else:
            # ? Fallback: Manually compute penalty leaves from Employee Penalty records
            penalties = frappe.get_all(
                "Employee Penalty",
                filters={
                    "employee": self.employee,
                    "company": self.company,
                    "penalty_date": ["between", [self.start_date, self.end_date]]
                },
                fields=["deduct_leave_without_pay"]
            )
            penalty_leaves = sum(p.get("deduct_leave_without_pay", 0) for p in penalties)
            self.custom_penalty_leave_days = penalty_leaves

    # * Calculates overtime hours from the Attendance doctype
    def _set_overtime(self):
        attendance = frappe.get_all(
            "Attendance",
            filters={
                "employee": self.employee,
                "company": self.company,
                "docstatus": ["!=", 2],  # ! Skip cancelled entries
                "attendance_date": ["between", [self.start_date, self.end_date]]
            },
            fields=["custom_overtime"]
        )
        self.custom_overtime = sum(
            att.get("custom_overtime", 0) for att in attendance if att.get("custom_overtime")
        )

    # * Computes actual payment days by subtracting LWP
    def _set_payment_days(self):
        payroll_settings = frappe.get_cached_value(
            "Payroll Settings",
            None,
            (
                "payroll_based_on",
                "include_holidays_in_total_working_days",
                "consider_marked_attendance_on_holidays",
                "daily_wages_fraction_for_half_day",
                "consider_unmarked_attendance_as",
            ),
            as_dict=True
        )

        total_days = self.get_payment_days(
            payroll_settings.include_holidays_in_total_working_days
        )

        # * Deduct LWP if applicable
        if self.leave_without_pay:
            total_days -= self.leave_without_pay

        self.payment_days = total_days
