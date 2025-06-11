import frappe
import requests
import json
from datetime import datetime
from prompt_hr.teams.utils import format_date_time_erpnext_to_teams
from prompt_hr.prompt_hr.doctype.teams_settings.teams_settings import generate_teams_token
from prompt_hr.prompt_hr.doctype.teams_api_post_log.teams_api_post_log import create_teams_api_post_log
from prompt_hr.teams.create_meeting import create_meeting_link


@frappe.whitelist()
def teams_calender_book(docname):
    """
    Create calender book in teams and outlooks and send email to all attendees
    """
    try:
        # docs = "HR-INT-2025-0001"
        interview_doc = frappe.get_doc("Interview", docname)
        subject = f"{interview_doc.custom_applicant_name} - {interview_doc.interview_round}"
        date_time = format_date_time_erpnext_to_teams(interview_doc.scheduled_on, interview_doc.from_time, interview_doc.to_time)
        start_time = date_time.get('start_time')
        end_time = date_time.get('end_time')
        token = generate_teams_token()
        
        join_url = ""
        is_face_to_face = interview_doc.custom_mode == "Face to Face Interview"

        if not is_face_to_face:
            join_url = create_meeting_link(docname)
            
            if not join_url:
                frappe.throw(("Error: While Post Teams onlineMeetings API"))

        
        doc = frappe.get_doc("Teams Settings","Teams Settings")
            
        url = f"{doc.graph_url}/v1.0/users/{doc.object_id}/events"
        
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {token}',
        }
        
        formatted_date = datetime.strptime(str(interview_doc.scheduled_on), "%Y-%m-%d").strftime("%d %b %Y")

        readable_date_time = f"{formatted_date} - {interview_doc.from_time} to {interview_doc.to_time} (IST)"
        
        html_content = f""" 
        <div style='font-family:Segoe UI, sans-serif; font-size:14px; color:#333;'>
            <p>Dear Participant,</p>
            <p>You are invited for an interview. Please find the details below:</p>
            <table style='margin-top:10px; margin-bottom:10px; padding:10px; background-color:#f3f6f9; border:1px solid #d1dce5; border-radius:5px;'>
                <tr>
                    <td style='padding:8px 0;margin-right:0px'> <strong>Meeting</strong></td>
                    <td style='padding:8px 0;'>:  {subject}</td>
                </tr>
                <tr>
                    <td style='padding:8px 0;'> <strong>Date & Time</strong></td>
                    <td style='padding:8px 0;'>:  {readable_date_time}</td>
                </tr>
            </table>
        """

        # Add the Join Link if not Face-to-Face
        if not is_face_to_face:
            html_content += f"""
            <p>
                <a href='{join_url}' 
                    style='background-color:#464775; color:#ffffff; padding:10px 16px; text-decoration:none; border-radius:4px; display:inline-block;'>
                    Join Teams Meeting
                </a>
            </p>
            """

        html_content += """
            <p>We look forward to your participation.</p>
            <p>Best regards,<br/>Prompt</p>
        </div>
        """
                
        attendees = []

        # 1. Add Applicant
        
        if interview_doc:
            attendees.append({
                "emailAddress": {
                    "address": interview_doc.job_applicant,
                    "name": interview_doc.custom_applicant_name if interview_doc.custom_applicant_name else interview_doc.job_applicant
                },
                "type": "required"
            })

        # 2. Add Internal Interviewers (interview_details child table)
        
        for row in interview_doc.interview_details:
            if row.custom_interviewer_employee:
                user_id = frappe.db.get_value("Employee", row.custom_interviewer_employee, "user_id")
                if user_id:
                    attendees.append({
                        "emailAddress": {
                            "address": user_id,
                            "name": row.custom_interviewer_name if row.custom_interviewer_name else user_id
                        },
                        "type": "required"
                    })

        # 3. Add External Interviewers (custom_external_interviewers child table)
        
        for row in interview_doc.custom_external_interviewers:
            if row.user:
                custom_user_email = frappe.db.get_value("Supplier", row.user, "custom_user")
                if custom_user_email:
                    attendees.append({
                        "emailAddress": {
                            "address": custom_user_email,
                            "name": row.user_name if row.user_name else custom_user_email
                        },
                        "type": "required"
                    })
        
        payload = {
            "subject": f"{subject}",
            "body": {
                "contentType": "HTML",
                "content": html_content
            },
            "start": {
                "dateTime": f"{start_time}",
                "timeZone": "India Standard Time"
            },
            "end": {
                "dateTime": f"{end_time}",
                "timeZone": "India Standard Time"
            },
            "location": {
                "displayName": "Microsoft Teams"
            },
            "attendees": attendees
            }

        response = requests.post(url, headers=headers, data=json.dumps(payload))
        response_data = response.json()
        
        if response.status_code == 201:
            status = "Success"
            post_data = create_teams_api_post_log(status,docname,payload,response_data,endpoint_type="events")
            interview_doc.db_set('custom_teams_calender_book',1)
            frappe.db.commit()
            return f"Teams Calender has been booked for this candidate : {interview_doc.custom_applicant_name or ''}"
            
        else:
            status = "Failed"
            post_data = create_teams_api_post_log(status,docname,payload,response_data,endpoint_type="events")
            
        
    except Exception as e:
        frappe.log_error("Error: While Post Teams Events API", f"Error: {e}\n")
        frappe.throw("Error: While Post Teams Events API",{e})
            