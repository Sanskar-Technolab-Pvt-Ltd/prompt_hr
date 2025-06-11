# Copyright (c) 2025, Jignasha Chavda and contributors
# For license information, please see license.txt

import frappe
import json
from frappe.model.document import Document


class TeamsApiPostLog(Document):
	pass




@frappe.whitelist()
def create_teams_api_post_log(status, source_docname,request, response,endpoint_type):
    
    """ create log after post data into teams api """
    
    try:
        exists = frappe.db.get_value("Teams Api Post Log", filters={"source_docname": source_docname, "endpoint_type": endpoint_type}, fieldname=['name'])
        if exists:
            log = frappe.get_doc("Teams Api Post Log",exists)
        else:
            log = frappe.new_doc("Teams Api Post Log")
            
        log.source_docname = source_docname
        log.request = json.dumps(request, indent=4)
        log.response = json.dumps(response, indent=4)
        log.endpoint_type = endpoint_type
        log.status = status
        log.save()
        frappe.db.commit()
    
    except Exception as e:
        frappe.log_error("Error: While create Teams log", f"Error: {e}\nargs: {source_docname}\n, {request}\n, {response}\n, {status}\n, {endpoint_type}\n")
        frappe.msgprint(str(e))
        return e
    
