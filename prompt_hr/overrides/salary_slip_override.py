import frappe
from frappe import _
from frappe.utils import ceil, flt
from hrms.payroll.doctype.salary_slip.salary_slip import SalarySlip

# ? CustomSalarySlip enhances SalarySlip by including:
# ! - Penalty leave calculation
# ! - Overtime computation
# ! - Custom payment day logic

class CustomSalarySlip(SalarySlip):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def before_submit(self):
        self.apply_custom_adhoc_components()

    def before_save(self):
        self.apply_custom_adhoc_components()
    
    def get_status(self):
        if self.docstatus == 2:
            return "Cancelled"
        else:
            if self.salary_withholding:
                return "Withheld"
            elif self.docstatus == 0:

                if self.payroll_entry:
                    is_salary_withheld = frappe.db.get_all("Hold Salary", {"parenttype": "Payroll Entry", "parent": self.payroll_entry, "employee": self.employee, "withholding_type": "Hold Salary Release"}, "name", limit=1)
                    if is_salary_withheld:
                        return "Salary Withheld"
                    else:
                        return "Draft"
                else:
                    return "Draft"
            elif self.docstatus == 1:
                return "Submitted"
    def get_working_days_details(self, lwp=None, for_preview=0):
        # * Step 1: Inherit default logic
        super().get_working_days_details(lwp, for_preview)

        # * Step 2: Set overtime hours
        self.set_overtime()

        # * Step 3: Custom LOP and penalty logic
        self.set_lop_and_penalty()

        if self.payroll_entry:
            self.set_payment_days()

    # * Fetches LOP and penalty days from Payroll Entry or fallback from Employee Penalty
    def set_lop_and_penalty(self):
        penalty_leaves = 0

        if self.payroll_entry:
            payroll_entry = frappe.get_doc("Payroll Entry", self.payroll_entry)
            for entry in payroll_entry.get("custom_lop_summary", []):
                summary = frappe.get_doc("LOP Summary", entry.name)
                if summary.employee == self.employee:
                    self.leave_without_pay = summary.lop_adjustment or (
                        (summary.actual_lop or 0) + (summary.penalty_leave_days or 0)
                    )
                    self.custom_penalty_leave_days = summary.penalty_leave_days or 0
                    return  # ! Exit if matched
        else:
            # ? Fallback: Manually calculate penalty from Employee Penalty records
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

    # * Computes total overtime from Attendance doctype
    def set_overtime(self):
        attendance = frappe.get_all(
            "Attendance",
            filters={
                "employee": self.employee,
                "company": self.company,
                "docstatus": ["!=", 2],  # ! Exclude cancelled records
                "attendance_date": ["between", [self.start_date, self.end_date]]
            },
            fields=["custom_overtime"]
        )
        self.custom_overtime = sum(
            att.get("custom_overtime", 0) for att in attendance if att.get("custom_overtime")
        )

    # * Computes actual payment days by subtracting LWP
    def set_payment_days(self):
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

        # * Adjust for LWP
        if total_days > self.leave_without_pay:
            total_days -= self.leave_without_pay
        else:
            total_days = 0

        self.payment_days = total_days

    def apply_custom_adhoc_components(self):
        if self.payroll_entry:
            # * Get the related Payroll Entry document
            payroll_entry = frappe.get_doc("Payroll Entry", self.payroll_entry)

            # * Load the linked Salary Structure
            salary_structure = frappe.get_doc("Salary Structure", self.salary_structure)

            for entry in payroll_entry.custom_adhoc_salary_details or []:
                # * Only process entries for the current employee
                if entry.employee == self.employee:
                    # * Determine component type (earning/deduction)
                    component = frappe.get_doc("Salary Component", entry.salary_component)
                    comp_type = "earnings" if component.type == "Earning" else "deductions"

                    # ? Check if the component exists in the salary structure (template-defined)
                    structure_row = None
                    for row in salary_structure.get(comp_type) or []:
                        if row.salary_component == entry.salary_component:
                            structure_row = row
                            break 
                    
                    # ? Check if the component exists in the current salary slip
                    slip_row = None
                    for row in self.get(comp_type) or []:
                        if row.salary_component == entry.salary_component:
                            slip_row = row
                            break

                    if slip_row and structure_row:
                        # * Case 1: Exists in both structure and slip → update amount
                        slip_row.amount = flt(slip_row.amount) + flt(entry.amount)

                    elif slip_row and not structure_row:
                        # * Case 2: Manually added (not in structure) → skip
                        continue

                    else:
                        # ! Case 3: Not in structure or slip → add as new
                        self.append(comp_type, {
                            "salary_component": entry.salary_component,
                            "amount": flt(entry.amount),
                            "salary_component_abbr": component.salary_component_abbr or ""
                        })

            # * Update gross pay and totals
            self.gross_pay = self.get_component_totals("earnings", depends_on_payment_days=1)
            self.base_gross_pay = flt(self.gross_pay * self.exchange_rate, self.precision("base_gross_pay"))
            self.set_totals()
            self.compute_year_to_date()
            self.compute_month_to_date()
            self.compute_component_wise_year_to_date()
        
    def compute_annual_deductions_before_tax_calculation(self):
        tax_slab = frappe.db.get_value('Salary Structure Assignment', self.custom_salary_structure_assignment, 'income_tax_slab')
        is_new_tax_slab = frappe.db.get_value('Income Tax Slab', tax_slab, 'custom_is_new_regime')

        prev_period_exempted_amount = 0
        current_period_exempted_amount = 0
        future_period_exempted_amount = 0

        # Previous period exempted amount (applies only for exempted components)
        prev_period_exempted_amount = self.get_salary_slip_details(
            self.payroll_period.start_date,
            self.start_date,
            parentfield="deductions",
            exempted_from_income_tax=1,
        )

        # Current period exempted amount
        for d in self.get("deductions"):
            if d.exempted_from_income_tax:
                if is_new_tax_slab:
                    # In new slab, check if the component should NOT be exempt
                    not_exempt_for_new_slab = frappe.db.get_value('Salary Component', d.salary_component, 'custom_do_not_exempt_for_new_tax_slab')
                    if not not_exempt_for_new_slab:
                        current_period_exempted_amount += d.amount
                else:
                    # In old slab, exempt directly
                    current_period_exempted_amount += d.amount

        # Future period exempted amount
        for deduction in self._salary_structure_doc.get("deductions"):
            if deduction.exempted_from_income_tax:
                if is_new_tax_slab:
                    not_exempt_for_new_slab = frappe.db.get_value('Salary Component', deduction.salary_component, 'custom_do_not_exempt_for_new_tax_slab')
                    if not not_exempt_for_new_slab:
                        if deduction.amount_based_on_formula:
                            for sub_period in range(1, ceil(self.remaining_sub_periods)):
                                future_period_exempted_amount += self.get_amount_from_formula(deduction, sub_period)
                        else:
                            future_period_exempted_amount += deduction.amount * (ceil(self.remaining_sub_periods) - 1)
                else:
                    # In old slab, exempt directly
                    if deduction.amount_based_on_formula:
                        for sub_period in range(1, ceil(self.remaining_sub_periods)):
                            future_period_exempted_amount += self.get_amount_from_formula(deduction, sub_period)
                    else:
                        future_period_exempted_amount += deduction.amount * (ceil(self.remaining_sub_periods) - 1)

        return (
            prev_period_exempted_amount + current_period_exempted_amount + future_period_exempted_amount
        ) or 0


    def get_taxable_earnings(self, allow_tax_exemption=False, based_on_payment_days=0):
        tax_slab = frappe.db.get_value('Salary Structure Assignment', self.custom_salary_structure_assignment, 'income_tax_slab')
        is_new_tax_slab = frappe.db.get_value('Income Tax Slab', tax_slab, 'custom_is_new_regime')

        taxable_earnings = 0
        additional_income = 0
        additional_income_with_full_tax = 0
        flexi_benefits = 0
        amount_exempted_from_income_tax = 0

        for earning in self.earnings:
            if based_on_payment_days:
                amount, additional_amount = self.get_amount_based_on_payment_days(earning)
            else:
                if earning.additional_amount:
                    amount, additional_amount = earning.amount, earning.additional_amount
                else:
                    amount, additional_amount = earning.default_amount, earning.additional_amount

            if earning.is_tax_applicable:
                if earning.is_flexible_benefit:
                    flexi_benefits += amount
                else:
                    taxable_earnings += amount - additional_amount
                    additional_income += additional_amount

                    if additional_amount and earning.is_recurring_additional_salary:
                        additional_income += self.get_future_recurring_additional_amount(
                            earning.additional_salary, earning.additional_amount
                        )

                    if earning.deduct_full_tax_on_selected_payroll_date:
                        additional_income_with_full_tax += additional_amount

        if allow_tax_exemption:
            for ded in self.deductions:
                if ded.exempted_from_income_tax:
                    if is_new_tax_slab:
                        not_exempt_for_new_tax_slab = frappe.db.get_value(
                            'Salary Component', ded.salary_component, 'custom_do_not_exempt_for_new_tax_slab'
                        )
                        if not not_exempt_for_new_tax_slab:
                            # Proceed only if not marked as "Do not exempt for new tax slab"
                            pass
                        else:
                            continue  # Skip deduction if it's marked as not exempt in new slab

                    # In old slab or allowed in new slab
                    amount, additional_amount = ded.amount, ded.additional_amount
                    if based_on_payment_days:
                        amount, additional_amount = self.get_amount_based_on_payment_days(ded)

                    taxable_earnings -= flt(amount - additional_amount)
                    additional_income -= additional_amount
                    amount_exempted_from_income_tax += flt(amount - additional_amount)

                    if additional_amount and ded.is_recurring_additional_salary:
                        additional_income -= self.get_future_recurring_additional_amount(
                            ded.additional_salary, ded.additional_amount
                        )

        return frappe._dict(
            {
                "taxable_earnings": taxable_earnings,
                "additional_income": additional_income,
                "amount_exempted_from_income_tax": amount_exempted_from_income_tax,
                "additional_income_with_full_tax": additional_income_with_full_tax,
                "flexi_benefits": flexi_benefits,
            }
        )
        
    def set_salary_structure_assignment(self):
        self._salary_structure_assignment = frappe.db.get_value(
            "Salary Structure Assignment",
            {
                "employee": self.employee,
                "salary_structure": self.salary_structure,
                "from_date": ("<=", self.actual_start_date),
                "docstatus": 1,
            },
            "*",
            order_by="from_date desc",
            as_dict=True,
        )

        if self._salary_structure_assignment:
            self.custom_salary_structure_assignment = self._salary_structure_assignment.name

        if not self._salary_structure_assignment:
            frappe.throw(
                _(
                    "Please assign a Salary Structure for Employee {0} applicable from or before {1} first"
                ).format(
                    frappe.bold(self.employee_name),
                    frappe.bold(formatdate(self.actual_start_date)),
                )
            )


