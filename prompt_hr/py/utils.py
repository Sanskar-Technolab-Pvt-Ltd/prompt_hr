import frappe
import hmac
import hashlib
import json
import traceback
from frappe import _


# ? FUNCTION TO GENERATE HMAC HASH FROM INPUT USING SITE SECRET
def create_hash(input_text: str) -> str:
    try:
        hash_secret = frappe.local.conf.get("hash_secret_key")
        if not hash_secret:
            frappe.throw(_("Hash secret not found in site_config.json"))

        full_hash = hmac.new(
            key=hash_secret.encode('utf-8'),
            msg=input_text.strip().encode('utf-8'),
            digestmod=hashlib.sha256
        ).hexdigest()

        return full_hash[:12]
    except Exception as e:
        frappe.log_error(f"Error creating hash: {str(e)}\n{traceback.format_exc()}")
        frappe.throw(_("Something went wrong during hash generation."))


# ? FUNCTION TO VERIFY IF PROVIDED INPUT MATCHES THE EXPECTED HASH
def verify_hash(input_text: str, hash_to_check: str) -> bool:
    try:
        generated_hash = create_hash(input_text)
        return hmac.compare_digest(generated_hash, hash_to_check)
    except Exception as e:
        frappe.log_error(f"Error verifying hash: {str(e)}\n{traceback.format_exc()}")
        return False


# ! prompt_hr.py.utils.validate_hash
# ? FUNCTION TO VALIDATE THE HASH FOR A SPECIFIC DOCTYPE AND PRIMARY KEY
@frappe.whitelist(allow_guest=True)
def validate_hash(hash, doctype, filters):
    try:
        filters_dict = json.loads(filters)
        docname = frappe.db.get_value(doctype, filters_dict, "name")

        if not docname:
            frappe.throw(_("Document not found."))

        generated_hash = create_hash(docname)

        if not hmac.compare_digest(generated_hash, hash):
            frappe.throw(_("Invalid hash."))

        return True

    except json.JSONDecodeError:
        frappe.log_error(f"Invalid filters format: {filters}")
        frappe.throw(_("Invalid filter format. Please contact support."))
    except Exception as e:
        frappe.log_error(f"Hash Validation Error: {str(e)}\n{traceback.format_exc()}")
        frappe.throw(_("Something went wrong during hash validation."))


# ? FUNCTION TO SEND FULLY DYNAMIC NOTIFICATION EMAIL
def send_notification_email(
    recipients,
    notification_name=None,
    doctype=None,
    docname=None,
    button_label="View Details",
    button_link="None",
    fallback_subject="Notification",
    fallback_message="You have a new update. Please check your portal.",
    extra_context=None,
    hash_input_text=None,
):
    try:
        hash = None
        base_url = frappe.utils.get_url()
        doc = frappe.get_doc(doctype, docname) if doctype and docname else frappe._dict({})

        if button_link == "None" and doctype and docname:
            button_link = f"{base_url}/app/{doctype.lower().replace(' ', '-')}/{docname}"

        context = {
            "doc": doc,
            "doctype": doctype,
            "docname": docname,
            "button_label": button_label,
            "button_link": button_link,
            "base_url": base_url,
        }

        if hash_input_text:
            hash = create_hash(hash_input_text)

        if extra_context:
            context.update(extra_context)

        notification_doc = None
        if notification_name:
            result = frappe.get_all("Notification", filters={"name": notification_name}, limit=1)
            if result:
                notification_doc = frappe.get_doc("Notification", result[0].name)

        for email in recipients:
            context["user"] = email
            subject, message = fallback_subject, fallback_message

            if notification_doc:
                subject = frappe.render_template(notification_doc.subject or fallback_subject, context)
                message = frappe.render_template(notification_doc.message or fallback_message, context)

            hash_message = f"<p>Password: <b>{hash}</b></p>" if hash else ""

            if button_link:
                message += f"""
                    <hr>
                    {hash_message}
                    <p><b>{button_label}</b></p>
                    <p><a href="{button_link}" target="_blank">{button_label}</a></p>
                """

            frappe.sendmail(
                recipients=[email],
                subject=subject,
                message=message
            )

        frappe.log_error(
            title="Notification Sent",
            message=f"Sent dynamic notification to {len(recipients)} recipient(s)."
        )

    except Exception as e:
        frappe.log_error(
            title="Notification Email Error",
            message=f"Failed sending notification: {str(e)}\n{traceback.format_exc()}"
        )
        frappe.throw(_("An error occurred while sending notification emails."))


