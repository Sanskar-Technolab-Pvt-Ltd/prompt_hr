import frappe

def on_submit(doc, method):
    """
    Triggered after a Leave Policy Assignment document is submitted.
    Allocates leaves based on policy details, effective dates, and current date.
    Updates corresponding Leave Allocation and Leave Ledger Entry records.
    """
    
    effective_from = doc.effective_from
    effective_to = doc.effective_to

    if not effective_from or not effective_to:
        frappe.throw("Effective From or Effective To date is missing in the document.")

    # Fetch all relevant Leave Allocations for this assignment
    leave_allocations = frappe.db.get_all(
        'Leave Allocation',
        filters={
            'employee': doc.employee,
            'leave_policy_assignment': doc.name
        },
        fields=['name', 'leave_type', 'unused_leaves']
    )

    if not leave_allocations:
        frappe.throw("No Leave Allocation records found for this assignment.")

    current_date = frappe.utils.nowdate()

    leave_policy_doc = frappe.get_doc('Leave Policy', doc.leave_policy)

    for leave_policy_detail in leave_policy_doc.get("leave_policy_details"):
        leave_type = leave_policy_detail.leave_type
        annual_allocation = leave_policy_detail.annual_allocation

        # Fetch Leave Type details
        leave_type_doc = frappe.get_doc('Leave Type', leave_type)
        is_earned = leave_type_doc.custom_is_earned_leave_allocation
        is_quarterly = leave_type_doc.custom_is_quarterly_carryforward_rule_applied
        allocation_day = leave_type_doc.allocate_on_day

        if is_earned and is_quarterly:
            # Quarterly allocation logic
            quarters = []
            for i in range(4):
                start = frappe.utils.add_months(effective_from, i * 3)
                end = frappe.utils.add_days(frappe.utils.add_months(start, 3), -1)
                quarters.append((start, end))

            leave_per_quarter = annual_allocation / 4
            passed_quarters = 0

            for start, end in quarters:
                if allocation_day == 'First Day' and frappe.utils.getdate(start) <= frappe.utils.getdate(current_date):
                    passed_quarters += 1
                elif allocation_day == 'Last Day' and frappe.utils.getdate(end) <= frappe.utils.getdate(current_date):
                    passed_quarters += 1

            allocated_leaves = passed_quarters * leave_per_quarter

            # Update Leave Allocation and Ledger Entry
            for alloc in leave_allocations:
                if alloc.leave_type == leave_type:
                    total_allocated = allocated_leaves + (alloc.unused_leaves or 0)
                    frappe.db.set_value('Leave Allocation', alloc.name, 'new_leaves_allocated', allocated_leaves)
                    frappe.db.set_value('Leave Allocation', alloc.name, 'total_leaves_allocated', total_allocated)

                    ledger_name = frappe.db.get_value(
                        'Leave Ledger Entry',
                        {'transaction_name': alloc.name, 'is_carry_forward': 0},
                        'name'
                    )
                    if ledger_name:
                        frappe.db.set_value('Leave Ledger Entry', ledger_name, 'leaves', allocated_leaves)

    frappe.db.commit()
        


