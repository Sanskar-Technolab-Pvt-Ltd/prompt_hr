<p>Dear HR Manager,</p>

<p>
    Interviewer <strong>{{ interviewer }}</strong> has confirmed their availability for the interview with the applicant:
</p>

<ul>
    <li><strong>Applicant Name:</strong> {{ doc.custom_applicant_name }}</li>
    <li><strong>Interview Round:</strong> {{ doc.interview_round }}</li>
    <li><strong>Position:</strong> {{ doc.designation }}</li>
</ul>

<p>
    <a href="{{ frappe.utils.get_url() }}/app/interview/{{ doc.name }}">
        Please review the applicant's details.
    </a>
</p>

<p>Regards,<br>HR Team</p>
