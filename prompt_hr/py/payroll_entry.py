import frappe
from frappe.utils import cint
from dateutil.relativedelta import relativedelta
from frappe.utils.xlsxutils import make_xlsx, read_xlsx_file_from_attached_file
from frappe.utils.response import build_response
from frappe import _
import traceback


# ? ON UPDATE CONTROLLER METHOD
# ! prompt_hr.py.payroll_entry.before_save
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

    if not doc.custom_lop_summary:
        # ? APPEND LOP SUMMARY
        append_lop_summary(doc)

    frappe.db.commit()
    doc.reload()

def append_exit_employees(doc):
    # ? FETCH ELIGIBLE EMPLOYEES BASED ON PAYROLL EMPLOYEE DETAIL
    eligible_employees = get_eligible_employees(doc.name)

    if not eligible_employees:
        # ? CLEAR EXISTING CHILD TABLE
        frappe.db.delete("Pending FnF Details", {"parent": doc.name})
        frappe.db.set_value("Payroll Entry", doc.name, "custom_exit_employees_count", 0)
        return

    # ? FETCH EMPLOYEES WHO HAVE RELIEVING DATE BETWEEN START AND END DATES
    exit_employees = frappe.get_all(
        "Employee",
        filters={
            "name": ["in", eligible_employees],
            "relieving_date": ["between", [doc.start_date, doc.end_date]],
        },
        fields=["name", "employee_name"],
    )

    exit_employee_ids = [emp["name"] for emp in exit_employees]

    # ? FETCH FULL AND FINAL STATEMENTS FOR THESE EMPLOYEES
    fnf_records = frappe.get_all(
        "Full and Final Statement",
        filters={"employee": ["in", exit_employee_ids]},
        fields=["employee", "name"],
    )

    # ? MAP EMPLOYEE → FNF RECORD
    fnf_record_map = {record["employee"]: record["name"] for record in fnf_records}
    fnf_employees = set(fnf_record_map.keys())

    # ? SET EMPLOYEE COUNT
    frappe.db.set_value(
        "Payroll Entry", doc.name, "custom_exit_employees_count", len(exit_employee_ids)
    )

    # ? CLEAR OLD CHILD ROWS
    frappe.db.delete("Pending FnF Details", {"parent": doc.name})

    # ? INSERT CHILD RECORDS USING get_doc().insert()
    for emp in exit_employees:
        frappe.get_doc(
            {
                "doctype": "Pending FnF Details",
                "parent": doc.name,
                "parenttype": "Payroll Entry",
                "parentfield": "custom_pending_fnf_details",
                "employee": emp["name"],
                "employee_name": emp.get("employee_name") or "Unknown",
                "is_fnf_processed": 1 if emp["name"] in fnf_employees else 0,
                "fnf_record": fnf_record_map.get(emp["name"]),
            }
        ).insert(ignore_permissions=True)


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
        pluck="",
    )
    frappe.db.set_value(
        "Payroll Entry", doc.name, "custom_new_joinee_count", len(new_joinees)
    )


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
            "docstatus": ["!=", 2],
            "workflow_state": ["in", ["Pending"]],
            "employee": ["in", eligible_employee_ids],
            "from_date": ["between", [doc.start_date, doc.end_date]],
            "status" : ["in", ["Open"]]
        },
        fields=["employee", "from_date", "to_date", "status", "name", "workflow_state"],
    )
    # * Clear existing entries before appending
    frappe.db.delete(
        "Pending Leave Approval",
        {
            "parent": doc.name,
            "parenttype": doc.doctype,
            "parentfield": "custom_pending_leave_approval",
        },
    )

    # ? APPEND PENDING LEAVE APPLICATION DETAILS IN TABLE
    doc.set("custom_pending_leave_approval", [])
    # * Process each open leave application
    for leave_application in open_leave_applications:
        employee = leave_application["employee"]
        leave_app_name = leave_application["name"]
        status = leave_application["workflow_state"]

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
            as_dict=True,
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
                    "status": status,
                    "leave_application": leave_app_name,
                },
            )

            # * Insert into child DocType directly (Pending Leave Approval)
            frappe.get_doc(
                {
                    "doctype": "Pending Leave Approval",
                    "parent": doc.name,
                    "parenttype": doc.doctype,
                    "parentfield": "custom_pending_leave_approval",
                    "employee": employee,
                    "employee_name": employee_name,
                    "from_date": leave_application["from_date"],
                    "to_date": leave_application["to_date"],
                    "status": status,
                    "leave_application": leave_app_name,
                }
            ).insert(ignore_permissions=True)

        # * Update status if already exists and status is different
        elif existing.status != status:
            # ! Sync status change with DB
            frappe.db.set_value(
                "Pending Leave Approval", existing.name, "status", status
            )


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
    if action not in ("approve", "reject"):
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
        if action == "approve" and row.workflow_state in ("Approved"):
            continue
        elif action == "reject" and row.workflow_state == "Rejected":
            continue

        # * Apply workflow changes
        if action == "approve":
            row.workflow_state = "Approved"
            # * Submit if draft
            if row.docstatus == 0:
                row.submit()

        elif action == "reject":
            row.workflow_state = "Rejected"
            # * Submit if draft
            if row.docstatus == 0:
                row.submit()


        # * Save leave application with updated state
        row.save(ignore_permissions=True)

        # * Track updated leave applications
        updated_rows.append(
            {"leave_application": rowname, "workflow_state": row.workflow_state}
        )

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
            as_dict=True,
        )

        # * Update the child row's status if found
        if existing:
            frappe.db.set_value(
                "Pending Leave Approval", existing.name, "status", current_status
            )

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
    frappe.db.delete(
        "Remaining Payroll Details",
        {
            "parent": doc.name,
            "parenttype": doc.doctype,
            "parentfield": "custom_remaining_payroll_details",
        },
    )

    doc.set("custom_remaining_payroll_details", [])

    # * Get all employees linked to the payroll entry
    all_employees = frappe.get_all(
        "Payroll Employee Detail", filters={"parent": doc.name}, fields=["employee"]
    )

    for employee in all_employees:
        employee_doc = frappe.get_doc("Employee", employee.employee)

        # * Skip if no consent or if details are already available
        needs_pf = employee_doc.custom_pf_consent and not employee_doc.custom_uan_number
        needs_esi = (
            employee_doc.custom_esi_consent and not employee_doc.custom_esi_number
        )

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
            },
        )

        if not existing:
            # * Append to parent doc child table
            doc.append(
                "custom_remaining_payroll_details",
                {
                    "employee": employee_doc.name,
                },
            )

            # * Insert into separate child DocType directly
            frappe.get_doc(
                {
                    "doctype": "Remaining Payroll Details",
                    "parent": doc.name,
                    "parenttype": doc.doctype,
                    "parentfield": "custom_remaining_payroll_details",
                    "employee": employee_doc.name,
                }
            ).insert(ignore_permissions=True)


