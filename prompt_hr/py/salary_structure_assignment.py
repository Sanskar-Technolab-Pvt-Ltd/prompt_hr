import frappe
from frappe.utils import getdate, add_months

def update_employee_ctc(doc, method=None):
    """
    Update the employee's CTC/Gross Salary based on the salary structure assignment.
    """
    if doc.employee:
        employee = frappe.get_doc("Employee", doc.employee)
        if employee.custom_salary_structure_based_on == "CTC Based":
            employee.db_set("ctc",doc.base)
        elif employee.custom_salary_structure_based_on == "Gross Based":
            employee.db_set("custom_gross_salary" ,doc.base)

    employee_standard_salary = frappe.get_all("Employee Standard Salary", filters={"employee":doc.employee, "docstatus":["!=",2]})
    if employee_standard_salary:
        for es in employee_standard_salary:
            es_doc = frappe.get_doc("Employee Standard Salary", es.name)
            es_doc.salary_structure_assignment = doc.name
            es_doc.salary_structure = doc.salary_structure
            es_doc.save(ignore_permissions=True)
    else:
        employee_standard_salary = frappe.new_doc("Employee Standard Salary")
        employee_standard_salary.employee = doc.employee
        employee_standard_salary.salary_structure_assignment = doc.name
        employee_standard_salary.salary_structure = doc.salary_structure
        employee_standard_salary.save(ignore_permissions=True)

def on_cancel(doc, method=None):
    employee_standard_salary = frappe.get_all("Employee Standard Salary", filters={"employee":doc.employee, "docstatus":["!=",2]})
    if employee_standard_salary:
        for es in employee_standard_salary:
            es_doc = frappe.get_doc("Employee Standard Salary", es.name)
            ssa = frappe.get_all("Salary Structure Assignment", filters={"employee": doc.employee, "docstatus":1, "name": ["!=", es_doc.salary_structure_assignment]}, fields=["name", "salary_structure"])
            if ssa:
                es_doc.salary_structure_assignment = ssa[0].name
                es_doc.salary_structure = ssa[0].salary_structure
                es_doc.save(ignore_permissions=True)
            else:
                frappe.delete_doc("Employee Standard Salary", es_doc.name)
            frappe.db.commit()

def update_arrear_details(doc, method=None):
    """
    Populate arrear details between Effective Date and Posting Date (exclusive).
    Adds or updates monthly arrear rows, removes outdated ones, and computes the total arrear amount.
    """

    # * Skip if Required fields Not exist
    if not (doc.from_date and doc.custom_posting_date and doc.base):
        doc.custom_salary_arrear_details = []
        doc.custom_total_arrear_payable = 0
        return

    start_date = getdate(doc.from_date)
    end_date = getdate(doc.custom_posting_date)

    # * Skip if invalid or same month
    if start_date >= end_date or (start_date.month == end_date.month and start_date.year == end_date.year):
        doc.custom_salary_arrear_details = []
        doc.custom_total_arrear_payable = 0
        return

    # * Create dict of Existing Rows
    existing_rows = {d.arrear_month: d for d in doc.custom_salary_arrear_details}
    valid_months = set()
    current_date = start_date

    # * Update rows only if from_date or base or custom_posting_date changed
    if (
        doc.has_value_changed("from_date") or 
        doc.has_value_changed("base") or 
        doc.has_value_changed("custom_posting_date")
    ):
        while current_date < end_date:
            arrear_month_str = current_date.strftime("%B %Y")
            valid_months.add(arrear_month_str)

            # * Fetch latest SSA before current date
            ssa = frappe.get_all(
                "Salary Structure Assignment",
                filters={
                    "employee": doc.employee,
                    "name": ["!=", doc.name],
                    "from_date": ["<", start_date],
                    "docstatus": 1,
                },
                fields=["base"],
                order_by="from_date desc",
                limit=1
            )
            ssa_base = ssa[0].base if ssa else 0
            arrear_amount = doc.base - ssa_base

            if arrear_amount > 0:
                # * Update existing row or append new one
                if arrear_month_str in existing_rows:
                    existing_rows[arrear_month_str].arrear_amount = arrear_amount
                else:
                    doc.append("custom_salary_arrear_details", {
                        "arrear_month": arrear_month_str,
                        "arrear_amount": arrear_amount
                    })
            else:
                # * Remove row if amount is not positive
                if arrear_month_str in existing_rows:
                    doc.remove(existing_rows[arrear_month_str])

            current_date = add_months(current_date, 1)

            # ! Prevent potential infinite loop by checking if next loop would hit or exceed the end month
            if current_date.month == end_date.month and current_date.year == end_date.year:
                break

        # * Remove rows that are outside the new date range
        for month_str in list(existing_rows):
            if month_str not in valid_months:
                doc.remove(existing_rows[month_str])

    # * Recalculate total
    doc.custom_total_arrear_payable = sum(
        row.arrear_amount for row in doc.custom_salary_arrear_details
    )
