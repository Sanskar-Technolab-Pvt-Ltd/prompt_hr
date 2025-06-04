

frappe.ui.form.on("Travel Request", {
	refresh: function (frm) {
		add_query_filter_to_existing_rows(frm);
	}, 	
	employee: function (frm) {
		add_query_filter_to_existing_rows(frm);
	},
	company: function (frm) {
		add_query_filter_to_existing_rows(frm);
	},
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



// ? FUNCTION TO ADD QUERY FILTER TO EXISTING ROWS
function add_query_filter_to_existing_rows(frm) {
	// ? GET EXISTING CHILD TABLE ROWS
	const rows = frm.doc.itinerary || [];
	if (!rows.length || !frm.doc.employee || !frm.doc.company) {
		return; // No rows to process
	}

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
						return {
							filters: {
								"mode_of_travel": ["in", travel_mode],
							}
						};
					};
				});
			} else {
				frappe.msgprint("Could not fetch grade for this employee.");
				console.error("Error fetching eligible travel modes:", r);
			}
		}
	});
}