# ? METHOD TO APPEND EMPLOYEES WITH INCOMPLETE BANK DETAILS
# ! prompt_hr.py.payroll_entry.append_employees_with_incomplete_bank_details
def append_employees_with_incomplete_bank_details(doc):
    # * Clear existing entries before appending
    frappe.db.delete(
        "Remaining Bank Details",
        {
            "parent": doc.name,
            "parenttype": doc.doctype,
            "parentfield": "custom_remaining_bank_details",
        },
    )

    doc.set("custom_remaining_bank_details", [])

    # * Get all employees linked to the payroll entry
    all_employees = frappe.get_all(
        "Payroll Employee Detail", filters={"parent": doc.name}, fields=["employee"]
    )

    for employee in all_employees:
        employee_doc = frappe.get_doc("Employee", employee.employee)

        # * Skip if no consent or if details are already available
        bank_name = employee_doc.bank_name
        bank_ac_no = employee_doc.bank_ac_no
        ifsc_code = employee_doc.ifsc_code

        if employee_doc.salary_mode != "Bank" or (
            bank_name and bank_ac_no and ifsc_code
        ):
            continue

        # ? Check if already exists in the child table
        existing = frappe.db.exists(
            "Remaining Bank Details",
            {
                "employee": employee_doc.name,
                "parent": doc.name,
                "parenttype": doc.doctype,
                "parentfield": "custom_remaining_bank_details",
            },
        )

        if not existing:
            # * Append to parent doc child table
            doc.append(
                "custom_remaining_bank_details",
                {
                    "employee": employee_doc.name,
                },
            )

            # * Insert into separate child DocType directly
            frappe.get_doc(
                {
                    "doctype": "Remaining Bank Details",
                    "parent": doc.name,
                    "parenttype": doc.doctype,
                    "parentfield": "custom_remaining_bank_details",
                    "employee": employee_doc.name,
                }
            ).insert(ignore_permissions=True)


