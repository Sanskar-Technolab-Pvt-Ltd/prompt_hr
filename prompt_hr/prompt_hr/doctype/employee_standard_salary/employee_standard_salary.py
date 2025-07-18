# Copyright (c) 2025, Jignasha Chavda and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _
from hrms.payroll.doctype.salary_slip.salary_slip import SalarySlip, _safe_eval, get_salary_component_data
from frappe.utils import (
    ceil, floor, flt, cint, get_first_day,
    get_last_day, getdate, rounded
)
from datetime import date


class EmployeeStandardSalary(Document):
    def validate(self):
        employee_standard_salary_doc = frappe.get_all("Employee Standard Salary", filters={"employee":self.employee, "docstatus":["!=", 2], "name":["!=", self.name]}, fields = ["name"])
        if employee_standard_salary_doc:
            frappe.throw("Employee Standard Salary already exists for this employee")

    def before_save(self):
        # ? Ensure required fields are present
        if not (self.employee and self.salary_structure_assignment):
            return

        # * Fetch Salary Structure Assignment
        salary_structure_assignment = frappe.get_doc(
            "Salary Structure Assignment", self.salary_structure_assignment
        )

        # ! Skip if Salary Structure not selected
        if not self.salary_structure:
            return

        # * Fetch Salary Structure
        self._salary_structure_doc = frappe.get_doc("Salary Structure", self.salary_structure)

        # * Setup globals for formula evaluation
        self.whitelisted_globals = {
            "int": int,
            "float": float,
            "long": int,
            "round": round,
            "rounded": rounded,
            "date": date,
            "getdate": getdate,
            "get_first_day": get_first_day,
            "get_last_day": get_last_day,
            "ceil": ceil,
            "floor": floor,
        }


        # Clear previous earnings/deductions
        self.earnings = []
        self.deductions = []
        self.employer_contribution = []

        # * Prepare data for evaluation
        self.data, self.default_data = self.get_data_for_eval()
        # * Add earnings
        for row in self._salary_structure_doc.get("earnings", []):
            component = self.create_component_row(row, "earnings")
            if component:
                self.append("earnings", component)
                # * Prepare data for evaluation
                self.data, self.default_data = self.get_data_for_eval()

        # * Add deductions
        for row in self._salary_structure_doc.get("deductions", []):
            component = self.create_component_row(row, "deductions")
            if component:
                self.append("deductions", component)
                # * Prepare data for evaluation
                self.data, self.default_data = self.get_data_for_eval()

        # * Add Employer Contributions
        for row in self._salary_structure_doc.get("custom_employer_contribution", []):
            component = self.create_component_row(row, "employer_contribution")
            if component:
                self.append("employer_contribution", component)
                # * Prepare data for evaluation
                self.data, self.default_data = self.get_data_for_eval()

    def get_data_for_eval(self):
        # * Create merged dict for salary component evaluation
        data = frappe._dict()

        # * Merge Employee data
        if self.employee:
            try:
                employee = frappe.get_doc("Employee", self.employee).as_dict()
                data.update(employee)
            except frappe.DoesNotExistError:
                frappe.throw(f"Employee record not found for {self.employee}")

        # * Merge Salary Structure Assignment data
        if self.salary_structure_assignment:
            try:
                assignment = frappe.get_cached_doc(
                    "Salary Structure Assignment", self.salary_structure_assignment
                ).as_dict()
                data.update(assignment)
            except frappe.DoesNotExistError:
                frappe.throw(f"Salary Structure Assignment not found for {self.salary_structure_assignment}")

        # * Merge fields from current document
        data.update(self.as_dict())
        data.update(SalarySlip.get_component_abbr_map(self))

        # Prepare shallow copy for default data
        default_data = data.copy()
        # * Populate abbreviations
        for key in ("earnings", "deductions", "employer_contribution"):
            for d in self.get(key):
                default_data[d.abbr] = d.default_amount or 0
                data[d.abbr] = d.amount or 0

        # * Set fallback defaults
        data.setdefault("total_working_days", 30)
        data.setdefault("leave_without_pay", 0)
        data.setdefault("custom_lop_days", 0)
        data.setdefault("absent_days", 0)
        data.setdefault("payment_days", 30)
        data.setdefault("custom_penalty_leave_days", 0)
        data.setdefault("custom_overtime", 0)
        return data, default_data

    def create_component_row(self, struct_row, component_type):
        """
        * Build a component row (earning or deduction) from Salary Structure row
        * Exclude formula, avoid statistical components, apply payment_days logic
        """
        amount = 0
        try:
            # Evaluate condition & formula
            condition = (struct_row.condition or "True").strip()
            formula = (struct_row.formula or "0").strip().replace("\r", "").replace("\n", "")
            if _safe_eval(condition, self.whitelisted_globals, self.data):
                amount = flt(
                    _safe_eval(formula, self.whitelisted_globals, self.data),
                    struct_row.precision("amount")
                )

        except Exception as e:
            frappe.throw(
                f"Error while evaluating the Salary Structure '{self.salary_structure}' at row {struct_row.idx}.\n"
                f"Component: {struct_row.salary_component}\n\n"
                f"Error: {e}\n\n"
                f"Hint: Check formula/condition syntax. Only valid Python expressions are allowed."
            )

        # Skip statistical components
        if struct_row.statistical_component:
            self.default_data[struct_row.abbr] = flt(amount)
            if struct_row.depends_on_payment_days:
                payment_days_amount = (
                    flt(amount) * flt(self.data.get("payment_days", 30)) / cint(30)
                )
                self.data[struct_row.abbr] = flt(payment_days_amount, struct_row.precision("amount"))
        # Skip zero-amount components (based on settings)
        remove_if_zero = frappe.get_cached_value(
            "Salary Component", struct_row.salary_component, "remove_if_zero_valued"
        )

        # ! IF CALCULATED AMOUNT IS ZERO AND NOT BASED ON FORMULA,
        # ! USE STATIC AMOUNT DEFINED IN THE SALARY COMPONENT
        if amount == 0 and not struct_row.amount_based_on_formula:
            amount = struct_row.amount
        
        if not (
            amount
            or (struct_row.amount_based_on_formula and amount is not None)
            or (not remove_if_zero and amount is not None)
        ):
            return None

        # Compute default_amount with default data
        try:
            default_amount = _safe_eval(
                (struct_row.formula or "0").strip(), self.whitelisted_globals, self.default_data
            )
        except Exception:
            default_amount = 0
        
        # Return final component row (formula is excluded)
        if not struct_row.statistical_component and not (remove_if_zero and not amount):
            return {
                "salary_component": struct_row.salary_component,
                "abbr": struct_row.abbr,
                "amount": flt(amount),
                "default_amount": flt(default_amount),
                "depends_on_payment_days": struct_row.depends_on_payment_days,
                "precision": struct_row.precision("amount"),
                "statistical_component": struct_row.statistical_component,
                "remove_if_zero_valued": remove_if_zero,
                "amount_based_on_formula": struct_row.amount_based_on_formula,
                "condition": struct_row.condition,
                "variable_based_on_taxable_salary": struct_row.variable_based_on_taxable_salary,
                "is_flexible_benefit": struct_row.is_flexible_benefit,
                "do_not_include_in_total": struct_row.do_not_include_in_total,
                "is_tax_applicable": struct_row.is_tax_applicable,
                "formula":formula
            }
