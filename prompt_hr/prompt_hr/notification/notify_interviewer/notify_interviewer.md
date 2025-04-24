Dear {{ interviewer or "Interviewer" }},
<br>
You have been scheduled for an interview session:
<br>
<b>Interview:</b> {{ doc.name }}<br>
<b>Date:</b> {{ frappe.utils.format_date(doc.scheduled_on) }}<br>
<b>Time:</b> {{ doc.from_time }} to {{ doc.to_time }}<br><br>

Please confirm your availability for this session.

<a href="{{ frappe.utils.get_url() }}/app/interview/{{ doc.name }}">
    Click here to view the interview details and Confirm Your Availability
</a>

<br><br>Regards,<br>
HR Team
