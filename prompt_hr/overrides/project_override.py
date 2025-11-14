import frappe
from erpnext.projects.doctype.project.project import Project



class CustomProject(Project):
    def create_task_from_template(self, task_details):
        
        assigned_emps = {emp.get("custom_employee") for emp in (self.users or []) if emp.get("custom_employee")}
        
        assigned_emps_list = [{"employee": e} for e in assigned_emps] if assigned_emps else []
        
        
        return frappe.get_doc(
            dict(
                doctype="Task",
                subject=task_details.subject,
                project=self.name,
                status="Open",
                exp_start_date=self.calculate_start_date(task_details),
                exp_end_date=self.calculate_end_date(task_details),
                description=task_details.description,
                task_weight=task_details.task_weight,
                type=task_details.type,
                issue=task_details.issue,   
                is_group=task_details.is_group,
                color=task_details.color,
                template_task=task_details.name,
                priority=task_details.priority,
                custom_assignee=assigned_emps_list             
            )
        ).insert()
        