frappe.ui.form.on("Job Requisition", {
    refresh: function (frm) {

        if (frm.doc.workflow_state == "Approved by Director") {

            frm.add_custom_button(__("Create Job Opening"), function () {

                frappe.route_options = {
                    "job_title": frm.doc.designation,
                    "custom_job_requisition_record": frm.doc.name,
                    "designation": frm.doc.designation,
                    "department": frm.doc.department,
                    "employment_type": frm.doc.custom_employment_type,
                    "custom_no_of_position": frm.doc.no_of_positions,
                    "custom_priority": frm.doc.custom_priority,
                    "description": frm.doc.description,
                    "location": frm.doc.custom_work_location,
                    "custom_business_unit": frm.doc.custom_business_unit,
                    "custom_required_experience": frm.doc.custom_experience
                }
                frappe.set_route("Form", "Job Opening", "new-job-opening");
                // frappe.route_to_form("Job Opening", null, { 'job_requisition': frm.doc.name });
                // frappe.new_doc("Patient Consultation", { 'patient_id': cur_frm.doc.patient_id, 'location_of_services': frm.doc.location_of_services, 'poct_service': frm.doc.name })
            });
        }


        if (frm.is_new()) {

            let current_user = frappe.session.user;
            console.log("New Job Requisition", current_user);
            
            frappe.db.get_value("Employee", { "user_id": current_user }, "name", function (r) {

                console.log("Employee Name", r);
                if (r && r.name) {
                    frm.set_value("requested_by", r.name);
                }
            });



        }
    }
});
