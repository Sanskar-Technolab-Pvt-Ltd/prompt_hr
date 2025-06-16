import frappe


# ? ON UPDATE CONTROLLER METHOD
# ! prompt_hr.py.payroll_entry.on_update
def on_update(doc, method):

    # ? SET NEW JOINEE COUNT
    set_new_joinee_count(doc)

    # ? SET EMPLOYEE COUNT AND APPEND IN PENDING FNF TABLE
    append_exit_employees(doc)

    # ? APPEND PENDING LEAVE APPLICATIONS
    append_pending_leave_approvals(doc)

    # ? APPEND EMPLOYEES MISSING PF/ESI DETAILS
    append_employees_with_incomplete_payroll_details(doc)

    # ? APPEND EMPLOYEES MISSING BANK DETAILS
    append_employees_with_incomplete_bank_details(doc)


# ? METHOD TO SET EMPLOYEE COUNT AND APPEND IN PENDING FNF TABLE
# ! prompt_hr.py.payroll_entry.append_exit_employees
def append_exit_employees(doc):

    # ? FETCH ELIGIBLE EMPLOYEES BASED ON PAYROLL EMPLOYEE DETAIL AND APPLY DATE RANGE FILTER
    eligible_employees = get_eligible_employees(doc.name)

    # ? FETCH EMPLOYEES WHO HAVE A RELIEVING DATE BETWEEN THE START AND END DATES
    exit_employees = frappe.db.get_all(
        "Employee",
        filters={
            "name": ["in", eligible_employees],
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

        # ? APPEND TO THE CHILD TABLE WITH EMPLOYEE, FULL NAME, FNF STATUS AND FNF RECORD
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

    # ? FETCH ELIGIBLE EMPLOYEES BASED ON PAYROLL EMPLOYEE DETAIL AND APPLY DATE RANGE FILTER
    eligible_employees = get_eligible_employees(doc.name)

    new_joinees = frappe.db.get_all(
        "Employee",
        filters={
            "name": ["in", eligible_employees],
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
    eligible_employee_ids = get_eligible_employees(doc.name)

    # ? FETCH LEAVE APPLICATIONS WITH STATUS "Open" FOR THESE ELIGIBLE EMPLOYEES
    # ? AND WHERE LEAVE PERIOD OVERLAPS WITH THE PAYROLL PERIOD
    open_leave_applications = frappe.db.get_all(
        "Leave Application",
        filters={
            "workflow_state": ["in", ["Approved", "Pending"]],
            "employee": ["in", eligible_employee_ids],
            "from_date": ["between", [doc.start_date, doc.end_date]],
        },
        fields=["employee", "from_date", "to_date", "status", "name"],
    )

    # ? APPEND PENDING LEAVE APPLICATION DETAILS IN TABLE
    doc.set("custom_pending_leave_approval", [])
    # * Process each open leave application
    for leave_application in open_leave_applications:
        employee = leave_application["employee"]
        leave_app_name = leave_application["name"]
        status = leave_application["status"]

        # * Fetch employee name from Employee master
        employee_name = frappe.db.get_value("Employee", employee, "employee_name")

        # ? Check if record already exists in child table
        existing = frappe.db.get_value(
            "Pending Leave Approval",
            {
                "leave_application": leave_app_name,
                "parent": doc.name,
                "parenttype": doc.doctype,
                "parentfield": "custom_pending_leave_approval",
            },
            ["name", "status"],
            as_dict=True
        )

        if not existing:
            # * Append to parent DocType's child table
            doc.append(
                "custom_pending_leave_approval",
                {
                    "employee": employee,
                    "employee_name": employee_name,
                    "from_date": leave_application["from_date"],
                    "to_date": leave_application["to_date"],
                    "status": status if status == "Approved" else "Open",
                    "leave_application": leave_app_name,
                }
            )

            # * Insert into child DocType directly (Pending Leave Approval)
            frappe.get_doc({
                "doctype": "Pending Leave Approval",
                "parent": doc.name,
                "parenttype": doc.doctype,
                "parentfield": "custom_pending_leave_approval",
                "employee": employee,
                "employee_name": employee_name,
                "from_date": leave_application["from_date"],
                "to_date": leave_application["to_date"],
                "status": status if status == "Approved" else "Open",
                "leave_application": leave_app_name,
            }).insert(ignore_permissions=True)

        # * Update status if already exists and status is different
        elif existing.status != status:
            # ! Sync status change with DB
            frappe.db.set_value("Pending Leave Approval", existing.name, "status", status)


# ? FUNCTION TO FETCH ELIGIBLE EMPLOYEES BASED ON PAYROLL EMPLOYEE DETAIL AND APPLY DATE RANGE FILTER
def get_eligible_employees(name):
    return frappe.db.get_all(
        "Payroll Employee Detail",  # Assuming this DocType stores payroll employee details
        filters={
            "parent": name,  # Assuming the payroll entry's name is linked in the employee detail
        },
        fields=["employee"],  # Fetch employee names linked to the payroll entry
        pluck="employee",
    )

# ? WHITELISTED FUNCTION TO HANDLE LEAVE ACTIONS
@frappe.whitelist()
def handle_leave_action(docname, doctype, action, leaves):
    # ! Validate action
    if action not in ("approve", "reject", "confirm"):
        frappe.throw("Invalid action")

    # * Parse JSON string to list
    leaves = frappe.parse_json(leaves)
    updated_rows = []

    # * Get parent document (e.g., Payroll Entry)
    doc = frappe.get_doc(doctype, docname)

    # * Loop through each leave application
    for rowname in leaves:
        row = frappe.get_doc("Leave Application", rowname)

        # ? Skip if already in desired workflow state
        if action == "approve" and row.workflow_state in ("Approved", "Confirmed"):
            continue
        elif action == "reject" and row.workflow_state == "Rejected":
            continue
        elif action == "confirm" and row.workflow_state == "Confirmed":
            continue

        # * Apply workflow changes
        if action == "approve":
            row.workflow_state = "Approved"

        elif action == "reject":
            row.workflow_state = "Rejected"
            # * Submit if draft
            if row.docstatus == 0:
                row.submit()

        elif action == "confirm":
            row.workflow_state = "Confirmed"
            row.submit()

        # * Save leave application with updated state
        row.save(ignore_permissions=True)

        # * Track updated leave applications
        updated_rows.append({
            "leave_application": rowname,
            "workflow_state": row.workflow_state
        })

        # * Update child row in parent: Pending Leave Approval
        current_status = row.workflow_state
        existing = frappe.db.get_value(
            "Pending Leave Approval",
            {
                "leave_application": rowname,
                "parent": doc.name,
                "parenttype": doc.doctype,
                "parentfield": "custom_pending_leave_approval",
            },
            ["name", "status"],
            as_dict=True
        )

        # * Update the child row's status if found
        if existing:
            frappe.db.set_value("Pending Leave Approval", existing.name, "status", current_status)

    # * Refresh child table
    append_pending_leave_approvals(doc)

    # * Save and commit parent document to reflect child changes
    doc.save(ignore_permissions=True)
    frappe.db.commit()

    # * Return list of updated leave applications
    return updated_rows

# ? METHOD TO APPEND EMPLOYEES MISSING PF/ESI DETAILS
# ! prompt_hr.py.payroll_entry.append_employees_with_incomplete_payroll_details
def append_employees_with_incomplete_payroll_details(doc):
    # * Clear existing entries before appending
    frappe.db.delete("Remaining Payroll Details", {
        "parent": doc.name,
        "parenttype": doc.doctype,
        "parentfield": "custom_remaining_payroll_details"
    })

    doc.set("custom_remaining_payroll_details", [])

    # * Get all employees linked to the payroll entry
    all_employees = frappe.get_all(
        "Payroll Employee Detail",
        filters={"parent": doc.name},
        fields=["employee"]
    )

    for employee in all_employees:
        employee_doc = frappe.get_doc("Employee", employee.employee)

        # * Skip if no consent or if details are already available
        needs_pf = employee_doc.custom_pf_consent and not employee_doc.custom_uan_number
        needs_esi = employee_doc.custom_eps_contribution and not employee_doc.custom_esi_number

        if not (needs_pf or needs_esi):
            continue

        # ? Check if already exists in the child table
        existing = frappe.db.exists(
            "Remaining Payroll Details",
            {
                "employee": employee_doc.name,
                "parent": doc.name,
                "parenttype": doc.doctype,
                "parentfield": "custom_remaining_payroll_details",
            }
        )

        if not existing:
            # * Append to parent doc child table
            doc.append(
                "custom_remaining_payroll_details",
                {
                    "employee": employee_doc.name,
                }
            )

            # * Insert into separate child DocType directly
            frappe.get_doc({
                "doctype": "Remaining Payroll Details",
                "parent": doc.name,
                "parenttype": doc.doctype,
                "parentfield": "custom_remaining_payroll_details",
                "employee": employee_doc.name,
            }).insert(ignore_permissions=True)

    # * Refresh from DB so changes reflect immediately in memory
    frappe.db.commit()
    doc.reload()


# ? METHOD TO APPEND EMPLOYEES WITH INCOMPLETE BANK DETAILS
# ! prompt_hr.py.payroll_entry.append_employees_with_incomplete_bank_details
def append_employees_with_incomplete_bank_details(doc):
    # * Clear existing entries before appending
    frappe.db.delete("Remaining Bank Details", {
        "parent": doc.name,
        "parenttype": doc.doctype,
        "parentfield": "custom_remaining_bank_details"
    })

    doc.set("custom_remaining_bank_details", [])

    # * Get all employees linked to the payroll entry
    all_employees = frappe.get_all(
        "Payroll Employee Detail",
        filters={"parent": doc.name},
        fields=["employee"]
    )

    for employee in all_employees:
        employee_doc = frappe.get_doc("Employee", employee.employee)

        # * Skip if no consent or if details are already available
        bank_name = employee_doc.bank_name
        bank_ac_no = employee_doc.bank_ac_no
        ifsc_code = employee_doc.ifsc_code

        if (bank_name and bank_ac_no and ifsc_code):
            continue

        # ? Check if already exists in the child table
        existing = frappe.db.exists(
            "Remaining Bank Details",
            {
                "employee": employee_doc.name,
                "parent": doc.name,
                "parenttype": doc.doctype,
                "parentfield": "custom_remaining_bank_details",
            }
        )

        if not existing:
            # * Append to parent doc child table
            doc.append(
                "custom_remaining_bank_details",
                {
                    "employee": employee_doc.name,
                }
            )

            # * Insert into separate child DocType directly
            frappe.get_doc({
                "doctype": "Remaining Bank Details",
                "parent": doc.name,
                "parenttype": doc.doctype,
                "parentfield": "custom_remaining_bank_details",
                "employee": employee_doc.name,
            }).insert(ignore_permissions=True)

    # * Refresh from DB so changes reflect immediately in memory
    frappe.db.commit()
    doc.reload()
