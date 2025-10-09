# organization_document_report.py

import frappe

def execute(filters=None):
    """
    Script report for Organization Documents
    """
    columns = [
        {"label": "ID", "fieldname": "name", "fieldtype": "Link","options":"Organization Documents", "width": 300},
        # {"label": "Document Name", "fieldname": "document_name", "fieldtype": "Data", "width": 300},
        {"label": "Publish Date", "fieldname": "publish_date", "fieldtype": "Date", "width": 150},
        {"label": "Document Name", "fieldname": "child_doc_title", "fieldtype": "Data", "width": 250},
        {"label": "Attachment", "fieldname": "attachment", "fieldtype": "HTML", "width": 250},
    ]

    data = []

    # Get current user
    user = frappe.session.user

    # Get the allowed documents based on custom permission
    permission_condition = get_organization_documents_permission(user)
    
    if not permission_condition:
        return columns, data
    
    if permission_condition:
        permission_condition = permission_condition.replace("`tabOrganization Documents`", "parent_doc")

    # Fetch documents with ignore_permissions=True to bypass standard DocType permissions
   #  Fetch parent and child records together using LEFT JOIN
    docs = frappe.db.sql(f"""
        SELECT 
            parent_doc.name,
            parent_doc.publish_date,
            child_doc.title AS child_doc_title,
            child_doc.attachment AS attachment
        FROM `tabOrganization Documents` AS parent_doc
        LEFT JOIN `tabDocuments Table` AS child_doc
            ON child_doc.parent = parent_doc.name
        WHERE {permission_condition}
        ORDER BY parent_doc.publish_date DESC
    """, as_dict=True)

    for doc in docs:
        attachment_html = ""
        if doc.attachment:
            # Build full URL if relative path
            file_url = doc.attachment
            if not file_url.startswith("http"):
                site_url = frappe.utils.get_url()  # Gets your site base URL
                file_url = f"{site_url}{file_url}"

            attachment_html = f'<a href="{file_url}" target="_blank" style="color:#007bff;text-decoration:underline;">Open Document</a>'
            
        data.append({
            "name": doc.name,
            # "document_name": doc.name,
            "publish_date": doc.publish_date,
            "child_doc_title": doc.child_doc_title or "",
            "attachment": attachment_html or ""
        })


    return columns, data


def get_organization_documents_permission(user):
    """
    Returns SQL condition string for documents the user can access
    """
    from prompt_hr.prompt_hr.doctype.organization_documents.organization_documents import get_permission_query_conditions
    return get_permission_query_conditions(user)

