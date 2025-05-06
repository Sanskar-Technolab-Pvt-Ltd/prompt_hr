

import frappe

# ? ON UPDATE CONTROLLER METHOD
# ! prompt_hr.py.payroll_entry.on_update
def before_save(doc, method):

    # ? SET NEW JOINEE COUNT
    set_new_joinee_count(doc)

    # ? SET EMPLOYEE COUNT AND APPEND IN PENDING FNF TABLE
    append_exit_employees(doc)

# ? METHOD TO SET EMPLOYEE COUNT AND APPEND IN PENDING FNF TABLE
# ! prompt_hr.py.payroll_entry.append_exit_employees
def append_exit_employees(doc):
    # ? FETCH EMPLOYEES WHO HAVE A RELIEVING DATE BETWEEN THE START AND END DATES
    exit_employees = frappe.db.get_all(
        "Employee",
        filters={
            "relieving_date": ["between", [doc.start_date, doc.end_date]],
        },
        fields=["name", "employee_name"],  # FETCH EMPLOYEE NAME AND FULL NAME
        pluck="name"
    )

    # ? FETCH FULL AND FINAL STATEMENTS FOR THESE EMPLOYEES
    fnf_records = frappe.get_all(
        "Full and Final Statement",
        filters={
            "employee": ["in", exit_employees]
        },
        fields=["employee", "name"],  # FETCH EMPLOYEE AND FNF RECORD NAME
    )

    # ? SEPARATE EMPLOYEE NAMES AND FNF RECORD NAMES
    full_and_final_statement_employees = [record["employee"] for record in fnf_records]  # LIST OF EMPLOYEE NAMES
    full_and_final_statement_record_names = {record["employee"]: record["name"] for record in fnf_records}  # MAP EMPLOYEE TO FNF RECORD NAME

    # ? SET EMPLOYEE COUNT
    doc.custom_exit_employees_count = len(exit_employees)
    doc.set("custom_pending_fnf_details", [])  # CLEAR EXISTING RECORDS IN THE CHILD TABLE

    # ? APPEND IN PENDING FNF TABLE
    for employee in exit_employees:
        # ? FETCH EMPLOYEE'S FULL NAME USING THE ID
        employee_data = frappe.db.get_value("Employee", employee, "employee_name")  # GET EMPLOYEE FULL NAME
        employee_full_name = employee_data if employee_data else "Unknown"

        # ? CHECK IF THE EMPLOYEE HAS A FULL AND FINAL STATEMENT PROCESSED
        is_fnf_processed = 1 if employee in full_and_final_statement_employees else 0
        
        # ? FETCH THE F&F RECORD NAME FOR THE EMPLOYEE IF AVAILABLE
        fnf_record = full_and_final_statement_record_names.get(employee, None)

        print(f"Employee: {employee}, Full Name: {employee_full_name}, FNF Processed: {is_fnf_processed}, FNF Record: {fnf_record}")

        # ? APPEND TO THE CHILD TABLE WITH EMPLOYEE, FULL NAME, FNF STATUS AND FNF RECORD
        doc.append("custom_pending_fnf_details", {
            "employee": employee,
            "employee_name": employee_full_name,  # STORE EMPLOYEE'S FULL NAME
            "is_fnf_processed": is_fnf_processed,
            "fnf_record": fnf_record  # STORE F&F RECORD NAME
        })

    return len(exit_employees)


# ? METHOD TO SET NEW JOINEE COUNT
# ! prompt_hr.py.payroll_entry.set_new_joinee_count
def set_new_joinee_count(doc):
    new_joinees = frappe.db.get_all(
        "Employee",
        filters={
            "status": "Active",
            "date_of_joining": ["between", [doc.start_date, doc.end_date]],
        },
        fields=["name"]
    )
    doc.custom_new_joinee_count = len(new_joinees)

    return len(new_joinees)
