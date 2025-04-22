<p>Hello Team,</p>

<p> We have released a new internal job opening for the position of {{ doc.designation }}. <br>If you're interested in exploring this opportunity, please through below mentioned link. </p>

<p>Deadline to apply: {{ frappe.utils.get_datetime(doc.custom_due_date_for_applying_job).strftime('%d %B, %Y') if doc.custom_due_date_for_applying_job }} </p>

<p>For questions, reach out to HR.</p>
