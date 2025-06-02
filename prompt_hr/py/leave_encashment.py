import frappe
from frappe import _, bold
from frappe.utils import get_link_to_form, cint
from prompt_hr.py.leave_allocation import get_matching_link_field


def custom_set_actual_encashable_days(doc, method=None):
    encashment_settings = doc.get_encashment_settings()
    if not encashment_settings.allow_encashment:
        frappe.throw(_("Leave Type {0} is not encashable").format(doc.leave_type))

    doc.actual_encashable_days = doc.leave_balance
    leave_form_link = get_link_to_form("Leave Type", doc.leave_type)
    max_encashable_leave = encashment_settings.max_encashable_leaves
    leave_type = frappe.get_doc("Leave Type", doc.leave_type)
    employee_doc = frappe.get_doc("Employee", doc.employee)
    if leave_type.custom_encashment_applicable_to:
        for encashment_applicable_to in leave_type.custom_encashment_applicable_to:
            fieldname = get_matching_link_field(encashment_applicable_to.document)
            if fieldname:
                field_value = getattr(employee_doc, fieldname, None)
                if field_value == encashment_applicable_to.value:
                    if encashment_applicable_to.maximum_limit == 0:
                        max_encashable_leave = 0
                    else:
                        max_encashable_leave =  cint(encashment_applicable_to.maximum_limit)

    if encashment_settings.non_encashable_leaves:
            actual_encashable_days = doc.leave_balance - encashment_settings.non_encashable_leaves
            doc.actual_encashable_days = actual_encashable_days if actual_encashable_days > 0 else 0
            frappe.msgprint(
                _("Excluded {0} Non-Encashable Leaves for {1}").format(
                    bold(encashment_settings.non_encashable_leaves),
                    leave_form_link,
                ),
            )
    if leave_type.custom_maximum_ctc_limit_to_eligible_for_encashment:
        if employee_doc.custom_gross_salary <= leave_type.custom_maximum_ctc_limit_to_eligible_for_encashment:
            max_encashable_leave = doc.leave_balance
        else:
            max_encashable_leave = 0
           
    if max_encashable_leave:
        doc.actual_encashable_days = min(
            doc.actual_encashable_days, max_encashable_leave
        )
    else:
        doc.actual_encashable_days = 0
    if encashment_settings.max_encashable_leaves:
        frappe.msgprint(
            _("Maximum encashable leaves for {0} are {1}").format(
                leave_form_link, bold(max_encashable_leave)
            ),
            title=_("Encashment Limit Applied"),
        )

def custom_set_encashment_amount(doc, method=None):
    employee = frappe.get_doc("Employee", doc.employee)
    gross_salary = employee.get("custom_gross_salary")
    # Get the encashment salary days setting from HR Settings
    encashment_salary_days = frappe.db.get_single_value("HR Settings", "custom_encashment_salary_days")

    if not encashment_salary_days:
        frappe.throw(_("Please set 'Encashment Salary Days' in HR Settings."))

    doc.encashment_amount = (doc.encashment_days * gross_salary) / cint(encashment_salary_days)
   
def before_save(doc, method=None):
    if cint(doc.actual_encashable_days) == 0:
        frappe.throw(_("Encashment failed: You have zero encashable days available."))
