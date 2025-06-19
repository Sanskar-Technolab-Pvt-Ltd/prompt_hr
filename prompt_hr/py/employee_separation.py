import frappe
from prompt_hr.py.utils import send_notification_email, get_prompt_company_name, get_indifoss_company_name


# ? BEFORE SAVE HOOK
def before_save(doc, method):
    # ? CHECK AND PROCESS EXIT CHECKLIST ACTIONS
    create_or_link_checklists_and_notify(doc)


# ? FUNCTION TO HANDLE CHECKLIST CREATION/LINKING AND EMAIL NOTIFICATION
def create_or_link_checklists_and_notify(doc):
    for row in doc.activities:
        employee_id = doc.get("employee")

        try:
            # ? HANDLE IT EXIT CHECKLIST CREATION OR LINKING
            if row.get("custom_checklist_name") == "IT Exit Checklist":
                # ? CHECK IF CHECKLIST ALREADY EXISTS
                existing_checklist = frappe.db.get_value(
                    "IT Exit Checklist", {"employee": employee_id}, "name"
                )

                if existing_checklist and not row.custom_checklist_record:
                    row.custom_checklist_record = existing_checklist

                elif not existing_checklist:
                    # ? CREATE NEW CHECKLIST
                    checklist = create_new_it_exit_checklist(employee_id)
                    row.custom_checklist_record = checklist.name

            # ? SEND EMAIL IF RAISED AND NOT YET SENT
            if row.custom_is_raised == 1 and row.custom_is_sent == 0:
                send_pending_action_email_for_exit(
                    row, row.custom_checklist_record, doc.company
                )
                row.custom_is_sent = 1

        except Exception as e:
            frappe.log_error(
                f"Error during checklist handling: {e}", "Exit Checklist Error"
            )
            frappe.throw(
                "Something went wrong while handling checklist or sending email."
            )


# ? FUNCTION TO CREATE A NEW IT EXIT CHECKLIST
def create_new_it_exit_checklist(employee_id):

    try:

        # ? FETCH EMPLOYEE DETAILS
        fields = [
            "employee_name",
            "designation",
            "reports_to",
            "department",
            "date_of_joining",
            "relieving_date",
            "company"
        ]
        
        values = frappe.db.get_value("Employee", employee_id, fields, as_dict=True)

        if not values:
            frappe.throw(f"Employee '{employee_id}' not found.")

        # ? INITIALIZE CHECKLIST
        checklist = frappe.new_doc("IT Exit Checklist")
        checklist.employee = employee_id
        checklist.employee_name = values.employee_name
        checklist.designation = values.designation
        checklist.reports_to = values.reports_to
        checklist.department = values.department
        checklist.date_of_joining = values.date_of_joining
        checklist.relieving_date = values.relieving_date
        checklist.company = values.company

       

        # ? FETCH ALL CLEARANCE ITEMS
        clearance_items = frappe.get_all(
            "Exit Clearance Item",
            fields=["clearance_item", "table_name"]
        )

        frappe.msgprint(f"Total Clearance Items Fetched: {len(clearance_items)}")
         
        # ? GROUP ITEMS BY TABLE NAME
        table_map = {}
        for item in clearance_items:
            table = item.table_name
            if table not in table_map:
                table_map[table] = []
            table_map[table].append(item.clearance_item)

        frappe.msgprint(f"Grouped Items by Table: {table_map}")

        # ? ADD ITEMS TO THEIR RESPECTIVE CHILD TABLES
        for table_name, items in table_map.items():
            for item_name in items:
                checklist.append(table_name, {
                    "clearance_item": item_name,
                })
                frappe.msgprint(f"Added {item_name} to {table_name}")

        checklist.insert(ignore_permissions=True)
        frappe.msgprint(f"Created IT Exit Checklist: {checklist.name}")
        return checklist

    except Exception as e:
        frappe.log_error(
            f"Failed to create IT Exit Checklist: {e}", "Checklist Creation Error"
        )
        frappe.throw("Unable to create IT Exit Checklist. Please check Employee details.")



# ? FUNCTION TO SEND EMAIL TO USER OR ROLE FOR ANY EXIT CHECKLIST
def send_pending_action_email_for_exit(row, checklist_name, company):
    try:
        doc_type = row.custom_checklist_name or "Exit Checklist"
        doc_name = checklist_name
        notification_name = "Exit Checklist"

        if not company:
            frappe.throw("Company not found for checklist employee.")

        if row.user and row.role:
            frappe.throw(
                "Kindly either select User or Role, not both", title="Invalid Selection"
            )

        recipients = []

        if row.role:
            users = frappe.get_all(
                "Has Role", filters={"role": row.role}, pluck="parent"
            )
            emp_users = frappe.get_all(
                "Employee",
                filters={
                    "user_id": ["in", users],
                    "company": company,
                    "status": "Active",
                },
                fields=["user_id"],
            )
            user_ids = [e.user_id for e in emp_users if e.user_id]
            recipients = frappe.get_all(
                "User", filters={"name": ["in", user_ids], "enabled": 1}, pluck="email"
            )

        elif row.user:
            email = frappe.db.get_value("User", row.user, "email")
            if email:
                recipients = [email]

        if not recipients:
            frappe.throw("No valid recipients found for checklist email.")

        send_notification_email(
            recipients=recipients,
            notification_name=notification_name,
            doctype=doc_type,
            docname=doc_name,
            button_label="View Checklist",
            send_header_greeting=True,
        )

        frappe.msgprint("Checklist notification sent.")

    except Exception as e:
        frappe.log_error(
            f"Failed to send checklist email: {e}", "Checklist Email Error"
        )
        frappe.throw("Unable to send checklist notification.")
