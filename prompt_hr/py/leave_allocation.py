import frappe
from frappe.utils import flt
from frappe import _
from hrms.hr.doctype.leave_allocation.leave_allocation import get_carry_forwarded_leaves

@frappe.whitelist()
def before_validate(doc, method=None):
    if doc.leave_type:
        employee_doc = frappe.get_doc("Employee", doc.employee)
        leave_type = frappe.get_doc("Leave Type", doc.leave_type)
                
        if leave_type and leave_type.is_carry_forward:
            # Set default carry forward as 1
            doc.db_set("carry_forward", 1)
            
            # Check if carry forward criteria is met
            if not check_carry_forward_criteria(employee_doc, leave_type):
                doc.db_set("carry_forward", 0)


def check_carry_forward_criteria(employee_doc, leave_type):
    # Check if custom carry forward conditions are defined
    if leave_type.custom_carry_forward_applicable_to:
        # Iterate through each carry forward rule
        for carry_forward_applicable_to in leave_type.custom_carry_forward_applicable_to:
            fieldname = get_matching_link_field(carry_forward_applicable_to.document)
            
            if fieldname:
                # Check if the employee's field value matches the carry forward condition
                field_value = getattr(employee_doc, fieldname, None)
                if field_value == carry_forward_applicable_to.value:
                    # If maximum limit is 0, return 0 to stop carry forward
                    if carry_forward_applicable_to.maximum_limit == 0:
                        return 0
                    else:
                        return carry_forward_applicable_to.maximum_limit
    return leave_type.maximum_carry_forwarded_leaves

def get_matching_link_field(document_name):
    # Retrieve the metadata for the Employee Doctype
    meta = frappe.get_meta("Employee")
    
    # Search for the Link field in Employee Doctype that links to the specified document
    for df in meta.fields:
        if df.fieldtype == "Link" and df.options == document_name:
            return df.fieldname
    
    return None  # Return None if no matching field is found

@frappe.whitelist()
def custom_set_total_leaves_allocated(doc, method=None):
    doc.unused_leaves = flt(
        get_carry_forwarded_leaves(doc.employee, doc.leave_type, doc.from_date, doc.carry_forward),
        doc.precision("unused_leaves"),
    )
    if doc.carry_forward:
        employee_doc = frappe.get_doc("Employee", doc.employee)
        leave_type = frappe.get_doc("Leave Type", doc.leave_type)
        if doc.unused_leaves > check_carry_forward_criteria(employee_doc, leave_type):
            doc.unused_leaves =  check_carry_forward_criteria(employee_doc, leave_type)

    doc.total_leaves_allocated = flt(
        flt(doc.unused_leaves) + flt(doc.new_leaves_allocated),
        doc.precision("total_leaves_allocated"),
    )

    doc.limit_carry_forward_based_on_max_allowed_leaves()

    if doc.carry_forward:
        doc.set_carry_forwarded_leaves_in_previous_allocation()

    if (
        not doc.total_leaves_allocated
        and not frappe.db.get_value("Leave Type", doc.leave_type, "is_earned_leave")
        and not frappe.db.get_value("Leave Type", doc.leave_type, "is_compensatory")
    ):
        frappe.throw(_("Total leaves allocated is mandatory for Leave Type {0}").format(doc.leave_type))