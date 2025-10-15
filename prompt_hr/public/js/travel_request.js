

frappe.ui.form.on("Travel Request", {
	refresh: function (frm) {
		add_query_filter_to_existing_rows(frm);
		allow_traveldesk_user_to_update_travel_request(frm);
	},
	employee: function (frm) {
		add_query_filter_to_existing_rows(frm);
	},
	company: function (frm) {
		add_query_filter_to_existing_rows(frm);
	},
	onload:function(frm){
		 add_current_user_employee(frm);
		
	},
	before_workflow_action: function(frm) {
		frappe.dom.unfreeze();

		return new Promise((resolve, reject) => {
			try {
				//? Check if the action is Escalate
				if (frm.selected_workflow_action === "Escalate") {
					//? Make escalation_reason required
					frm.set_df_property('custom_escalation_reason', 'reqd', 1);

					//? Check if user has filled the escalation reason
					if (!frm.doc.custom_escalation_reason) {
						frappe.msgprint(__('Please fill Escalation Reason before escalating'));
						reject(); //? Stop workflow
						return;
					}

					resolve(); //? Allow workflow to proceed
				} else {
					//? Reset field to non-mandatory if not escalating
					frm.set_df_property('custom_escalation_reason', 'reqd', 0);
					resolve(); //? Allow workflow to proceed
				}
			} catch (e) {
				//? Handle unexpected errors
				frappe.msgprint(__('An error occurred'));
				reject();
			}
		});
	},
	// after_workflow_action: function(frm){
	// 	 if (frm.doc.workflow_state === "Approved by Reporting Manager") {
	// 		console.log("Function is calling")
    //         frappe.call({
    //             method: "prompt_hr.py.travel_request.after_workflow_action",
    //             args: { docname: frm.doc.name },
    //         });
    //     }	
	// }

});


// ? HANDLE CHILD TABLE ROW ADD/REMOVE EVENTS
frappe.ui.form.on("Travel Itinerary", {
	// ? TRIGGER WHEN A ROW IS ADDED
	itinerary_add: function (frm, cdt, cdn) {
		add_query_filter_to_existing_rows(frm);
	},
	// ? TRIGGER WHEN A ROW IS REMOVED (WORKS VIA ON_CHANGE)
	itinerary_remove: function (frm) {
		add_query_filter_to_existing_rows(frm);
	}
});

function allow_traveldesk_user_to_update_travel_request(frm){
	if(!frm.is_new()){
		//? Allow editing if workflow state is "Pending"
        if (frm.doc.workflow_state === "Pending") {
            frm.fields_dict && Object.keys(frm.fields_dict).forEach(fieldname => {
                frm.set_df_property(fieldname, 'read_only', 0);
            });
            return;
        }

		if(!frappe.user.has_role("Travel Desk User")){
			frm.set_df_property('custom_escalation_reason', 'read_only', 1);
			frm.disable_form();
		}
		else{
			frm.set_df_property('custom_escalation_reason', 'read_only', 0);
		}
	}
}

function add_current_user_employee(frm){
	if (!frm.doc.employee) {
            frappe.call({
                method: "frappe.client.get_value",
                args: {
                    doctype: "Employee",
                    filters: { user_id: frappe.session.user }, 
                    fieldname: ["name"]
                },
                callback: function(r) {
                    if (r.message) {
                        //? If employee exists, set the value in the field
                        frm.set_value("employee", r.message.name);
                    } else {
						//? If no employee is found, clear the employee field
                        frm.set_value("employee", '');
                    }
                },
                //? Ignore permissions while fetching the employee
                ignore_permissions: true
            });
        }
}

// ? FUNCTION TO ADD QUERY FILTER TO EXISTING ROWS
function add_query_filter_to_existing_rows(frm) {
	// ? GET EXISTING CHILD TABLE ROWS
	const rows = frm.doc.itinerary || [];
	if (!rows.length || !frm.doc.employee || !frm.doc.company) {
		return; 
	}

	//? Check if current user has the "Travel Desk User" role
	const isTravelDeskUser = frappe.user.has_role('Travel Desk User');

	// ? CALL PYTHON METHOD TO FETCH GRADE BASED ON EMPLOYEE AND COMPANY
	frappe.call({
		method: "prompt_hr.py.travel_request.get_eligible_travel_modes",
		args: {
			employee: frm.doc.employee,
			company: frm.doc.company
		},
		callback: function (r) {
			if (r.message) {
				const travel_mode = r.message;
				// ? LOOP THROUGH EACH EXISTING ROW TO ADD QUERY FILTER
				rows.forEach(function (row) {
					frm.fields_dict["itinerary"].grid.get_field("custom_travel_mode").get_query = function (doc, cdt, cdn) {
						if (isTravelDeskUser) {
							// If user is "Travel Desk User", don't apply any filter
							return {};
						}
						else{
						return {
							filters: {
								"mode_of_travel": ["in", travel_mode],
							}
						};
						}
					};
				});
			} else {
				frappe.msgprint("Could not fetch grade for this employee.");
				console.error("Error fetching eligible travel modes:", r);
				frm.fields_dict["itinerary"].grid.get_field("custom_travel_mode").get_query = function (doc, cdt, cdn) {
						return {
							filters: {
								"mode_of_travel": ["in", []],
							}
						};
					};
			}
		}
	});
}