@frappe.whitelist()
def get_actual_lop_days(employee, start_date):
    if isinstance(start_date, str):
        start_date = frappe.utils.getdate(start_date)

    # Calculate the first and last day of the previous month
    previous_month_start = (
        start_date.replace(day=1) - relativedelta(months=1)
    ).replace(day=1)
    previous_month_end = (
        previous_month_start.replace(day=1)
        + relativedelta(months=1)
        - relativedelta(days=1)
    )

    # * Fetch salary slip of Last Month
    last_month_salary_slip = frappe.get_all(
        "Salary Slip",
        filters={
            "employee": employee,
            "start_date": [">=", previous_month_start],
            "end_date": ["<=", previous_month_end],
            "docstatus": 1,
        },
        fields=["start_date", "leave_without_pay"],
        limit=1,
    )

    lop_days = (
        last_month_salary_slip[0].leave_without_pay if last_month_salary_slip else 0
    )

    return lop_days


# ? METHOD TO APPEND LOP SUMMARY
# ! prompt_hr.py.payroll_entry.append_lop_summary
def append_lop_summary(doc, method=None):
    # ! CLEAR old LOP Summary entries to avoid duplicates
    frappe.db.delete(
        "LOP Summary",
        {
            "parent": doc.name,
            "parenttype": doc.doctype,
            "parentfield": "custom_lop_summary",
        },
    )
    doc.set("custom_lop_summary", [])

    # * Get all employees from Payroll Employee Detail
    employees = frappe.get_all(
        "Payroll Employee Detail", filters={"parent": doc.name}, fields=["employee"]
    )

    # * Get all LWP-type leave types once (no need to query per employee)
    leave_types = frappe.get_all("Leave Type", filters={"is_lwp": 1}, fields=["name"])
    leave_type_names = [lt.name for lt in leave_types]

    for emp in employees:
        emp_id = emp.employee

        # ? Get Penalty LOPs within date range
        penalties = frappe.get_all(
            "Employee Penalty",
            filters={
                "employee": emp_id,
                "company": doc.company,
                "penalty_date": ["between", [doc.start_date, doc.end_date]],
            },
            fields=["deduct_leave_without_pay"],
        )
        # * Sum total penalty days
        penalty_days = sum(p.get("deduct_leave_without_pay", 0) for p in penalties)

        # ? Get total approved LWP leave days in date range
        lwp_leaves = frappe.get_all(
            "Leave Application",
            filters={
                "employee": emp_id,
                "from_date": ["between", [doc.start_date, doc.end_date]],
                "docstatus": "1",
                "status": "Approved",
                "leave_type": ["in", leave_type_names],
            },
            fields=["total_leave_days"],
        )
        # * Sum all actual LWP days
        actual_lwp = sum(l.total_leave_days for l in lwp_leaves)

        # ? ADD ACTUAL LWP AND PENALTY DAYS TO CALCULATE TOTAL PENALTY
        total_lop = actual_lwp + penalty_days

        if total_lop > 0:
            # * Append to in-memory child table for UI
            doc.append(
                "custom_lop_summary",
                {
                    "employee": emp_id,
                    "penalty_leave_days": penalty_days,
                    "actual_lop": actual_lwp,
                    "total_lop": total_lop
                },
            )

            # ! Optional: Insert to DB (for backend or reports)
            frappe.get_doc(
                {
                    "doctype": "LOP Summary",
                    "parent": doc.name,
                    "parenttype": doc.doctype,
                    "parentfield": "custom_lop_summary",
                    "employee": emp_id,
                    "penalty_leave_days": penalty_days,
                    "actual_lop": actual_lwp,
                    "total_lop": total_lop
                }
            ).insert(ignore_permissions=True)


