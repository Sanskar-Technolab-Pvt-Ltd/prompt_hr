import frappe
import requests
import json
from prompt_hr.teams.utils import format_date_time_erpnext_to_teams
from prompt_hr.prompt_hr.doctype.teams_settings.teams_settings import generate_teams_token
from prompt_hr.prompt_hr.doctype.teams_api_post_log.teams_api_post_log import create_teams_api_post_log



@frappe.whitelist()
def create_meeting_link(docname):
    """
    Create a meeting link using the Teams API
    """
    try:
        # docs = "HR-INT-2025-0001"
        interview_doc = frappe.get_doc("Interview", docname)
        
        subject = f"{interview_doc.custom_applicant_name}-{interview_doc.interview_round}"
        date_time = format_date_time_erpnext_to_teams(interview_doc.scheduled_on, interview_doc.from_time, interview_doc.to_time)
        start_time = date_time.get('start_time')
        end_time = date_time.get('end_time')
        token = generate_teams_token()
        
        doc = frappe.get_doc("Teams Settings","Teams Settings")
            
        url = f"{doc.graph_url}/v1.0/users/{doc.object_id}/onlineMeetings"
        
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {token}',
        }
        
        payload = {
        "startDateTime": f"{start_time}Z",
        "endDateTime": f"{end_time}Z",
        "subject": f"{subject}"
        }

        response = requests.post(url, headers=headers, data=json.dumps(payload))
        response_data = response.json()
        
      
        if response.status_code == 201:
            join_url = response.json()['joinUrl']
            status = "Success"
            post_data = create_teams_api_post_log(status,docname,payload,response_data,endpoint_type="onlineMeetings")
            return join_url
        
        else:
            status = "Failed"
            post_data = create_teams_api_post_log(status,docname,payload,response_data,endpoint_type="onlineMeetings")
            
            # frappe.throw("Error: While Post Teams onlineMeetings API")
            
            
    except Exception as e:
        frappe.log_error("Error: While Post Teams onlineMeetings Api", f"Error: {e}\n")
        frappe.throw("Error: While Post Teams onlineMeetings API",{e})
                
        

   
    
    
    
    
    