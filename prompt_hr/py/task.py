import frappe
from prompt_hr.py.utils import get_roles_from_hr_settings_by_module



def task_view_and_access_permissions(user=None):
    
    
    if not user:
        user = frappe.session.user

    roles = frappe.get_roles(user)
    
    hr_roles = get_roles_from_hr_settings_by_module("custom_hr_roles_for_timesheet_for_prompt")
    
    # if any(r in roles for r in ["S - HR Director (Global Admin)", "S - Accounts User", "S - Accounts Manager", "System Manager"]):
        # return ""
    
    if any(r in roles for r in hr_roles):
        return ""
        
        

    user_sql = frappe.db.escape(user)
    
    if "Projects Manager" in roles:


        employee_subq = f"(select name from `tabEmployee` where user_id={user_sql})"

        reports_to_subq = f"(select name from `tabEmployee` where reports_to in {employee_subq})"

        projects_managed_subq = f"(select name from `tabProject` where custom_project_manager in {employee_subq})"

        employees_child_exists = (
            "exists ("
            "  select 1 from `tabEmployee Multiselect` emu "
            "  where emu.parent = `tabTask`.name "
            "    and emu.parenttype = 'Task' "
            "    and emu.employee in ("
            f"         select name from `tabEmployee` where name in {employee_subq} "
            f"         union all select name from `tabEmployee` where name in {reports_to_subq}"
            "    )"
            ")"
        )

        cond = (
            "("
            f"  `tabTask`.project in {projects_managed_subq} "
            f"  or {employees_child_exists} "
            ")"
        )

        return cond
    
    else:
        employee_of_user_subq = f"(select name from `tabEmployee` where user_id={user_sql})"

        assigned_via_todo_exists = (
            "exists ("
            "  select 1 from `tabToDo` td "
            "  where td.reference_type = 'Task' "
            "    and td.reference_name = `tabTask`.name "
            f"   and td.allocated_to = {user_sql} "
            "    and ifnull(td.status, '') != 'Cancelled'"
            ")"
        )

        in_multiselect_exists = (
            "exists ("
            "  select 1 from `tabEmployee Multiselect` emu "
            "  where emu.parent = `tabTask`.name "
            "    and emu.parenttype = 'Task' "
            f"   and emu.employee in {employee_of_user_subq} "
            ")"
        )

        return f"({assigned_via_todo_exists} or {in_multiselect_exists})"
    


# ! prompt_hr.py.task.share_doc_to_users
@frappe.whitelist()
# ? auto assign and share task to setted user in table
def share_doc_to_users(doc,method):
    """This automatically assigns and shares the document on the on_update event, based on the user set
    in the Assignee Employee Multiselect. If a user is removed, their read permission and assignment are also revoked.
    """
    # ? IF DOCUMENT IS NOT NEW THAT TIME ONLY RUN THIS SCRIPT
    if not doc.is_new():
        employees = doc.custom_assignee
        

        # # ? GET LIST OF ALL CURRENT EMPLOYEE SETTED IN THE Assignee MULTISELECT FILELD
        current_users = {frappe.db.get_value("Employee", emp.employee, "user_id") or "" for emp in employees}
        

        # ? GET A LIST OF ALL open STATUS TODO(ASSIGNMENTS) FOR THIS PARTICULAR DOCUMENT
        assigned_todos = frappe.get_all(
            "ToDo",
            filters={
                "reference_type": "Task",
                "reference_name": doc.name,
                "status": "Open",
            },
            fields=["name", "allocated_to"],
        )

        # ? GET ALL DOCUMENT SHARE FOR THIS CURRENT DOCUMENT (PERMISSIONS WE GIVEN IN THE SIDEBAR)
        shared_users = frappe.get_all(
            "DocShare",
            filters={
                "share_doctype": "Task",
                "share_name": doc.name,
            },
            fields=["name", "user"],
        )

        # ? REMOVE ASSIGNED IF USER IS NOT AVAILABLE IN THE USER CHILD TABLE
        for todo in assigned_todos:
            # ? VALIDATE THE USER IS AVAILABLE OR NOT IN THE USERLIST
            if todo.allocated_to not in current_users:
                frappe.delete_doc(
                    "ToDo", todo.name, force=True, ignore_permissions=True
                )

        # ? REMOVE SHARE PERMISSIONS IF USER IS NOT AVAILABLE IN THE USER CHILD TABLE
        for share in shared_users:
            if share.user not in current_users:
                frappe.delete_doc(
                    "DocShare", share.name, force=True, ignore_permissions=True
                )

        # ? AUTO ASSIGN AND SHARE TO USER IF USER IS ADD IN USER CHILD TABLE
        for dev in doc.custom_assignee:
            
            user = frappe.db.get_value("Employee", dev.employee, "user_id") or None

            # ? CHECK OPEN TODO(ASSIGNMENT) ALREADY EXISTS OR NOT BASED ON THE OPEN STATUS
            existing_todo = frappe.db.get_value(
                "ToDo",
                {
                    "allocated_to": user,
                    "reference_type": "Task",
                    "reference_name": doc.name,
                    "status": "Open",
                },
                "name",
            )
            # ? IF NOT EXISTS TODO(ASSIGNMENT) FOR ADDED NEW USER IN CHILD TABLE
            if not existing_todo:
                # ? create new todo(Assignment) if any open todo is not exists
                todo = frappe.new_doc("ToDo")
                todo.update(
                    {
                        "reference_type": doc.doctype,
                        "reference_name": doc.name,
                        "allocated_to": user,
                        "assigned_by": frappe.session.user,
                        "description": doc.subject,
                    }
                )
                # ? INSERT DOCUMENT
                todo.insert(ignore_permissions=True)

            # ? IF SHARE PERMISSION NOT EXISTS THATTIME ONLY RUN THIS
            if not frappe.db.exists(
                "DocShare",
                {"user": user, "share_doctype": "Task", "share_name": doc.name},
            ):
                # ? Check if the user has the Projects Manager role then give all permission related project
                if frappe.db.exists(
                    "Has Role", {"parent": user, "role": "Projects Manager"}
                ):
                    frappe.share.add(
                        "Task",
                        doc.name,
                        user,
                        read=1,
                        write=1,
                        share=1,
                        everyone=0,
                    )
                # ? IF THE USER HAS THE 'PROJECT USER' ROLE, ONLY GRANT READ-ONLY ACCESS TO THE PROJECT DOCUMENT
                else:
                    frappe.share.add(
                        "Task",
                        doc.name,
                        user,
                        read=1,
                        write=0,
                        share=0,
                        everyone=0,
                    )

        # ? RELOAD DOC
        doc.reload()