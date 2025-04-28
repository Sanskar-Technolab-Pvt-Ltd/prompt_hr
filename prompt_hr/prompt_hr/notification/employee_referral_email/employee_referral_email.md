<p>Hello Team,</p>

<p>We’re excited to share that we have an open position for <b>{{ doc.designation }}</b> on our <b>{{ doc.department }}</b> team at <b>{{ doc.company }}</b>!</p>

<p>We believe great people know great people — so if you know someone who would be a great fit, please send them our way!</p>

<p><b>Deadline to apply:</b> {{ frappe.utils.get_datetime(doc.custom_due_date_for_applying_job_jr).strftime('%d %B, %Y') if doc.custom_due_date_for_applying_job_jr }}</p>

<p>For any questions, please reach out to HR.</p>
