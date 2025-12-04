<p>Dear Team,</p>

<p>
    This is to inform you that <b>{{ doc.record }}</b> has been issued.  
    The record link ID is <b>{{ doc.record_link }}</b>.
</p>

<p><b>Key Details:</b></p>

<ul>
    <li>Employee Name / Applicant Name: <b>{{ doc.employee_name or doc.job_applicant_name }}</b></li>
    <li>Current Applicant Status: <b>{{ doc.workflow_state }}</b></li>
</ul>

<p>
    Kindly take the necessary follow-up actions as per the process.
</p>
