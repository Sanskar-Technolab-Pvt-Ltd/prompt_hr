<p>Hello Team,</p>

<p>We’re excited to share that we have an open position for {{ doc.designation }} on our {{ doc.department }} team at {{ doc.company }}!</p>

<p>We believe great people know great people—so if you know someone who would be a great fit, please send them our way! </p>

<p>Deadline to apply: {{ frappe.utils.get_datetime(doc.custom_due_date_for_applying_job_jr).strftime('%d %B, %Y') if doc.custom_due_date_for_applying_job_jr }} </p>

<p>For questions, reach out to HR.</p>
