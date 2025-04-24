import frappe
from prompt_hr.py.utils import validate_hash
import json

def get_context(context):
	# do your magic here
	pass

@frappe.whitelist(allow_guest=True)
def validate_candidate_portal_hash(hash, doctype, filters, fields):
	
	fields = json.loads(fields)

	# ? VALIDATE THE HASH FOR A SPECIFIC DOCTYPE AND PRIMARY KEY
	if validate_hash(hash, doctype, filters):

		data = frappe.get_all(
			doctype,
			filters=filters,
			fields=fields
		)
		if not data:
			frappe.throw("Document not found")
		return data
	else:
		frappe.throw("Invalid hash")


import frappe
import json

@frappe.whitelist(allow_guest=True)
def update_candidate_portal_record(hash, doctype, filters, fields):
    # Convert fields from JSON string to dictionary
    fields = json.loads(fields)

    # Validate the hash
    if not validate_hash(hash, doctype, filters):
        frappe.throw("Invalid hash")

    # Search for the existing record
    existing_record = frappe.get_all(
        doctype,
        filters=filters,
        fields=["name"]
    )

    # If the record does not exist, throw an error
    if not existing_record:
        frappe.throw("Document not found")

    # Retrieve the document
    record_name = existing_record[0]['name']
    doc = frappe.get_doc(doctype, record_name)

    # Update fields with the new values
    for field, value in fields.items():
        if hasattr(doc, field):
            setattr(doc, field, value)

    # Save the updated document
    doc.save()

    return "Document updated successfully"

import frappe
from frappe import _
from frappe.utils import cint

@frappe.whitelist()
def update_candidate_portal(doc):
    """
    Update Candidate Portal document with provided values
    
    :param doc: dict containing document values to update including the name
    :return: dict with success status and message
    """
    try:
        if isinstance(doc, str):
            doc = frappe.parse_json(doc)
        
        # Verify document exists
        if not frappe.db.exists("Candidate Portal", doc.get("name")):
            return {"success": False, "message": "Record not found"}
        
        # Get existing document
        existing_doc = frappe.get_doc("Candidate Portal", doc.get("name"))
        
        # Update fields from the form
        for key, value in doc.items():
            if key != "name" and hasattr(existing_doc, key):
                existing_doc.set(key, value)
        
        # Save the document with ignore_permissions for web form
        existing_doc.save(ignore_permissions=True)
        
        return {
            "success": True,
            "message": "Candidate information updated successfully"
        }
        
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), _("Candidate Portal Update Error"))
        return {
            "success": False,
            "message": f"Error updating information: {str(e)}"
        }