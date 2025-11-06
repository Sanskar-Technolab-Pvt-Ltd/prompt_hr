import frappe
from frappe import _
import json
from frappe.utils import ceil, flt, formatdate, cint
from hrms.hr.utils import validate_active_employee
from hrms.payroll.doctype.salary_slip.salary_slip import SalarySlip
from hrms.payroll.doctype.salary_slip.salary_slip_loan_utils import (
	set_loan_repayment,
)
from hrms.payroll.doctype.payroll_period.payroll_period import (
	get_period_factor,
)

# ? CustomSalarySlip enhances SalarySlip by including:
# ! - Penalty leave calculation
# ! - Overtime computation
# ! - Custom payment day logic

class CustomSalarySlip(SalarySlip):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def validate(self):
        self.check_salary_withholding()
        self.status = self.get_status()
        validate_active_employee(self.employee)
        self.validate_dates()
        self.check_existing()

        if self.payroll_frequency:
            self.get_date_details()

        if not (len(self.get("earnings")) or len(self.get("deductions"))):
            self.get_emp_and_working_day_details()
        else:
            self.get_working_days_details(lwp=self.leave_without_pay)

        self.set_salary_structure_assignment()

        # ? ONLY CALCULATE NET PAY WHEN THE SALARY SLIP IS NEW.
        
        self.verify_duplicate_component_entry()
        self.calculate_net_pay()
        self.compute_year_to_date()
        self.compute_month_to_date()
        self.compute_component_wise_year_to_date()

        self.add_leave_balances()

        max_working_hours = frappe.db.get_single_value(
            "Payroll Settings", "max_working_hours_against_timesheet"
        )

        if max_working_hours:
            if self.salary_slip_based_on_timesheet and (self.total_working_hours > int(max_working_hours)):
                frappe.msgprint(
                    _("Total working hours should not be greater than max working hours {0}").format(
                        max_working_hours
                    ),
                    alert=True,
                )

    def before_save(self):
        # ? ADD ADHOC COMPONENTS ONCE AT A TIME OF CREATION
        if self.is_new():
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
                    self.leave_without_pay = summary.lop_adjustment or 0
                    self.custom_penalty_leave_days = summary.penalty_leave_days or 0
                    return  # ! Exit if matched
        else:
            # ? Fallback: Manually calculate penalty from Employee Penalty records
            penalties = frappe.get_all(
                "Employee Penalty",
                filters={
                    "employee": self.employee,
                    "company": self.company,
                    "penalty_date": ["between", [self.start_date, self.end_date]],
                    "is_leave_balance_restore":0
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
            # ? IF CUSTOM ADHOC SALARY DETAILS PRESENT ADD IT TO SALARY SLIP
            if payroll_entry.custom_adhoc_salary_details:
                adhoc_component_list = []
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
                            slip_row.custom_is_manually_modified = 1
                            adhoc_component_list.append(slip_row.abbr)

                        elif slip_row and not structure_row:
                            # * Case 2: Manually added (not in structure) → skip
                            continue

                        else:
                            # ! Case 3: Not in structure or slip → add as new
                            self.append(comp_type, {
                                "salary_component": entry.salary_component,
                                "amount": flt(entry.amount),
                                "abbr": component.salary_component_abbr or "",
                                "custom_is_manually_modified": 1
                            })
                            if component.salary_component_abbr:
                                adhoc_component_list.append(component.salary_component_abbr)

                # * Update gross pay and totals
                self.calculate_net_pay(add_adhoc_component = True, adhoc_component_list= adhoc_component_list)
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
                    taxable_earnings += (amount or 0) - (additional_amount or 0)
                    additional_income += (additional_amount or 0)

                    if additional_amount and earning.is_recurring_additional_salary:
                        additional_income += self.get_future_recurring_additional_amount(
                            earning.additional_salary, earning.additional_amount
                        )

                    if earning.deduct_full_tax_on_selected_payroll_date:
                        additional_income_with_full_tax += (additional_amount or 0)

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

                    taxable_earnings -= flt((amount or 0) - (additional_amount or 0))
                    additional_income -= (additional_amount or 0)
                    amount_exempted_from_income_tax += flt(amount - (additional_amount or 0))

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

    @frappe.whitelist()
    def set_totals(self):
        self.gross_pay = 0.0

        if self.salary_slip_based_on_timesheet == 1:
            self.calculate_total_for_salary_slip_based_on_timesheet()
        else:
            self.total_deduction = 0.0
            if hasattr(self, "earnings"):
                for earning in self.earnings:
                    if not earning.do_not_include_in_total and not earning.statistical_component:
                        self.gross_pay += flt(earning.amount, earning.precision("amount"))

            if hasattr(self, "deductions"):
                for deduction in self.deductions:
                    if not deduction.do_not_include_in_total and not deduction.statistical_component:
                        self.total_deduction += flt(deduction.amount, deduction.precision("amount"))

            self.net_pay = (
                flt(self.gross_pay) - flt(self.total_deduction) - flt(self.get("total_loan_repayment"))
            )

        self.set_base_totals()

    def add_leave_balances(self):
        self.set("leave_details", [])

        if frappe.db.get_single_value("Payroll Settings", "show_leave_balances_in_salary_slip"):
            from hrms.hr.doctype.leave_application.leave_application import get_leave_details

            leave_details = get_leave_details(self.employee, self.end_date, True)

            for leave_type, leave_values in leave_details["leave_allocation"].items():
                self.append(
                    "leave_details",
                    {
                        "leave_type": leave_type,
                        "total_allocated_leaves": flt(leave_values.get("total_leaves")),
                        "expired_leaves": flt(leave_values.get("expired_leaves")),
                        "used_leaves": flt(leave_values.get("leaves_taken")),
                        "custom_penalized_leaves": flt(leave_values.get("penalized_leaves")),
                        "pending_leaves": flt(leave_values.get("leaves_pending_approval")),
                        "available_leaves": flt(leave_values.get("remaining_leaves")),
                    },
                )

    def calculate_net_pay(self, skip_tax_breakup_computation: bool = False, add_adhoc_component=False, adhoc_component_list = []):
        #! RESET THE CHANGE TRACKER FOR COMPONENTS
        self._change_components = {}
        self._adhoc_component = {}
        #? COMPARE OLD VS NEW DOCUMENT TO DETECT CHANGED COMPONENTS
        if not self.is_new():
            old_doc = frappe.get_doc(self.doctype, self.name)

            #! FUNCTION TO POPULATE CHANGED COMPONENTS (COMMON FOR EARNINGS & DEDUCTIONS)
            def detect_changes(child_table, old_doc):
                #? STEP 1: TEMPORARY STORAGE FOR MODIFIED ABBRs
                modified_abbrs = set()

                #! STEP 2: INITIAL LOOP — DETECT CHANGES
                for row in self.get(child_table):
                    if row.custom_is_manually_modified:
                        self._change_components[row.name] = row.get("amount")
                        modified_abbrs.add(row.get("abbr"))
                        continue

                    old_row = next((r for r in old_doc.get(child_table) if r.name == row.name), None)
                    if old_row:
                        old_value = old_row.get("amount")
                        new_value = row.get("amount")

                        #? MARK CHANGED ROW AND TRACK ABBR
                        if old_value != new_value and old_row.get("abbr") == row.get("abbr") and not old_row.get('custom_is_manually_modified'):
                            self._change_components[row.name] = row.get("amount")
                            if old_doc.leave_without_pay == self.get("leave_without_pay"):
                                row.custom_is_manually_modified = 1
                                modified_abbrs.add(row.get("abbr"))

                #! STEP 3: SECOND LOOP — MARK ALL ROWS WITH SAME ABBR
                if modified_abbrs:
                    for row in self.get(child_table):
                        if row.get("abbr") in modified_abbrs and not row.custom_is_manually_modified:
                            row.custom_is_manually_modified = 1
                            self._change_components[row.name] = row.get("amount")

            detect_changes("earnings", old_doc)
            detect_changes("deductions", old_doc)

        elif self.is_new() and add_adhoc_component and adhoc_component_list:
            #! FUNCTION TO POPULATE CHANGED COMPONENTS (COMMON FOR EARNINGS & DEDUCTIONS)
            def add_adhoc_component_changes(child_table):
                #? STEP 1: TEMPORARY STORAGE FOR MODIFIED ABBRs
                modified_abbrs = set()
                #! STEP 2: INITIAL LOOP — DETECT CHANGES
                for row in self.get(child_table):
                    if row.custom_is_manually_modified:
                        self._adhoc_component[row.abbr] = row.get("amount")
                        modified_abbrs.add(row.get("abbr"))
                        continue

            add_adhoc_component_changes("earnings")
            add_adhoc_component_changes("deductions")


        #! FUNCTION TO SET GROSS PAY AND BASE GROSS PAY
        def set_gross_pay_and_base_gross_pay():
            self.gross_pay = self.get_component_totals("earnings", depends_on_payment_days=1)
            self.base_gross_pay = flt(
                flt(self.gross_pay) * flt(self.exchange_rate),
                self.precision("base_gross_pay"),
            )

        #! START CALCULATIONS
        if self.salary_structure:
            self.calculate_component_amounts("earnings")

        #? APPLY CHANGES FOR EARNINGS COMPONENTS
        if self._change_components:
            for row in self.get("earnings"):
                if row.get("name") in self._change_components:
                    row.amount = self._change_components[row.get("name")]
                    self.default_data[row.abbr] = flt(row.amount)
                    self.data[row.abbr] = flt(row.amount)

        # ? APPLY CHANGES FOR ADHOC COMPONETS
        if self._adhoc_component:
            for row in self.get("earnings"):
                if row.get("abbr") in self._adhoc_component:
                    row.amount = self._adhoc_component[row.get("abbr")]
                    self.default_data[row.abbr] = flt(row.amount)
                    self.data[row.abbr] = flt(row.amount)

        changes_component_abbr_list = []
        if self._salary_structure_doc and (self._change_components or adhoc_component_list):
            changes_component_abbr_list = frappe.get_all(
                "Salary Detail",
                filters={"parent": self.name, "name": ["in", self._change_components]},
                pluck="abbr",
            )
            if adhoc_component_list:
                changes_component_abbr_list.extend(adhoc_component_list)

        self.evaluate_and_update_structure_formula("earnings", changes_component_abbr_list)

        #! UPDATE REMAINING SUB-PERIOD DETAILS
        if self.payroll_period:
            self.remaining_sub_periods = get_period_factor(
                self.employee,
                self.start_date,
                self.end_date,
                self.payroll_frequency,
                self.payroll_period,
                joining_date=self.joining_date,
                relieving_date=self.relieving_date,
            )[1]

        #! FINAL GROSS CALCULATION
        set_gross_pay_and_base_gross_pay()

        #! DEDUCTION CALCULATION
        if self.salary_structure:
            self.calculate_component_amounts("deductions")


        #? APPLY CHANGES FOR DEDUCTION COMPONENTS
        if self._change_components:
            for row in self.get("deductions"):
                if row.get("name") in self._change_components:
                    row.amount = self._change_components[row.get("name")]
                    self.default_data[row.abbr] = flt(row.amount)
                    self.data[row.abbr] = flt(row.amount)

        # ? APPLY CHANGES FOR ADHOC COMPONETS
        if self._adhoc_component:
            for row in self.get("deductions"):
                if row.get("abbr") in self._adhoc_component:
                    row.amount = self._adhoc_component[row.get("abbr")]
                    self.default_data[row.abbr] = flt(row.amount)
                    self.data[row.abbr] = flt(row.amount)

        # Evaluate deduction structure formula
        self.evaluate_and_update_structure_formula("deductions", changes_component_abbr_list)

        #! FINAL STEPS (UNCHANGED DEFAULT LOGIC)
        set_loan_repayment(self)
        self.set_precision_for_component_amounts()
        self.set_net_pay()

        if not skip_tax_breakup_computation:
            self.compute_income_tax_breakup()

    def evaluate_and_update_structure_formula(self, section_name, changes_component_abbr_list):
        for struct_row in self._salary_structure_doc.get(section_name):
            #! EVALUATE STRUCTURE FORMULA LOGIC (UNCHANGED FROM DEFAULT)
            if struct_row.get("abbr") not in changes_component_abbr_list:
                amount = self.eval_condition_and_formula(struct_row, self.data)
                if struct_row.statistical_component:
                    self.default_data[struct_row.abbr] = flt(amount)
                    if struct_row.depends_on_payment_days:
                        payment_days_amount = (
                            flt(amount) * flt(self.payment_days) / cint(self.total_working_days)
                            if self.total_working_days
                            else 0
                        )
                        self.data[struct_row.abbr] = flt(payment_days_amount, struct_row.precision("amount"))
                else:
                    remove_if_zero_valued = frappe.get_cached_value(
                        "Salary Component", struct_row.salary_component, "remove_if_zero_valued"
                    )

                    default_amount = 0
                    if (
                        amount
                        or (struct_row.amount_based_on_formula and amount is not None)
                        or (not remove_if_zero_valued and amount is not None and not self.data[struct_row.abbr])
                    ):
                        default_amount = self.eval_condition_and_formula(struct_row, self.default_data)
                        self.update_component_row(
                            struct_row,
                            amount,
                            section_name,
                            data=self.data,
                            default_amount=default_amount,
                            remove_if_zero_valued=remove_if_zero_valued,
                        )

    def get_component_totals(self, component_type, depends_on_payment_days=0):
        total = 0.0

        for d in self.get(component_type):
            if not d.do_not_include_in_total and not d.statistical_component:
                amount = flt(d.amount, d.precision("amount"))   
                total += amount

        return total
    
    def verify_duplicate_component_entry(self):
        """
        #! FUNCTION TO DETECT AND MERGE DUPLICATE COMPONENT ENTRIES
        #? SCANS BOTH 'earnings' AND 'deductions' TABLES.
        #? MERGES AMOUNTS OF DUPLICATES AND DISPLAYS A MESSAGE.
        """

        for table in ["earnings", "deductions"]:
            rows = self.get(table)
            if not rows:
                continue

            abbr_map = {}
            duplicates_found = []

            #! STEP 1: GROUP BY ABBR
            for row in rows:
                abbr = row.get("abbr")
                if not abbr:
                    continue

                if abbr not in abbr_map:
                    abbr_map[abbr] = [row]
                else:
                    abbr_map[abbr].append(row)

            #! STEP 2: MERGE DUPLICATES
            for abbr, row_list in abbr_map.items():
                if len(row_list) > 1:
                    #? SUM ALL AMOUNTS
                    total_amount = sum(flt(r.amount) for r in row_list)
                    #? KEEP FIRST ROW
                    main_row = row_list[0]
                    main_row.amount = total_amount
                    main_row.custom_is_manually_modified = 1
                    #? DELETE DUPLICATE ROWS
                    for dup_row in row_list[1:]:
                        self.remove(dup_row)

                    duplicates_found.append(f"Component - {row.salary_component} (merged {len(row_list)} rows)")

            #! STEP 3: DISPLAY MESSAGE
            if duplicates_found:
                frappe.msgprint(
                    msg=(
                        f"<b>Duplicate Components Merged in {table.title()}:</b><br>"
                        + "<br>".join(duplicates_found)
                    ),
                    title="Duplicate Components Found",
                    indicator="blue",
                )
