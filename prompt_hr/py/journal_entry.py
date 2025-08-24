import frappe

def on_submit(doc, event):
    pass
    # if doc.voucher_type == "Bank Entry":
    #     if any(row.get("reference_type") == "Payroll Entry" for row in doc.accounts) :
            
    #         employees = frappe.db.get_all("Employee", {"status": "Active", "designation": "S - HR Director (Global Admin)"}, ["user_id", "prefered_email"])
            
    #         emp_emails = [em.get("prefered_email") if em.get("prefered_email") else em.get("user_id") for em in employees]
            
    #         print(f"\n\n emp_emails {emp_emails} \n\n")
            
            