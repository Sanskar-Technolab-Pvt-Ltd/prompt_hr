{% if doc.rh_rating_added and doc.dh_rating_added == 0%}
        {% if doc.hod %}
            {% set hod_name = frappe.db.get_value("Employee", doc.hod, "employee_name") %}
            <p>Dear{{ hod_name if hod_name else "Head of Department"}},</p>
        {% else %}
            <p>Dear Head of Department,</p>
        {% endif %}
  {% elif doc.rh_rating_added == 0 %}
        {% if doc.reporting_manager %}
            {% set reporting_head_name = frappe.db.get_value("Employee", doc.reporting_manager, "employee_name") %}
            <p>Dear {{ reporting_head_name if reporting_head_name else "Reporting Head"}},</p>
        {% else %}
            <p>Dear Reporting Head,</p>
        {% endif %}
  {% endif %}

<p>You are requested to kindly review and provide your remarks for {{ doc.employee_name }} in the Confirmation Evaluation Form. Your input is essential to proceed with the confirmation process.</p>

<p>Please log in to the system and complete your section at the earliest convenience.</p>

<p>Thank you for your cooperation.</p>

<p>Best regards,</p>
<p>HR Department</p>
