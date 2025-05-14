

import frappe

# ? FUNCTION TO UPDATE EXPECTED SCORE BASED ON INTERVIEW ROUND
def before_save(doc, method):

    if doc.is_new():
        expected_score = frappe.db.get_value("Interview Round",doc.interview_round, "custom_expected_average_score")
        if doc.custom_expected_average_score != expected_score:
            doc.custom_expected_average_score = expected_score