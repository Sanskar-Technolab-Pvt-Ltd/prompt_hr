# Copyright (c) 2025, Jignasha Chavda and contributors
# For license information, please see license.txt

import frappe
import requests
import json
from frappe.model.document import Document
from frappe.utils.password import get_decrypted_password


class TeamsSettings(Document):
    def on_update(self):
        generate_teams_token(self)




def generate_teams_token(doc=""):
    """Generate a token for the Teams API."""
    try:
        doc = frappe.get_doc("Teams Settings","Teams Settings")
        if doc.enable:
            url = f"{doc.url}/{doc.tenent_id}/oauth2/v2.0/token"
            
            headers = {
                "Content-Type": "application/x-www-form-urlencoded"
            }
            
            payload = {
                "client_id": doc.client_id,
                "client_secret": get_decrypted_password("Teams Settings", "Teams Settings","client_secret"),
                "scope" : "https://graph.microsoft.com/.default",
                "grant_type": "client_credentials"
            }
            
            response =  requests.post(url, headers=headers, data=payload)
            
            if response.status_code == 200:
                doc.token = response.json()['access_token']
                frappe.db.set_value("Teams Settings", "Teams Settings", "token", response.json()['access_token'])
                frappe.db.commit()
                return response.json()['access_token']
            else:
                frappe.throw(response.json(), "Failed to Generate Teams Token")
                
        else:
            frappe.throw("Please Enable Teams API from Teams Settings")    
				
    except Exception as e:
        frappe.log_error("Error: While generate Teams token", e)
            
	
            
            
			
            
    