@frappe.whitelist()
def download_adhoc_salary_template(payroll_entry_id):
    # * Fetch the Payroll Entry document
    payroll_entry = frappe.get_doc("Payroll Entry", payroll_entry_id)

    # * Get the list of employees in this Payroll Entry
    employee_list = [(emp.employee, emp.employee_name) for emp in payroll_entry.employees]

    # * Prepare Excel header
    excel_data = [["Employee", "Employee Name", "Salary Component", "Amount"]]

    # * Add existing adhoc salary details if they exist
    if payroll_entry.custom_adhoc_salary_details:
        for detail in payroll_entry.custom_adhoc_salary_details:
            excel_data.append([
                detail.employee,
                detail.employee_name,
                detail.salary_component,
                detail.amount
            ])
    else:
        # * Otherwise, generate empty rows for manual entry
        for emp_id, emp_name in employee_list:
            excel_data.append([emp_id, emp_name, "", ""])

    # * Generate the XLSX file from the data
    xlsx_file = make_xlsx(excel_data, "Adhoc Salary Details Template")
    xlsx_file.seek(0)

    # * Set response for file download
    frappe.local.response.filename = "Adhoc Salary Details Template.xlsx"
    frappe.local.response.filecontent = xlsx_file.read()
    frappe.local.response.type = "download"

    return build_response("download")


@frappe.whitelist()
def import_adhoc_salary_details(payroll_entry_id, file_url):
    # * Fetch the Payroll Entry document
    payroll_entry = frappe.get_doc("Payroll Entry", payroll_entry_id)

    # * Prepare trackers for success & errors
    import_errors = []
    records_added = 0
    update_count = 0
    payroll_employee_ids = [emp.employee for emp in payroll_entry.employees]

    # * Read rows from the uploaded Excel file
    rows = read_xlsx_file_from_attached_file(file_url)

    if not rows:
        # ! No data found in file
        frappe.throw(_("No data found in the uploaded file. Please check and try again."))

    # * Skip header row and process each line
    for row_index, row in enumerate(rows[1:], start=2):
        if len(row) < 4:
            # ! Row is incomplete
            import_errors.append(f"Row {row_index}: Missing required columns")
            continue

        employee_id, employee_name, salary_component_name, salary_amount = row[:4]

        # * Check for required values and list what’s missing
        missing_fields = []

        if not employee_id:
            missing_fields.append("Employee ID")
        if not employee_name:
            missing_fields.append("Employee Name")
        if not salary_component_name:
            missing_fields.append("Salary Component")
        if not salary_amount:
            missing_fields.append("Amount")

        if missing_fields:
            # ! One or more required fields are missing — show which ones
            import_errors.append(
                f"Row {row_index}: Missing required field(s): {', '.join(missing_fields)}"
            )
            continue

        # * Ensure employee is in the current Payroll Entry
        if employee_id not in payroll_employee_ids:
            # ! Employee not valid for this payroll
            import_errors.append(f"Row {row_index}: Employee {employee_id} is not part of this payroll entry")
            continue

        # * Validate Salary Component
        if not frappe.db.exists("Salary Component", salary_component_name):
            # ! Salary Component missing
            import_errors.append(f"Row {row_index}: Salary Component '{salary_component_name}' does not exist")
            continue

        # * Validate amount is a float
        try:
            salary_amount = float(salary_amount)
        except Exception:
            # ! Amount is invalid
            import_errors.append(f"Row {row_index}: Invalid amount '{salary_amount}'")
            continue

        # * Check if this salary detail already exists to update
        record_updated = False
        for existing in payroll_entry.custom_adhoc_salary_details:
            if existing.employee == employee_id and existing.salary_component == salary_component_name:
                if existing.amount != salary_amount:
                    update_count += 1

                existing.amount = salary_amount
                record_updated = True
                break
            elif existing.employee == employee_id and not existing.salary_component:
                existing.salary_component = salary_component_name
                existing.amount = salary_amount
                record_updated = True
                update_count += 1
                break

        # * Append new entry if no match found
        if not record_updated:
            payroll_entry.append("custom_adhoc_salary_details", {
                "employee": employee_id,
                "employee_name": employee_name,
                "salary_component": salary_component_name,
                "amount": salary_amount
            })
            records_added += 1

    # * If there were errors, show them to the user
    if import_errors:
        # ! Data import failed
        frappe.throw(_("Import failed due to the following issues:<br>") + "<br>".join(import_errors))

    # * Save the Payroll Entry with the new details
    payroll_entry.save()

    if records_added or update_count:
        message = "Import completed successfully."

        if records_added:
            message += f"<br>{records_added} new record(s) were added."

        if update_count:
            message += f"<br>{update_count} existing record(s) were updated."
    else:
        message = "No changes were made. The file may not contain any new or updated data."

    frappe.msgprint(_(message))

    return {"added": records_added}


