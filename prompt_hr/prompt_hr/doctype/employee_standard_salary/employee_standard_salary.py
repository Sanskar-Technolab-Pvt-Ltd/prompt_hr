# Copyright (c) 2025, Jignasha Chavda and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from hrms.payroll.doctype.salary_slip.salary_slip import SalarySlip
from frappe.utils import (
    ceil,
    floor,
    get_first_day,
    get_last_day,
    getdate,
    rounded,
)
from datetime import date


class EmployeeStandardSalary(Document):
    def before_save(self):
        # Check if required fields exist
        if not (self.employee and self.salary_structure_assignment):
            return

        # Get salary structure assignment data
        salary_structure_assignment = frappe.get_doc(
            "Salary Structure Assignment", self.salary_structure_assignment
        )
        
        if self.salary_structure:
            salary_structure = frappe.get_doc("Salary Structure", self.salary_structure)
            
            # Setup whitelisted globals for formula evaluation
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
            
            if salary_structure:
                data = self.get_data_for_eval()
                self.earnings = []
                self.deductions = []
                
                # Process earnings components
                for comp in salary_structure.earnings:
                    comp_dict = comp.as_dict().copy()
                    comp_dict.pop("name", None)
                    comp_dict.pop("parent", None)
                    comp_dict.pop("parentfield", None)
                    comp_dict.pop("parenttype", None)
                    self.append("earnings", comp_dict)

                # Process deductions components
                for comp in salary_structure.deductions:
                    comp_dict = comp.as_dict().copy()
                    comp_dict.pop("name", None)
                    comp_dict.pop("parent", None)
                    comp_dict.pop("parentfield", None)
                    comp_dict.pop("parenttype", None)
                    self.append("deductions", comp_dict)
				
                # Calculate earning amounts
                for earning in self.earnings:
                    if not earning.amount:
                        earning.amount = SalarySlip.eval_condition_and_formula(self, earning, data)
                    
				# Calculate deduction amounts
                for deduction in self.deductions:
                    if not deduction.amount:
                        deduction.amount = SalarySlip.eval_condition_and_formula(self, deduction, data)

    def get_data_for_eval(self):
        """Get data context for formula evaluation"""
        data = frappe._dict()

        # Get employee data
        employee = frappe.get_cached_doc("Employee", self.employee).as_dict()
        data.update(employee)

        # Get salary structure assignment data
        if self.salary_structure_assignment:
            salary_structure_assignment = frappe.get_cached_doc(
                "Salary Structure Assignment", self.salary_structure_assignment
            ).as_dict()
            data.update(salary_structure_assignment)

        # Add current document data
        data.update(self.as_dict())

        return data

