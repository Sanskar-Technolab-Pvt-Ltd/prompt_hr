import frappe
from frappe.model.document import Document
from prompt_hr.py.utils import get_indifoss_company_name


class ITExitChecklist(Document):

    # ? MAIN HOOK ON UPDATE
    def on_update(self):
        status_map = self.get_clearance_status_map()
        self.update_employee_clearance_status(status_map)

    def before_save(self):
        """
        #! BEFORE SAVE HOOK FOR IT ASSET CLEARANCE
        - TRACKS CHANGES IN APPROVAL STATUS FOR IT CHILD TABLE
        - APPENDS CHANGE HISTORY WITH USER DETAILS
        """

        #? RETURN IF NO IT OR ENGINEERING CHILD TABLE RECORDS
        if not self.it and not self.engineering:
            return

        #? RETURN IF DOCUMENT IS NEW
        if self.is_new():
            return

        #? FETCH PREVIOUS RECORDS FROM DATABASE
        prev_records = frappe.get_all(
            "IT Asset Clearance",
            filters={"parent": self.name},
            fields=["name", "approval_status"]
        )

        #? CREATE DICTIONARY {name: approval_status} FOR QUICK LOOKUP
        prev_dict = {rec["name"]: rec["approval_status"] for rec in prev_records}

        #? GET CURRENT USER'S EMPLOYEE NAME
        current_user = frappe.session.user
        current_employee = frappe.get_all(
            "Employee",
            filters={"user_id": current_user, "status": "Active"},
            fields=["employee_name"]
        )

        if current_employee:
            user = current_employee[0].employee_name
        else:
            user = frappe.session.user

        is_completed = 1

        #? LOOP THROUGH IT CHILD TABLE AND TRACK STATUS CHANGES
        for record in (self.it or []) + (self.engineering or []):
            if record.name in prev_dict:
                previous_status = prev_dict.get(record.name)
                current_status = record.approval_status

                #? CHECK IF APPROVAL STATUS HAS CHANGED
                if current_status != previous_status:
                    #? APPEND CHANGE HISTORY
                    history_entry = f"Approval Status Changed From {previous_status} -> {current_status} by {user}"

                    if record.approval_status_history:
                        record.approval_status_history += f"\n{history_entry}"
                    else:
                        record.approval_status_history = history_entry

            if record.approval_status != "Approved" or not record.status:
                is_completed = 0
                

        if is_completed:
            self.status = "Completed"
        else:
            self.status = "Pending"

    # ? FUNCTION TO GET STATUS FOR EACH CHILD TABLE USING PER-TABLE STATUS RULES
    def get_clearance_status_map(self):
        
        # ? MANUALLY SORTED BY LABEL (ALPHABETICAL ORDER) - This order will be maintained in child tables
        department_map = {
            "it": "IT",
			"engineering":"Engineering"
        }

        status_rules = {
            "it": {
                "empty": {"", "Hold Till (Mention Date)"},
                "completed": {"Discontinue", "Forward/Transfer To"},
            },
			"engineering": {
                "empty": {"", "Hold Till (Mention Date)"},
                "completed": {"Discontinue", "Forward/Transfer To"},
            },
        }

        status_map = {}

        for table, department in department_map.items():
            rows = self.get(table) or []
            rules = status_rules.get(table)

            if not rows:
                status_map[department] = "Pending"
                continue

            statuses = {row.status for row in rows}

            if statuses.issubset(rules["empty"]):
                status = "Pending"
            elif statuses.issubset(rules["completed"]):
                status = "Completed"
            else:
                status = "Partially Completed"

            status_map[department] = status

        return status_map

    def update_employee_clearance_status(self, status_map):
        if not self.employee:
            frappe.msgprint("No employee linked to this checklist.")
            return
        
        try:
            # ? UPDATE EMPLOYEE CLEARANCE STATUS
            self._update_clearance_status_with_consistent_idx(
                parent=self.employee,
                parenttype="Employee",
                status_map=status_map
            )
            
            # ? UPDATE FULL AND FINAL STATEMENT CLEARANCE STATUS (IF EXISTS)
            fnf_doc_name = frappe.db.get_value("Full and Final Statement", {"employee": self.employee})
            if fnf_doc_name:
                self._update_clearance_status_with_consistent_idx(
                    parent=fnf_doc_name,
                    parenttype="Full and Final Statement",
                    status_map=status_map
                )
                
        except Exception as e:
            frappe.msgprint(f"Error updating checklist status: {str(e)}")

    def _update_clearance_status_with_consistent_idx(self, parent, parenttype, status_map):
        """Helper method to update clearance status with consistent idx ordering"""
        
        # ? DEFINE CONSISTENT DEPARTMENT ORDER (SAME AS IN GET_CLEARANCE_STATUS_MAP)
        department_order = [
           "IT", "Engineering"
        ]
        
        # Fetch existing rows with current status
        existing_rows = frappe.get_all(
            "Exit Checklist Status",
            filters={
                "parenttype": parenttype,
                "parentfield": "custom_exit_checklist_status",
                "parent": parent
            },
            fields=["name", "department", "status"]
        )
        
        existing_row_map = {row["department"]: {"name": row["name"], "status": row["status"]} for row in existing_rows}
        
        # ? PROCESS UPDATES FOR EXISTING RECORDS
        for department, new_status in status_map.items():
            if department in existing_row_map:
                # ? ONLY UPDATE IF STATUS HAS CHANGED
                current_status = existing_row_map[department]["status"]
                if current_status != new_status:
                    frappe.db.set_value("Exit Checklist Status", existing_row_map[department]["name"], "status", new_status)
        
        # ? HANDLE NEW RECORDS IN CORRECT ORDER
        new_departments = [dept for dept in status_map.keys() if dept not in existing_row_map]
        
        if new_departments:
            parent_doc = frappe.get_doc(parenttype, parent)
            
            # ? ADD NEW RECORDS IN THE PREDEFINED ORDER
            for department in department_order:
                if department in new_departments:
                    parent_doc.append("custom_exit_checklist_status", {
                        "department": department,
                        "status": status_map[department]
                    })
            
            parent_doc.save(ignore_permissions=True)