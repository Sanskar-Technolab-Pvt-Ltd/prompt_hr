# Copyright (c) 2025, Jignasha Chavda and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from datetime import datetime


class InterviewAvailabilityForm(Document):
	pass

@frappe.whitelist()
def hello():
    return "danj"

# ! prompt_hr.prompt_hr.doctype.interview_availibilty_form.interview_availibilty_form.fetch_latest_availability
# ? FETCH LATEST AVAILABILITY FOR A GIVEN DATE AND TIME RANGE
@frappe.whitelist()
def fetch_latest_availability(param_date, param_from_time, param_to_time, designation):
    try:


        # ? CONVERT STRING INPUTS TO TIME OBJECTS
        from_time = datetime.strptime(param_from_time, "%H:%M:%S").time()
        to_time = datetime.strptime(param_to_time, "%H:%M:%S").time()

        # ? FETCH RECORDS FOR THE GIVEN DATE (SORTED BY CREATION DATE DESCENDING)
        records = frappe.db.get_all(
            "Interview Availability",
            filters={"date": param_date, 'designation': designation},
            fields=["name", "from_time", "to_time", 'interviewer'],
            order_by="creation DESC"
        )

        latest_record = []

        for record in records:
            record_from_time = datetime.strptime(str(record["from_time"]), "%H:%M:%S").time()
            record_to_time = datetime.strptime(str(record["to_time"]), "%H:%M:%S").time()

            # ? CHECK IF THE TIME RANGE OVERLAPS (EXCLUDING BOUNDARY CASES)
            if (record_from_time <= from_time < record_to_time) or (record_from_time < to_time <= record_to_time):
                latest_record.append(record['interviewer'])

        return {"status": "Available", "record": latest_record} if latest_record else {"status": "Not Available"}

    except Exception as e:
        frappe.log_error(f"Error in fetch_latest_availability: {str(e)}", "Interview Availability")
        return {"status": "Error", "message": str(e)}