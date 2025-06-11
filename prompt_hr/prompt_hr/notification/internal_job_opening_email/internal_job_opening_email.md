<p>Hi {{ doc.employee_name }},</p>

<p>We are excited to announce a new internal job opening for the position of <b>{{ doc.position }}</b> at <b>{{ doc.company }}</b>!</p>

<p>If you're looking for new challenges and opportunities, this could be a great fit for you. We encourage you to apply for this position and take the next step in your career journey with us.</p>

<p><b>Job Details:</b></p>

<ul>
  <li><b>Position:</b> {{ doc.position }}</li>
  <li><b>Department:</b> {{ doc.department }}</li>
  <li><b>Location:</b> {{ doc.location }}</li>
  <li><b>Deadline to Apply:</b> {{ doc.application_deadline }}</li>
</ul>

<p>For more information and to apply, please visit the internal job portal.</p>

<p>We look forward to your application!</p>

<p>Best regards,<br>The {{ doc.company }} HR Team</p>
