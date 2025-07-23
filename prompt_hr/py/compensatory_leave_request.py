import frappe
from frappe import _
from frappe.utils import getdate, flt, add_days, date_diff

@frappe.whitelist()
def expire_compensatory_leave_after_confirmation():
    # ? Step 1: Fetch all compensatory leave types with custom validity set
    leave_types = frappe.get_all(
        "Leave Type",
        filters={"is_compensatory": 1, "custom_leave_validity_days": [">", 0]},
        fields=["name"]
    )

    if not leave_types:
        return

    for leave_type in leave_types:
        # ? Step 2: Fetch approved compensatory leave requests for this leave type
        compensatory_leave_requests = frappe.get_all(
            "Compensatory Leave Request",
            filters={
                "docstatus": 1,
                "workflow_state": "Approved",
                "leave_type": leave_type.name,
            },
            fields=["*"],
            order_by="custom_approved_date ASC"
        )

        # * Fetch Leave Type Doc to access custom validity days
        leave_type_doc = frappe.get_doc("Leave Type", leave_type.name)

        # * Calculate cutoff dates to check expired windows
        backed_date = add_days(getdate("2025-07-05"), -1 * (leave_type_doc.custom_leave_validity_days + 1))
        backed_date_2 = add_days(backed_date, -1 * (leave_type_doc.custom_leave_validity_days + 1))

        # * Dictionary to track previously expired requests per employee
        employers_compensatory_leave_requests = frappe._dict()

        # ? Step 3: Check past requests that are already expired
        for alloc in compensatory_leave_requests:
            if getdate(backed_date_2) <= getdate(alloc.custom_approved_date) < getdate(backed_date):
                leave_allocation = frappe.get_doc("Leave Allocation", alloc.leave_allocation)

                # * Check if negative ledger entry already exists for this request
                negative_ledger_exists = frappe.get_all("Leave Ledger Entry", filters={
                    "employee": leave_allocation.employee,
                    "leave_type": leave_allocation.leave_type,
                    "transaction_type": "Leave Application",
                    "from_date": [">=", alloc.custom_approved_date],
                    "to_date": ["<", add_days(alloc.custom_approved_date, leave_type_doc.custom_leave_validity_days + 1)],
                    "leaves": ["<", 0]
                }, fields=["leaves"], pluck="leaves")
                positive_ledger_exists = frappe.get_all("Leave Ledger Entry", filters={
                    "employee": leave_allocation.employee,
                    "leave_type": leave_allocation.leave_type,
                    "transaction_type": "Leave Application",
                    "from_date": [">=", alloc.custom_approved_date],
                    "to_date": ["<", add_days(alloc.custom_approved_date, leave_type_doc.custom_leave_validity_days + 1)],
                    "leaves": [">", 0]
                }, fields=["leaves"])
                print(f"Checking for negative ledger entries for {alloc.employee} on {alloc.custom_approved_date}: {negative_ledger_exists}")
                if negative_ledger_exists:
                    # * Record already-expired request count per employee
                    employers_compensatory_leave_requests[alloc.employee] = sum(negative_ledger_exists, 0)+sum(positive_ledger_exists, 0)
                else:
                    # // Log skip info for debugging
                    print(f"SKIPPED: Leave for {alloc.employee} on {alloc.custom_approved_date} already expired (negative ledger exists)")

        # ? Step 4: Expire today's eligible compensatory leave requests
        for alloc in compensatory_leave_requests:
            expiry_date = add_days(alloc.custom_approved_date, leave_type_doc.custom_leave_validity_days + 1)

            if getdate(expiry_date) == getdate("2025-07-09"):
                leave_allocation = frappe.get_doc("Leave Allocation", alloc.leave_allocation)

                # * Get leave applications taken under this allocation
                leaves_taken = frappe.get_all(
                    "Leave Application",
                    filters={
                        "employee": alloc.employee,
                        "leave_type": alloc.leave_type,
                        "docstatus": 1,
                        "from_date": [">", alloc.custom_approved_date],
                        "to_date": ["<=", leave_allocation.to_date]
                    },
                    fields=["total_leave_days"]
                )
                print(f"Processing {len(leaves_taken)} leaves taken for {alloc.employee} on {alloc.custom_approved_date}")
                # * Calculate total days taken from this request
                leave_days_taken = sum(flt(leave.total_leave_days) for leave in leaves_taken)

                # * Calculate total days allocated from the request period
                total_allocated = date_diff(alloc.work_end_date, add_days(alloc.work_from_date, -1))

                # * Subtract already-expired days from the taken count
                if employers_compensatory_leave_requests.get(alloc.employee):
                    leave_days_taken -= employers_compensatory_leave_requests[alloc.employee]

                # * Final unused days = allocated - taken
                unused_leaves = total_allocated - leave_days_taken

                # ! Expire unused leaves by making negative ledger entry
                if unused_leaves > 0:
                    if unused_leaves > total_allocated:
                        unused_leaves = total_allocated

                    create_additional_leave_ledger_entry(
                        leave_allocation, unused_leaves * -1, getdate("2025-07-09")
                    )
                else:
                    # * Even if nothing left, count this request as expired
                    employers_compensatory_leave_requests[alloc.employee] = employers_compensatory_leave_requests.get(alloc.employee, 0) + 1
