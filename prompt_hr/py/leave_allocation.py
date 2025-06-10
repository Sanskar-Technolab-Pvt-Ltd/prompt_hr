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
                if not leave_type.custom_maximum_ctc_limit_for_carry_forward:
                    doc.db_set("carry_forward", 0)
            if leave_type.custom_maximum_ctc_limit_for_carry_forward and leave_type.custom_maximum_ctc_limit_for_carry_forward >= employee_doc.ctc:
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
    # Special case: If the document is "Employee" itself,
    # return the fieldname "employee" directly (if it exists in the metadata)
    if document_name == "Employee":
        for field in meta.fields:
            if field.fieldname == "employee":
                return field.fieldname
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
        elif leave_type.custom_maximum_ctc_limit_for_carry_forward:
            if employee_doc.ctc > leave_type.custom_maximum_ctc_limit_for_carry_forward:
                doc.unused_leaves =  min(doc.unused_leaves,leave_type.maximum_carry_forwarded_leaves)

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

@frappe.whitelist()
def get_leave_types_for_display(doctype, txt, searchfield, start, page_len, filters):
    gender = filters.get("gender")
    company = filters.get("company")

    # Start with base conditions for leave types
    base_condition = """
        (
            (custom_company = %(company)s OR custom_company IS NULL) and (is_lwp = 0)
        )
    """

    # Extend condition based on gender
    gender_condition = ""
    if gender == "Male":
        gender_condition = "OR (custom_is_paternity_leave = 1)"
    elif gender == "Female":
        gender_condition = "OR (custom_is_maternity_leave = 1)"

    condition = f"{base_condition} {gender_condition}"

    # Final SQL query
    return frappe.db.sql(f"""
        SELECT name FROM `tabLeave Type`
        WHERE ({condition})
        ORDER BY name ASC
        LIMIT %(start)s, %(page_len)s
    """, {
        "company": company,
        "start": start,
        "page_len": page_len
    })


def before_submit(doc, method):
    if getattr(doc, "ignore_manual_allocation_check", False):
        return
    # * Get the Leave Type document
    leave_type = frappe.get_doc("Leave Type", doc.leave_type)

    # * Check if it's a Maternity or Paternity Leave
    if leave_type.custom_is_maternity_leave or leave_type.custom_is_paternity_leave:

        # * Get company abbreviation
        company_abbr = frappe.get_value("Company", doc.company, "abbr")

        # * For Indifoss Company Logic
        if company_abbr == frappe.db.get_single_value("HR Settings", "custom_indifoss_abbr"):

            # * Fetch previous allocations excluding the current one
            prev_allocation_count = frappe.get_all(
                "Leave Allocation",
                filters={
                    "docstatus": 1,
                    "employee": doc.employee,
                    "leave_type": doc.leave_type,
                    "name": ["!=", doc.name]
                },
            )

            # * If already 2 allocations exist
            if len(prev_allocation_count) >= 2:
                # * Allow only if max allowed is more than 2 and current count is within limit
                if (
                    int(leave_type.custom_maximum_times_for_applying_leave) > 2 and
                    int(leave_type.custom_maximum_times_for_applying_leave) > len(prev_allocation_count)
                ):
                    # * Set special leave allocation for third child
                    doc.new_leaves_allocated = int(leave_type.custom_leave_allowed_for_third_child)
                    doc.total_leaves_allocated = int(leave_type.custom_leave_allowed_for_third_child)
                else:
                    frappe.throw(_("Maximum limit reached for allocating this type of leave to this employee."))

        # * For Prompt Company Logic
        elif company_abbr == frappe.db.get_single_value("HR Settings", "custom_prompt_abbr"):

            # * Check if any previous allocations exist
            prev_allocation_count = frappe.get_all(
                "Leave Allocation",
                filters={
                    "docstatus": 1,
                    "employee": doc.employee,
                    "leave_type": doc.leave_type,
                    "name": ["!=", doc.name]
                },
            )

            # * Only one-time manual allocation is allowed
            if len(prev_allocation_count) > 0:
                frappe.throw(_("Manual allocation for this leave type is allowed only once"))

