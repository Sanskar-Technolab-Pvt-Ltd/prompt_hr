<p>Hi {{ doc.applicant_name }},</p>

<p>We are pleased to invite you to the next step in our hiring process: a screen test for the position of <b>{{ doc.position }}</b> at <b>{{ doc.company }}</b>! 🎬</p>

<p>Please complete the screen test by following the link below:</p>

<p><b>Screen Test Details:</b></p>
<ul>
  <li><b>Test Link:</b> <a href="{{ doc.test_link }}" target="_blank">Click here to start the screen test</a></li>
  <li><b>Deadline:</b> {{ doc.test_deadline }}</li>
</ul>

<p>We wish you the best of luck and look forward to your participation!</p>

<p>Best regards,<br>The {{ doc.company }} Team</p>
