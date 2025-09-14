<p>Dear <b>{{ employee_name }}</b>,</p>

<p>
    Please be informed that the following leave deductions have been scheduled
    as a penalty on <b>{{ frappe.format_date(penalty_date,"dd-MM-yyyy") }}</b>:
</p>

<table border="1" cellpadding="6" cellspacing="0"
       style="border-collapse: collapse; width: 100%; margin: 12px 0; font-size: 14px;">
    <thead style="background-color: #f2f2f2;">
        <tr>
            <th style="text-align: left;">Leave Type</th>
            <th style="text-align: left;">Leave Amount</th>
            <th style="text-align: left;">Reason</th>

        </tr>
    </thead>
    <tbody>
        {%- set penalty_doc = frappe.get_doc("Employee Penalty", penalty) -%}
        {% if penalty_doc %}
            {% for row in penalty_doc.leave_penalty_details %}
            <tr>
                <td>{{ row.leave_type }}</td>
                <td>{{ row.leave_amount }}</td>
                <td> {{row.reason}}</td>
            </tr>
            {% endfor %}
        {% endif %}
    </tbody>
</table>

<p>
    These leave deductions will automatically be applied on the penalty date mentioned above.
</p>

<p>
    If you have any questions or need clarification, please contact the HR department.
</p>

<p><br></p>

<p>
    Warm regards,<br>
    HR Team<br>
</p>
