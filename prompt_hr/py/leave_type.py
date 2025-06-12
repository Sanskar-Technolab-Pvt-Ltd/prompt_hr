import frappe

def on_update(doc, method=None):
    if doc.custom_is_earned_leave_allocation:
        if doc.custom_is_quarterly_carryforward_rule_applied:
            doc.db_set("earned_leave_frequency", "Quarterly")
        else:
            doc.db_set("earned_leave_frequency", "Monthly")
    else:
        doc.db_set("earned_leave_frequency", "Yearly")

def custom_get_earned_leaves():
    return frappe.get_all(
		"Leave Type",
		fields=[
			"name",
			"max_leaves_allowed",
			"earned_leave_frequency",
			"rounding",
			"allocate_on_day",
		],
		filters={"custom_is_earned_leave_allocation": 1},
	)