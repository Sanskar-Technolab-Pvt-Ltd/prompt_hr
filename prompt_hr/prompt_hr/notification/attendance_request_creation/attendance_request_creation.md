<p>{% set rh_emp = frappe.db.get_value("Employee", doc.employee, "reports_to") %}
{% if rh_emp %}
    {% set reporting_head = frappe.db.get_value("Employee", rh_emp, "employee_name")%}
{% else %}
    {% set reporting_head = "Reporting Head"%}
{% endif %}</p>

<p>Dear {{ reporting_head }},<br>
 An attendance request has been created—please review it at your convenience.</p>
