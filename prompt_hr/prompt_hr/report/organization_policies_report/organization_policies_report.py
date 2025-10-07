# organization_document_report.py

import frappe

def execute(filters=None):
    """
    Script report for Organization Documents
    """
    columns = [
        {"label": "ID", "fieldname": "name", "fieldtype": "Link","options":"Organization Documents", "width": 100},
        {"label": "Document Name", "fieldname": "document_name", "fieldtype": "Data", "width": 300},
        {"label": "Publish Date", "fieldname": "publish_date", "fieldtype": "Date", "width": 150},
    ]

    data = []

    # Get current user
    user = frappe.session.user

    # Get the allowed documents based on custom permission
    permission_condition = get_organization_documents_permission(user)

    if not permission_condition:
        return columns, data

    # Fetch documents with ignore_permissions=True to bypass standard DocType permissions
    docs = frappe.db.sql(f"""
        SELECT name, document_name, publish_date
        FROM `tabOrganization Documents`
        WHERE {permission_condition}
    """, as_dict=True)

    for doc in docs:
        data.append({
            "name": doc.name,
            "document_name": doc.document_name,
            "publish_date": doc.publish_date
        })

    return columns, data


def get_organization_documents_permission(user):
    """
    Returns SQL condition string for documents the user can access
    """
    from prompt_hr.prompt_hr.doctype.organization_documents.organization_documents import get_permission_query_conditions
    return get_permission_query_conditions(user)

