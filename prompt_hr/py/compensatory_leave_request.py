import frappe
from frappe import _
from frappe.utils import getdate, flt, add_days, date_diff

@frappe.whitelist()
def expire_compensatory_leave_after_confirmation():
    # Get compensatory leave types that have custom validity defined
    leave_types = frappe.get_all(
        "Leave Type",
        filters={"is_compensatory": 1, "custom_leave_validity_days": [">", 0]},
        fields=["name"]
    )

    # Fetch all approved compensatory leave requests for those leave types
    compensatory_leave_requests = frappe.get_all(
        "Compensatory Leave Request",
        filters={
            "docstatus": 1,
            "leave_type": ["in", [lt.name for lt in leave_types]]
        },
        fields=["*"]
    )

    for alloc in compensatory_leave_requests:
        leave_type = frappe.get_doc("Leave Type", alloc.leave_type)

        # Calculate expiry based on the modified date and custom validity days
        expiry_date = add_days(alloc.modified, leave_type.custom_leave_validity_days)
        # Skip if not yet expired
        if getdate(expiry_date) >= getdate():
            continue

        # Get the original leave allocation linked to the request
        leave_allocation = frappe.get_doc("Leave Allocation", alloc.leave_allocation)

        # Fetch leave applications made under this allocation
        leaves_taken = frappe.get_all(
            "Leave Application",
            filters={
                "employee": alloc.employee,
                "leave_type": alloc.leave_type,
                "docstatus": 1,
                "from_date": [">=", leave_allocation.from_date],
                "to_date": ["<=", leave_allocation.to_date]
            },
            fields=["*"]
        )

        # Calculate total leave days taken
        leave_days_taken = sum(flt(leave.total_leave_days) for leave in leaves_taken)

        # Total allocated leave based on the request duration
        total_allocated = date_diff(alloc.work_end_date, add_days(alloc.work_from_date, -1))

        # Calculate unused leave
        unused_leaves = total_allocated - leave_days_taken

        # If unused leave exists, expire it by adding a negative ledger entry
        if unused_leaves > 0:
            ledger_entry = frappe.get_doc({
                "doctype": "Leave Ledger Entry",
                "employee": alloc.employee,
                "leave_type": alloc.leave_type,
                "company": alloc.company,
                "leaves": -1 * unused_leaves,
                "transaction_type": "Leave Allocation",
                "transaction_name": leave_allocation.name,
                "from_date": getdate(),
                "to_date": getdate(leave_allocation.to_date)
            })
            ledger_entry.insert(ignore_permissions=True)
            ledger_entry.submit()
