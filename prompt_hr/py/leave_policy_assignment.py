import frappe

@frappe.whitelist()
def on_update(doc,method=None):
    if doc.leave_policy:
        leave_policy = frappe.get_doc("Leave Policy", doc.leave_policy)
        employee_doc = frappe.get_doc("Employee", doc.employee)
        if leave_policy:
            leave_policy_details = frappe.get_all("Leave Policy Detail",filters={"parent":leave_policy.name},fields=['*'])
            for leave_policy_detail in leave_policy_details:
                leave_type = frappe.get_doc("Leave Type", leave_policy_detail.leave_type)
                if leave_type and leave_type.is_carry_forward:
                    if any([
                            leave_type.custom_cf_applicable_to_business_unit,
                            leave_type.custom_cf_applicable_to_department,
                            leave_type.custom_cf_applicable_to_location,
                            leave_type.custom_cf_applicable_to_employment_type,
                            leave_type.custom_cf_applicable_to_grade,
                            leave_type.custom_cf_applicable_to_product_line
                        ]):
                            # Format: (LeaveType field, Employee field)
                            criteria = [
                                ("custom_cf_applicable_to_business_unit", "custom_business_unit"),
                                ("custom_cf_applicable_to_department", "department"),
                                ("custom_cf_applicable_to_location", "custom_work_location"),
                                ("custom_cf_applicable_to_employment_type", "employment_type"),
                                ("custom_cf_applicable_to_grade", "grade"),
                                ("custom_cf_applicable_to_product_line", "custom_product_line"),
                            ]

                            for leave_field, employee_field in criteria:
                                leave_values = getattr(leave_type, leave_field)
                                employee_value = getattr(employee_doc, employee_field)

                                if not leave_values:
                                    continue

                                leave_ids = []

                                if isinstance(leave_values, list) and isinstance(leave_values[0], frappe.model.document.Document):
                                    for d in leave_values:
                                        if not d:
                                            continue

                                        if leave_field == "custom_cf_applicable_to_product_line":
                                            leave_ids.append(frappe.get_doc("Product Line Multiselect", d.name).indifoss_product)
                                        elif leave_field == "custom_cf_applicable_to_business_unit":
                                            leave_ids.append(frappe.get_doc("Business Unit Multiselect", d.name).bussiness_unit)
                                        elif leave_field == "custom_cf_applicable_to_department":
                                            leave_ids.append(frappe.get_doc("Department Multiselect", d.name).department)
                                        elif leave_field == "custom_cf_applicable_to_location":
                                            leave_ids.append(frappe.get_doc("Work Location Multiselect", d.name).work_location)
                                        elif leave_field == "custom_cf_applicable_to_employment_type":
                                            leave_ids.append(frappe.get_doc("Employment Type Multiselect", d.name).employement_type)
                                        elif leave_field == "custom_cf_applicable_to_grade":
                                            leave_ids.append(frappe.get_doc("Grade Multiselect", d.name).grade)
                                if employee_value in leave_ids:
                                    doc.db_set("carry_forward",1)
                    else:
                        doc.db_set("carry_forward", 0)
