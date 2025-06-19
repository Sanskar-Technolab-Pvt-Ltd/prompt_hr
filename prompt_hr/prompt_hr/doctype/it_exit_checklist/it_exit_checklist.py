import frappe
from frappe.model.document import Document
from prompt_hr.py.utils import get_prompt_company_name


class ITExitChecklist(Document):

    # ? MAIN HOOK ON UPDATE
    def on_update(self):
        if self.company == get_prompt_company_name().get("company_name"):
            status_map = self.get_clearance_status_map()
            self.update_employee_clearance_status(status_map)

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