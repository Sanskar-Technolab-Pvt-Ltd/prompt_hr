import frappe
from frappe import _, bold
from frappe.utils import get_link_to_form, cint
from prompt_hr.py.leave_allocation import get_matching_link_field
from hrms.hr.doctype.leave_encashment.leave_encashment import LeaveEncashment


class CustomLeaveEncashment(LeaveEncashment):
    def set_actual_encashable_days(self):
        encashment_settings = self.get_encashment_settings()
        if not encashment_settings.allow_encashment:
            frappe.throw(_("Leave Type {0} is not encashable").format(self.leave_type))

        self.actual_encashable_days = self.leave_balance
        leave_form_link = get_link_to_form("Leave Type", self.leave_type)
        max_encashable_leave = encashment_settings.max_encashable_leaves
        leave_type = frappe.get_doc("Leave Type", self.leave_type)
        employee_self = frappe.get_doc("Employee", self.employee)
        if leave_type.custom_encashment_applicable_to:
            for encashment_applicable_to in leave_type.custom_encashment_applicable_to:
                fieldname = get_matching_link_field(encashment_applicable_to.document)
                if fieldname:
                    field_value = getattr(employee_self, fieldname, None)
                    if field_value == encashment_applicable_to.value:
                        if encashment_applicable_to.maximum_limit == 0:
                            max_encashable_leave = 0
                        else:
                            max_encashable_leave =  cint(encashment_applicable_to.maximum_limit)

        if encashment_settings.non_encashable_leaves:
                actual_encashable_days = self.leave_balance - encashment_settings.non_encashable_leaves
                self.actual_encashable_days = actual_encashable_days if actual_encashable_days > 0 else 0
                frappe.msgprint(
                    _("Excluded {0} Non-Encashable Leaves for {1}").format(
                        bold(encashment_settings.non_encashable_leaves),
                        leave_form_link,
                    ),
                )
        if leave_type.custom_maximum_ctc_limit_to_eligible_for_encashment:
            if employee_self.ctc <= leave_type.custom_maximum_ctc_limit_to_eligible_for_encashment:
                max_encashable_leave = self.leave_balance
            else:
                max_encashable_leave = 0
            
        if max_encashable_leave:
            self.actual_encashable_days = min(
                self.actual_encashable_days, max_encashable_leave
            )
        else:
            self.actual_encashable_days = 0
        if encashment_settings.max_encashable_leaves:
            frappe.msgprint(
                _("Maximum encashable leaves for {0} are {1}").format(
                    leave_form_link, bold(max_encashable_leave)
                ),
                title=_("Encashment Limit Applied"),
            )

    def set_encashment_amount(self):
        employee = frappe.get_doc("Employee", self.employee)
        gross_salary = employee.get("custom_gross_salary")
        # Get the encashment salary days setting from HR Settings
        encashment_salary_days = frappe.db.get_single_value("HR Settings", "custom_encashment_salary_days")
        if not encashment_salary_days:
            frappe.throw(_("Please set 'Encashment Salary Days' in HR Settings."))

        self.encashment_amount = (self.encashment_days * gross_salary) / cint(encashment_salary_days)