# ? FUNCTION TO FETCH DOCUMENTS FROM A JOINING DOCUMENT CHECKLIST
@frappe.whitelist()
def get_checklist_documents(checklist):
    try:
        documents = frappe.db.get_all(
            "Joining Document",
            filters={"parent": checklist},
            fields=["required_document", "document_collection_stage"],
        )
        if not documents:
            return {"error": 1, "message": _("No documents found for the provided checklist.")}
        return {"documents": documents}
    except Exception as e:
        frappe.log_error(f"Error fetching checklist documents: {str(e)}\n{traceback.format_exc()}")
        return {"error": str(e)}


# ? FUNCTION TO INVITE CANDIDATE FOR DOCUMENT COLLECTION
@frappe.whitelist()
def invite_for_document_collection(args, joining_document_checklist, document_collection_stage=None, documents=None):
    try:
        if isinstance(args, str):
            args = frappe.parse_json(args)

        if isinstance(documents, str):
            documents = frappe.parse_json(documents)

        job_applicant = frappe.db.get_value(
            "Job Applicant",
            args.get("name"),
            ["email_id", "phone_number", "applicant_name", "designation"],
            as_dict=True
        )

        if not job_applicant:
            frappe.throw(_("Job Applicant not found."))

        existing = frappe.db.exists("Candidate Portal", {
            "applicant_email": job_applicant.email_id,
        })

        if existing:
            invitation = frappe.get_doc("Candidate Portal", existing)
            invitation.update({
                "phone_number": job_applicant.phone_number,
                "applicant_name": job_applicant.applicant_name,
                "applied_for_designation": job_applicant.designation,
                "joining_document_checklist": joining_document_checklist,
                "document_collection_stage": document_collection_stage,
            })

            existing_required_docs = {d.required_document for d in invitation.documents}
            if documents:
                new_docs_seen = set()
                for doc in documents:
                    req_doc = doc.get("required_document")
                    if req_doc and req_doc not in existing_required_docs and req_doc not in new_docs_seen:
                        invitation.append("documents", {
                            "required_document": req_doc,
                            "document_collection_stage": doc.get("document_collection_stage")
                        })
                        new_docs_seen.add(req_doc)

            invitation.save(ignore_permissions=True)
            frappe.db.commit()
            return _("Invitation updated successfully.")
        else:
            invitation = frappe.new_doc("Candidate Portal")
            invitation.update({
                "applicant_email": job_applicant.email_id,
                "phone_number": job_applicant.phone_number,
                "applicant_name": job_applicant.applicant_name,
                "applied_for_designation": job_applicant.designation,
                "joining_document_checklist": joining_document_checklist,
                "document_collection_stage": document_collection_stage,
            })

            if documents:
                seen_docs = set()
                for doc in documents:
                    req_doc = doc.get("required_document")
                    if req_doc and req_doc not in seen_docs:
                        invitation.append("documents", {
                            "required_document": req_doc,
                            "document_collection_stage": doc.get("document_collection_stage")
                        })
                        seen_docs.add(req_doc)

            invitation.insert(ignore_permissions=True)
            frappe.db.commit()
            return _("Invitation sent successfully.")

    except Exception as e:
        frappe.log_error(f"Error inviting for document collection: {str(e)}\n{traceback.format_exc()}")
        frappe.throw(_("An error occurred while inviting for document collection."))