@frappe.whitelist()
# * METHOD TO FETCH AND SEND SALARY SLEEP TO EMPLOYEE
# ! prompt_hr.py.payroll_entry.send_salary_sleep_to_employee
def send_salary_sleep_to_employee(payroll_entry_id):
    try:
        salary_slip_info_list = frappe.db.get_all("Salary Slip", {"docstatus": 1, "payroll_entry": payroll_entry_id}, ['name', 'employee'])
        print_format_info = frappe.db.get_all("Print Format Selection", {"parenttype":"HR Settings", "parentfield": "custom_print_format_table_prompt", "document": "Salary Slip"}, ["print_format_document", "letter_head"], limit=1)
        print_format_id = print_format_info[0].get("print_format_document") if print_format_info else None
        letter_head = print_format_info[0].get("letter_head") if print_format_info else None

        if salary_slip_info_list:
            for salary_slip_info in salary_slip_info_list:
                attachments = []
                preferred_email = frappe.db.get_value("Employee", salary_slip_info.employee, "prefered_email")
                if not preferred_email:
                    preferred_email = frappe.db.get_value("Employee", salary_slip_info.employee, "user_id")
                try:
                    # ? GENERATE PDF USING FRAPPE'S BUILT-IN PDF GENERATION
                    pdf_content = frappe.get_print(
                        doctype="Salary Slip",
                        name= salary_slip_info.name,
                        print_format=print_format_id,
                        letterhead=letter_head,
                        as_pdf=True,
                    )
                    # ? CREATE ATTACHMENT DICTIONARY
                    attachment_name = f"Salary Slip_{salary_slip_info.name}_{print_format_id}.pdf"
                    attachments.append({"fname": attachment_name, "fcontent": pdf_content})

                except Exception as pdf_error:
                    frappe.log_error(
                        title="PDF Generation Error",
                        message=f"Failed to generate PDF attachment: {str(pdf_error)}\n{traceback.format_exc()}",
                    )
                frappe.sendmail(
                recipients=[preferred_email],
                subject="Salary Slip",
                message="Please find attached your salary slip.",
                attachments=attachments if attachments else None,
            )
    except Exception as e:
        frappe.log_error("Error while sending salary slips", frappe.get_traceback())
        frappe.throw(_("Error while sending salary slips: {0}").format(str(e)))
        
        

@frappe.whitelist()
def send_payroll_entry(payroll_entry_id):
    try:
        account_user_users = frappe.db.get_all("Has Role", {"role": "Accounts User", "parenttype": "User", "parent": ["not in", ["Administrator"]]}, ["parent"])
        print(f"\n\n {account_user_users} \n\n")
        if account_user_users:
            account_user_emails = [user.get("parent") for user in account_user_users]
            payroll_entry_link = frappe.utils.get_url_to_form("Payroll Entry", payroll_entry_id)

            frappe.sendmail(
                recipients=account_user_emails,
                subject="Payroll Entry Notification",
                message=f"A new Payroll Entry has been created. You can view it here: {payroll_entry_link}"
            )

    except Exception as e:
        frappe.log_error("Error while sending Payroll Entry notification", frappe.get_traceback())
        frappe.throw(_("Error while sending Payroll Entry notification: {0}").format(str(e)))