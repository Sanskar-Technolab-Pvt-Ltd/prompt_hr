<p>Dear All,</p>

<p>
  This is to inform you that the penalty applied to
  <strong>{{ employee_name }}</strong> on
  <strong>{{ frappe.utils.format_date(penalty_date) }}</strong>
  (Penalty ID: <strong>{{ penalty }}</strong>)
  has been <strong>cancelled</strong> by
  <strong>{{ current_user }}</strong>.
</p>

{% if reason %}
<p><strong>Reason:</strong> {{ reason }}</p>
{% endif %}

{% set penalty_link = frappe.utils.get_url() ~ '/app/employee-penalty/' ~ penalty %}
<p>You can view the penalty record here:
   <a href="{{ penalty_link }}">{{ penalty }}</a>
</p>

<p>Regards,<br/>HR Manager</p>
