<p>{% set reporting_head_id = frappe.db.get_value("Employee", doc.employee, "reports_to") %}
{% if reporting_head_id %}
    {% set reporting_head_name = frappe.db.get_value("Employee", reporting_head_id, "employee_name") %}
{% else %}
    {% set reporting_head_name = "Reporting Head" %}
{% endif %}</p>

<p>Dear {{ reporting_head_name }},<br>

   I am writing to formally request your approval for my WeekOff Change Request. <br>
Kindly review and approve the request at your earliest convenience.</p>
