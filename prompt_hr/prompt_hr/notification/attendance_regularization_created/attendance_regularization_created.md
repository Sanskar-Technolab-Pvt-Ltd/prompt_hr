{% set rh_emp = frappe.db.get_value("Employee", doc.employee, "reports_to") %}
{% if rh_emp%}
    {% set reporting_head = frappe.db.get_value("Employee", rh_emp, "user_id") %}
{% else %} 
    {% set reporting_head = "Reporting Head" %} 
{% endif %}

<p>Dear {{reporting_head}},</p>

<p>I would like to inform you that I have created an Attendance Regularization record for date {{doc.regularization_date}}.<br>
The record is now available in the system for your review and necessary action.</p>
