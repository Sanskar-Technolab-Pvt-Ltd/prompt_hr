{% set dotted_manager_name = frappe.db.get_value("Employee", doc.employee, "employee_name") %}



Hi {{ dotted_manager_name }},

The reporting manager has added their feedback for {{ doc.employee }} in the Probation Feedback Form.
Kindly review the form and add your rating at your earliest convenience.

Thank you!
HR Team