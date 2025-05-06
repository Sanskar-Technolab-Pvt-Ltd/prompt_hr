import frappe


# ? ON UPDATE CONTROLLER METHOD
# ! prompt_hr.py.payroll_entry.on_update
def before_save(doc, method):

    # ? SET NEW JOINEE COUNT
    set_new_joinee_count(doc)

    # ? SET EMPLOYEE COUNT AND APPEND IN PENDING FNF TABLE
    append_exit_employees(doc)

    # ? APPEND PENDING LEAVE APPLICATIONS
    append_pending_leave_approvals(doc)


# ? METHOD TO SET EMPLOYEE COUNT AND APPEND IN PENDING FNF TABLE
# ! prompt_hr.py.payroll_entry.append_exit_employees
def append_exit_employees(doc):
    # ? FETCH EMPLOYEES WHO HAVE A RELIEVING DATE BETWEEN THE START AND END DATES
    exit_employees = frappe.db.get_all(
        "Employee",
        filters={
            "relieving_date": ["between", [doc.start_date, doc.end_date]],
        },
        fields=["name", "employee_name"],
        pluck="name",
    )

    # ? FETCH FULL AND FINAL STATEMENTS FOR THESE EMPLOYEES
    fnf_records = frappe.get_all(
        "Full and Final Statement",
        filters={"employee": ["in", exit_employees]},
        fields=["employee", "name"],
    )

    # ? SEPARATE EMPLOYEE NAMES AND FNF RECORD NAMES
    full_and_final_statement_employees = [record["employee"] for record in fnf_records]
    full_and_final_statement_record_names = {
        record["employee"]: record["name"] for record in fnf_records
    }

    # ? SET EMPLOYEE COUNT
    doc.custom_exit_employees_count = len(exit_employees)
    doc.set("custom_pending_fnf_details", [])

    # ? APPEND IN PENDING FNF TABLE
    for employee in exit_employees:
        # ? FETCH EMPLOYEE'S FULL NAME USING THE ID
        employee_data = frappe.db.get_value("Employee", employee, "employee_name")
        employee_full_name = employee_data if employee_data else "Unknown"

        # ? CHECK IF THE EMPLOYEE HAS A FULL AND FINAL STATEMENT PROCESSED
        is_fnf_processed = 1 if employee in full_and_final_statement_employees else 0

        # ? FETCH THE F&F RECORD NAME FOR THE EMPLOYEE IF AVAILABLE
        fnf_record = full_and_final_statement_record_names.get(employee, None)

        # APPEND TO THE CHILD TABLE WITH EMPLOYEE, FULL NAME, FNF STATUS AND FNF RECORD
        doc.append(
            "custom_pending_fnf_details",
            {
                "employee": employee,
                "employee_name": employee_full_name,
                "is_fnf_processed": is_fnf_processed,
                "fnf_record": fnf_record,
            },
        )


# ? METHOD TO SET NEW JOINEE COUNT
# ! prompt_hr.py.payroll_entry.set_new_joinee_count
def set_new_joinee_count(doc):
    new_joinees = frappe.db.get_all(
        "Employee",
        filters={
            "status": "Active",
            "date_of_joining": ["between", [doc.start_date, doc.end_date]],
        },
        fields=["name"],
    )
    doc.custom_new_joinee_count = len(new_joinees)


# ? METHOD TO APPEND PENDING LEAVE APPLICATIONS
# ! prompt_hr.py.payroll_entry.append_pending_leave_approvals
def append_pending_leave_approvals(doc):
    # ? FETCH ELIGIBLE EMPLOYEES BASED ON PAYROLL EMPLOYEE DETAIL AND APPLY DATE RANGE FILTER
    eligible_employee_ids = frappe.db.get_all(
        "Payroll Employee Detail",  # Assuming this DocType stores payroll employee details
        filters={
            "parent": doc.name,  # Assuming the payroll entry's name is linked in the employee detail
        },
        fields=["employee"],  # Fetch employee names linked to the payroll entry
        pluck="employee",
    )



    # ? FETCH LEAVE APPLICATIONS WITH STATUS "Open" FOR THESE ELIGIBLE EMPLOYEES
    # ? AND WHERE LEAVE PERIOD OVERLAPS WITH THE PAYROLL PERIOD
    open_leave_applications = frappe.db.get_all(
        "Leave Application",
        filters={
            "status": "Open",
            "employee": ["in", eligible_employee_ids],
            "from_date": ["between", [doc.start_date, doc.end_date]],
        },
        fields=["employee", "from_date", "to_date", "status", "name"],
    )

    # ? APPEND PENDING LEAVE APPLICATION DETAILS IN TABLE
    doc.set("custom_pending_leave_approval", [])

    for leave_application in open_leave_applications:
        # ? FETCH EMPLOYEE NAME USING THE EMPLOYEE ID
        employee_name = frappe.db.get_value("Employee", leave_application["employee"], "employee_name")
        
        doc.append(
            "custom_pending_leave_approval",
            {
                "employee": leave_application["employee"],
                "employee_name": employee_name,
                "from_date": leave_application["from_date"],
                "to_date": leave_application["to_date"],
                "status": leave_application["status"],
                "leave_application": leave_application["name"],
            },
        )
