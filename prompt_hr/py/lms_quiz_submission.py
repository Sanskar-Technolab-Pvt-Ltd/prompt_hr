import frappe


def update_status(doc, event):
    
    if (doc.score or doc.score == 0) and doc.passing_percentage:
        if doc.score < doc.passing_percentage:
            doc.custom_status = "Failed"
            
            # frappe.db.set_value("Job Applicant", doc.custom_job_applicant, "status", "Screening Test Failed")
            frappe.db.set_value("Job Applicant", "alex@gmail.com", "status", "Screening Test Failed")
            
        elif doc.score >= doc.passing_percentage:
            doc.custom_status = "Passed"
            frappe.db.set_value("Job Applicant", "alex@gmail.com", "status", "Screening Test Passed")
            