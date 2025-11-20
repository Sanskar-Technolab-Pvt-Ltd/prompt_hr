

frappe.ui.form.on("Travel Request", {
	refresh: function (frm) {
		add_query_filter_to_existing_rows(frm);
		control_travel_desk_fields(frm)
		allow_traveldesk_user_to_update_travel_request(frm);
		allow_edit_booking_table_to_traveldesk_user(frm);
	},
	employee: function (frm) {
		add_query_filter_to_existing_rows(frm);
	},
	company: function (frm) {
		add_query_filter_to_existing_rows(frm);
	},
	onload:function(frm){
		add_current_user_employee(frm);
		control_travel_desk_fields(frm)
	},
	before_workflow_action: function(frm) {
	frappe.dom.unfreeze();

		return new Promise((resolve, reject) => {
			try {
					if (frm.selected_workflow_action !== "Escalate") {
						resolve();
						return;
					}

					const dialog_fields = [
						{
							label: "Employee",
							fieldname: "employee",
							fieldtype: "Link",
							options: "Employee",
							ignore_user_permissions: true,
							reqd: 1,
							get_query: function () { return {}; }
						},
						{
							label: "Reason For Escalation",
							fieldname: "reason_for_escalation",
							fieldtype: "Small Text",
							reqd: 1,
						}
					];

					let dialog = new frappe.ui.Dialog({
						title: __("Confirm {0}", [frm.selected_workflow_action]),
						fields: dialog_fields,
						primary_action_label: "Send For Approval",
						primary_action: function (values) {
							// hide dialog and call backend
							
							dialog.hide();
							frappe.call({
								method: "prompt_hr.py.utils.share_doc_with_employee",
								args: {
									employee: values.employee,
									doctype: frm.doctype,
									docname: frm.docname,
									reason_for_escalation: values.reason_for_escalation || ""
								},
								callback: function (r) {
									if (r.message && r.message.status === "success") {
										frappe.msgprint(__(`Document shared with ${values.employee} successfully.`));
										resolve();
									} else {
										frappe.msgprint(__('Failed to share document.'));
										reject();
									}
								},
								error: function (err) {
									console.error("Error during API call:", err);
									frappe.msgprint(__('Error occurred while sharing document.'));
									reject();
								}
							});
						},
						secondary_action_label: __("Cancel"),
						secondary_action: function () {
							dialog.hide();
							reject();
						}
					});

					dialog.show();

				} catch (e) {
					console.error(e);
					reject();
				}
		});
	},








// 	before_workflow_action: function(frm) {
// 	frappe.dom.unfreeze();

// 	return new Promise((resolve, reject) => {
// 		try {
// 			//? Check if the action is Escalate
// 			if (frm.selected_workflow_action === "Escalate") {

// 				//? Check user role - only Travel Desk User can edit
// 				if (!frappe.user.has_role("Travel Desk User")) {
// 					reject(); //? Stop workflow
// 					return;
// 				}

// 				//? Make the escalation reason field required
// 				frm.set_df_property('custom_escalation_reason', 'reqd', 1);

// 				//? Make the field editable only for Travel Desk User
// 				frm.set_df_property('custom_escalation_reason', 'read_only', 0);

// 				if (!frm.doc.custom_escalation_reason){
// 					//? Scroll to the field and focus cursor inside textarea
// 					setTimeout(() => {
// 						let fieldEl = $('[data-fieldname="custom_escalation_reason"] textarea');
// 						if (fieldEl.length) {
// 							$('html, body').animate({
// 								scrollTop: fieldEl.offset().top - 100
// 							}, 300);
// 							fieldEl.focus();
// 						}
// 					}, 300);
// 				}
				

// 				// ? Check if user has filled the escalation reason
// 				if (!frm.doc.custom_escalation_reason) {
// 					frappe.msgprint(__('Please fill Escalation Reason before escalating.'));
// 					reject(); //? Stop workflow
// 					return;
// 				}

// 				resolve(); //? Allow workflow to proceed
// 			} else {
// 				//? If not escalating, remove required and make read-only again
// 				frm.set_df_property('custom_escalation_reason', 'reqd', 0);

// 				//? If not travel desk user → field stays readonly
// 				if (!frappe.user.has_role("Travel Desk User")) {
// 					frm.set_df_property('custom_escalation_reason', 'read_only', 1);
// 				}
// 				resolve(); //? Allow workflow to proceed
// 			}
// 		} catch (e) {
// 			frappe.msgprint(__('An unexpected error occurred.'));
// 			console.error(e);
// 			reject();
// 		}
// 	});
// },

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

function reason_for_escalation_dialog(frm) {
    return new Promise((resolve, reject) => {
        frappe.dom.unfreeze()
        
        frappe.prompt({
            label: 'Reason for Escalation',
            fieldname: 'reason_for_escalation',
            fieldtype: 'Small Text',
            reqd: 1
        }, (values) => {
            if (values.reason_for_escalation) {
                frm.set_value("custom_escalation_reason", values.reason_for_escalation)
                // frm.set_value("approval_status", "Rejected")
                frm.save().then(() => {
                    resolve();
                }).catch(reject);						
            }
            else {
                reject()
            }
        })
    });
}



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

function allow_edit_booking_table_to_traveldesk_user(frm){
	//?  CONTROL CHILD TABLE PERMISSIONS
		if (!frappe.user.has_role("Travel Desk User")) {
			//? Make the child table read-only
			frm.set_df_property('custom_booking_details', 'read_only', 1);

			//? Hide Add Row and Remove Row buttons
			frm.fields_dict.custom_booking_details.grid.wrapper.find('.grid-add-row').hide();
			frm.fields_dict.custom_booking_details.grid.wrapper.find('.grid-remove-rows').hide();

			frm.set_df_property('custom_escalation_reason','read_only',1)
		} else {
			//? Allow editing for Travel Desk User
			frm.set_df_property('custom_booking_details', 'read_only', 0);			
			frm.fields_dict.custom_booking_details.grid.wrapper.find('.grid-add-row').show();
			frm.fields_dict.custom_booking_details.grid.wrapper.find('.grid-remove-rows').show();
			frm.set_df_property('custom_escalation_reason','read_only',0)
		}
}

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

function control_travel_desk_fields(frm) {
    const allowed_roles = [
        "Travel Desk User",
        "S - Accounts Executive"
    ];

    // Check if user has at least one role
    const has_allowed_role = allowed_roles.some(role => frappe.user.has_role(role));

    const fields = [
        "custom_booking_details",
        "custom_escalation_reason",
        "custom_escalated_to",
        "costing_details",
        "cost_center",
        "costings",
        "accounting_dimensions_section"
    ];

    fields.forEach(fieldname => {
        frm.set_df_property(fieldname, "read_only", !has_allowed_role);
    });
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
