import frappe

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
    