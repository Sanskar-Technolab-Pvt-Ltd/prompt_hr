// ? MAIN FORM EVENTS
frappe.ui.form.on('Expense Claim', {
    onload: function (frm) {
        if (frm.is_new()) {
            if (frm.doc.expenses && frm.doc.expenses.length > 0) {
                // ? IF NEW FORM AND EXPENSES EXIST, CLEAR THEM
                frm.clear_table("expenses");
                frm.refresh_field("expenses");
            }
        }
        if (frm.is_new() && !frm.doc.employee) {
            frappe.call({
                method: 'frappe.client.get_list',
                args: {
                    doctype: 'Employee',
                    filters: {
                        user_id: frappe.session.user
                    },
                    fields: ['name', 'employee_name'],
                    limit_page_length: 1
                },
                callback: function (r) {
                    if (r.message && r.message.length > 0) {
                        frm.set_value('employee', r.message[0].name);
                    }
                }
            });
        }
        frm.fields.forEach(field => {
            if (field.df.fieldtype === "Section Break" && field.df.collapsible) {
                field.collapse(false);  // ? OPEN BY DEFAULT
            }
        });
    },
	refresh(frm) {
        if ( !frm.is_new() && frm.doc.workflow_state == "Pending For Approval") {
            if (!frappe.user_roles.includes("S - HR Director (Global Admin)") && !frappe.user_roles.includes("S - HR L2 Manager") && !frappe.user_roles.includes("System Manager") && !frappe.user_roles.includes("S - Sales Co-ordinator") && !frappe.user_roles.includes("S - Service Coordinator") && !frappe.user_roles.includes("S - HR L5") && !frappe.user_roles.includes("S - HR Supervisor (RM)") && !frappe.user_roles.includes("S - HR L4") && !frappe.user_roles.includes("S - HR L3") && !frappe.user_roles.includes("S - HR L2") && !frappe.user_roles.includes("S - HR L1")) {
                //? DISABLE FORM ONLY FOR CREATOR
                if (frappe.session.user === frm.doc.owner) {
                    frm.disable_form();
                }
            }
        }
        // ? SERVICE ENGINEER CANNOT BE ABLE TO ADD ROWS DIRECTLY
        const roles = frappe.user_roles || [];
        const is_service_engineer = (roles.includes("S - Service Engineer") || roles.includes("Service Engineer")) && !roles.includes("System Manager");
        frm.set_df_property("expenses", "cannot_add_rows", is_service_engineer);

		add_view_field_visit_expense_button(frm);
		fetch_commute_data(frm);
		set_local_commute_monthly_expense(frm);
        set_travel_request_details(frm)
		// ? FETCH GENDER OF THE CURRENT EMPLOYEE
        if (frm.doc.employee) {
            frappe.db.get_value('Employee', frm.doc.employee, 'gender', function(r) {
                if (r && r.gender) {
                    // ? SET FILTERS FOR SHARED ACCOMODATION EMPLOYEE (BELONGS TO SAME GENDER AS EMPLOYEE AND NOT HIMSELF)
                    frm.set_query('custom_shared_accommodation_employee', 'expenses', function() {
                        return {
                            filters: {
                                name: ["!=", frm.doc.employee],
                                gender: r.gender
                            }
                        };
                    });
                }
            });
        }
        if (frm.is_new() || frm.doc.workflow_state == "Draft") {
            add_view_field_visit_expense_button(frm);
            getTourVisitExpenseDialog(frm);
            claim_extra_expenses(frm)
        }
    },
    after_save: function(frm) {  
        setTimeout(() => {  
            frm.reload_doc();  
        }, 50);  
    },
    before_workflow_action: function (frm) {

        // ! IF "REJECT" ACTION, PROCEED IMMEDIATELY
        if (frm.selected_workflow_action === "Send For Approval" || frm.selected_workflow_action === "Submit") {                        
            return Promise.resolve();
        }
        if (frm.selected_workflow_action === "Reject" && (frm.doc.custom_reason_for_rejection || "").length < 1) {
            console.log(">>> Workflow action is 'Reject' – proceeding without dialog.");
            return reason_for_rejection_dialog(frm)
        }
        
        if (frm.selected_workflow_action === "Escalate" && (frm.doc.custom_reason_for_escalation || "").length < 1) {
            return reason_for_escalation_dialog(frm)
        }

        frappe.dom.unfreeze();  // ! ENSURE UI IS UNFROZEN
        console.log(">>> Workflow action:", frm.selected_workflow_action);

        handleWorkflowTransition(frm)
        .then(() => console.log("Workflow action completed successfully."))
        .catch(() => console.log("Workflow action failed."));
    },
	employee: (frm) => { 
		fetch_commute_data(frm); 
		set_local_commute_monthly_expense(frm);
        // ? MAKE A TABLE OF TRAVEL REQUEST DETAILS
        set_travel_request_details(frm)
	},
	company: fetch_commute_data,
	project(frm) {
		setCampaignFromProject(frm);
	}
});

// ? CHILD TABLE EVENTS
frappe.ui.form.on("Expense Claim Detail", {
	expenses_add(frm, cdt, cdn) {
		reset_commute_fields(cdt, cdn);
		const grid_row = frm.fields_dict.expenses.grid.get_row(cdn);
		if (grid_row) {
			prompt_hr.utils.set_field_properties_bulk(grid_row, commute_fields, {
				hidden: true,
				read_only: true
			});
		}
	},
	expense_type(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		const grid_row = frm.fields_dict.expenses.grid.get_row(cdn);
		if (grid_row) toggle_commute_fields(frm, grid_row, row);
	},
	custom_mode_of_vehicle(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		const grid_row = frm.fields_dict.expenses.grid.get_row(cdn);
		if (grid_row) toggle_commute_fields(frm, grid_row, row);
	}
});
function make_border_red_for_is_exception_records(frm) {
    let exceptionMessages = [];
    frm?.fields_dict?.expenses?.grid?.grid_rows?.forEach((gridRow) => {
        const rowDoc = gridRow?.doc;
        const $row = $(gridRow.row);
    
        // ALWAYS RESET BORDER FIRST
        $row.css("border", "");  
    
        if (rowDoc?.custom_is_exception) {
            // APPLY RED BORDER IF EXCEPTION
            $row.css("border", "2px solid red");

            if (rowDoc?.custom_max_limit > 0) {
                // COLLECT EXCEPTION MESSAGE WITH ROW NUMBER
                exceptionMessages.push(
                    `Row ${rowDoc?.idx}: ${rowDoc?.expense_type
                    } allowance limit has been crossed by ${(rowDoc?.amount - rowDoc?.custom_max_limit
                ).toFixed(2)}`
                );
            } else {
                // COLLECT EXCEPTION MESSAGE WITH ROW NUMBER
                exceptionMessages.push(
                    `Row ${rowDoc?.idx}: ${rowDoc?.expense_type} allowance limit has been crossed.`
                );
            }
        }
        if (!rowDoc?.custom_field_visit_and_service_call_details && !rowDoc?.custom_tour_visit_details) {
            // APPLY RED BORDER IF EXCEPTION
            $row.css("border", "2px solid red");
            
            // COLLECT EXCEPTION MESSAGE WITH ROW NUMBER
            exceptionMessages.push(
                `Row ${rowDoc?.idx}: No Field Visit and Service Call details found.`
            );
        }
        
    });

    if (exceptionMessages.length > 0) {
        const html = `
            <div style="padding: 14px; background: #fff5f5; border: 1px solid #ffa8a8; 
                        border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); 
                        font-size: 14px; color: #c92a2a; margin-top: 8px;">
                <h3 style="margin-top: 0; margin-bottom: 12px; font-size: 15px; color: #a61e4d;">
                    ⚠ Expense Exceptions
                </h3>
                <ul style="margin: 0; padding-left: 20px;">
                    ${exceptionMessages.map(msg => `<li>${msg}</li>`).join("")}
                </ul>
            </div>
        `;
        
        // Append message only if not already present (to avoid duplicates)
        if (frm.fields_dict["custom_local_commute_budget_details"].$wrapper.find('.expense-exception-message').length === 0) {
            frm.fields_dict["custom_local_commute_budget_details"].$wrapper.append(`<div class="expense-exception-message">${html}</div>`);
        }
    }
}
function claim_extra_expenses(frm) {
    //? ADD EXTRA EXPENSES BUTTON
    frm.add_custom_button(__('Claim Extra Expenses'), function () {
        // ! THROW MESSAGE IF EMPLOYEE IS NOT SELECTED
        if (!frm.doc.employee) {
            frappe.msgprint({
                title: __('Missing Employee'),
                message: __('Please select an Employee before proceeding.'),
                indicator: 'red'
            });
            return;
        }
        const service_roles = ["S - Service Engineer", "Service Engineer", "S - Service Director"];
        const all_perm_roles = ["S - HR L5", "S - HR L4", "S - HR L3", "S - HR L2", "S - HR L1", "S - HR L2 Manager", "S - HR Supervisor (RM)", "System Manager", "S - HR Director (Global Admin)"]
        const sales_roles = ["S - Sales Director", "S - Sales Manager", "S - Sales Supervisor", "S - Sales Executive"];


        let userRoles = frappe.user_roles || [];

        // FUNCTION TO CHECK IF USER HAS ANY ROLE IN A GIVEN ROLE LIST
        function hasRole(roleList) {
            return roleList.some(r => userRoles.includes(r));
        }

        // ? FUNCTION TO GET SERVICE CALLS AS PER FIELD VISIT
        function load_service_calls_for_visits(field_visits) {
            return frappe.call({
                method: "prompt_hr.py.expense_claim.get_service_calls_from_field_visits",
                args: {
                    field_visits: field_visits,
                    txt: ""
                }
            }).then(r => {
                let list = (r.message || []).map(d => ({ value: d.name, label: __(d.name), description: "" }));
                return list;
            });
        }

        let defaultVisit = "";
        let expense_type_reqd = 1
        let readOnlyField = false;

        // LOGIC TO SET DEFAULT AND READONLY
        if (hasRole(all_perm_roles)) {
            defaultVisit = "General Purpose";
            expense_type_reqd = 0
            readOnlyField = false;
        } else if (hasRole(service_roles)) {
            defaultVisit = "Field Visit";
            readOnlyField = true;
        } else if (hasRole(sales_roles)) {
            defaultVisit = "Tour Visit";
            readOnlyField = true;
        }

        // CREATE DIALOG
        const dialog = new frappe.ui.Dialog({
            title: "EXTRA Expenses",
            fields: [
                {
                    label: 'Visit Type',
                    fieldname: 'visit_type',
                    fieldtype: 'Select',
                    options: "\nGeneral Purpose\nField Visit\nTour Visit",
                    default: defaultVisit,
                    reqd: 1,
                    read_only: readOnlyField,
                    onchange: function () {
                        toggleExpenseFields(dialog);
                    }
                },
                {
                    label: 'Expense Type',
                    fieldname: 'expense_type',
                    fieldtype: 'Select',
                    options: "DA\nNon DA",
                    reqd: expense_type_reqd,
                    hidden: !expense_type_reqd,
                    onchange: function () {
                        toggleExpenseFields(dialog);
                    }
                },

                {
                    label: "Add Without Field Visit and Service Call",
                    fieldname: "add_without_fv_sc",
                    fieldtype: "Check",
                    hidden: 1,
                    onchange: function () {
                        const isRequired = !dialog.get_value("add_without_fv_sc");
                        dialog.set_df_property("field_visit", "reqd", isRequired);
                        dialog.set_df_property("service_call", "reqd", isRequired);
                        dialog.set_df_property("field_visit", "hidden", !isRequired);
                        dialog.set_df_property("service_call", "hidden", !isRequired);
                        dialog.set_df_property("customer", "hidden", isRequired);
                        dialog.set_df_property("customer", "reqd", !isRequired);
                        dialog.set_df_property("from_date", "reqd", isRequired);
                        dialog.set_df_property("to_date", "reqd", isRequired);
                        dialog.set_df_property("from_date", "hidden", !isRequired);
                        dialog.set_df_property("to_date", "hidden", !isRequired);

                        dialog.fields_dict.field_visit.refresh();
                        dialog.fields_dict.service_call.refresh();
                    }
                },
                {
                    label: "Add Without Tour Visits",
                    fieldname: "add_without_tv",
                    fieldtype: "Check",
                    hidden: 1,
                    onchange: function () {
                        const isRequired = !dialog.get_value("add_without_tv");
                        dialog.set_df_property("tour_visit", "reqd", isRequired);
                        dialog.set_df_property("tour_visit", "hidden", !isRequired);
                        dialog.set_df_property("customer", "hidden", isRequired);
                        dialog.set_df_property("customer", "reqd", !isRequired);
                        dialog.set_df_property("from_date", "reqd", isRequired);
                        dialog.set_df_property("to_date", "reqd", isRequired);
                        dialog.set_df_property("from_date", "hidden", !isRequired);
                        dialog.set_df_property("to_date", "hidden", !isRequired);
                        dialog.fields_dict.field_visit.refresh();
                        dialog.fields_dict.service_call.refresh();
                    }
                },

                // ? DA FIELDS
                {
                    label: 'From Date',
                    fieldname: 'from_date',
                    fieldtype: 'Date',
                    hidden: 1,
                    onchange: function () {
                        validate_dates_debounced(dialog)
                    }
                },
                {
                    label: 'From Time',
                    fieldname: 'from_time',
                    fieldtype: 'Time',
                    hidden: 1,
                    onchange: function () {
                        validate_dates_debounced(dialog)
                    }
                },
                {
                    label: 'To Date',
                    fieldname: 'to_date',
                    fieldtype: 'Date',
                    hidden: 1,
                    onchange: function () {
                        validate_dates_debounced(dialog)
                    }
                },
                {
                    label: 'To Time',
                    fieldname: 'to_time',
                    fieldtype: 'Time',
                    hidden: 1,
                    onchange: function () {
                        validate_dates_debounced(dialog)
                    }
                },

                {
                    label: "Customer",
                    fieldname: "customer",
                    fieldtype: "MultiSelectList",
                    options: "Customer",
                    hidden: 1,
                    get_data: function (txt) {
                        return frappe.db.get_link_options("Customer", txt);
                    }
                },

                // ? NON DA FIELDS
                {
                    label: "Field Visit",
                    fieldname: "field_visit",
                    fieldtype: "MultiSelectList",
                    hidden: 1,
                    get_data: function (txt) {
                        filters = {
                            service_mode: "On Site(Customer Premise)",
                            field_visited_by: frm.doc.employee,
                            status: "Visit Completed",
                        }
                        const from_date = dialog.get_value("from_date");
                        const to_date = dialog.get_value("to_date");
                        if (from_date && to_date) {
                            const from_datetime = from_date + " 00:00:00";
                            const to_datetime = to_date + " 23:59:59";
                            filters.visit_ended = ["between", [from_datetime, to_datetime]];
                        }
                        return frappe.db.get_link_options("Field Visit", txt, filters);
                    }
                },
                {
                    label: "Service Call",
                    fieldname: "service_call",
                    fieldtype: "MultiSelectList",
                    hidden: 1,
                    get_data: function (txt) {
                        const field_visit_ids = dialog.get_value("field_visit") || [];
                        if (!field_visit_ids.length) {
                            return [];
                        }
                        return load_service_calls_for_visits(field_visit_ids).then(list => {
                            return list.filter(d => !txt || d.value.toLowerCase().includes(txt.toLowerCase()));
                        });
                    }
                },
                // ? NON DA FIELDS
                {
                    label: "Tour Visit",
                    fieldname: "tour_visit",
                    fieldtype: "MultiSelectList",
                    hidden: 1,
                    get_data: function (txt) {
                        filters = {
                            person: frm.doc.employee,
                            status: "Completed",
                        }
                        const from_date = dialog.get_value("from_date");
                        const to_date = dialog.get_value("to_date");
                        if (from_date && to_date) {
                            filters.tour_end_date = ["between", [from_date, to_date]];
                        }
                        return frappe.db.get_link_options("Tour Visit", txt, filters);
                    }
                },
                {
                    label: "Number of Row",
                    fieldname: "number_of_row",
                    fieldtype: "Int",
                    default: 1,
                    min: 1,
                    max: 4,
                    hidden: expense_type_reqd
                },
            ],
            primary_action_label: "ADD EXPENSE",
            primary_action(values) {
                if (values.number_of_row > 4) {
                    frappe.msgprint(__("Number of Row cannot be greater than 4"));
                    return;
                }

                if (values.visit_type == "General Purpose") {
                    for (let i = 0; i < values.number_of_row; i++) {
                        let new_expense = {
                        }
                        frm.add_child("expenses", new_expense);
                    }
                    frm.refresh_field("expenses");
                    dialog.hide();
                }

                else if ((values.add_without_fv_sc || values.add_without_tv) && values.expense_type == "Non DA"){
                    let customers = values.customer;
                    let customer_list = Array.isArray(customers) ? customers.join(", ") : customers;
                    for (let i = 0; i < values.number_of_row; i++) {
                        let new_expense = {
                            "custom_customer_details": customer_list, 
                        };
                        frm.add_child("expenses", new_expense);
                    }
                    frm.refresh_field("expenses");
                    dialog.hide();
                }
                else if (values.expense_type == "DA") {
                    add_extra_da(frm, values.from_date, values.from_time, values.to_date, values.to_time, values.customer)
                    dialog.hide();

                }
                else if (values.expense_type == "Non DA" && values.visit_type == "Field Visit") {

                const selected_field_visits = values.field_visit || [];
                const selected_service_calls = values.service_call || [];

                //? CALL BACKEND TO GET FORMATTED COMMA-SEPARATED STRINGS
                frappe.call({
                    method: "prompt_hr.py.expense_claim.get_field_visit_service_call_details",
                    args: {
                        field_visits: selected_field_visits,
                        service_calls: selected_service_calls
                    },
                    callback: function (r) {
                        if (!r.exc && r.message) {
                            const expense = {
                                expense_date: values.from_date,
                                custom_expense_end_date: values.to_date,
                                custom_field_visits: r.message.custom_field_visit,
                                custom_service_calls: r.message.custom_service_call,
                                custom_field_visit_and_service_call_details: r.message.custom_field_visit_and_service_call_details,
                            };
                            for (let i = 0; i < values.number_of_row; i++) {
                                frm.add_child("expenses", expense);
                            }
                            frm.refresh_field("expenses");
                            dialog.hide();
                        }
                    }
                });
            }
                else if (values.expense_type == "Non DA" && values.visit_type == "Tour Visit") {

                    const selected_tour_visits = values.tour_visit

                    //? CALL BACKEND TO GET FORMATTED COMMA-SEPARATED STRINGS
                    frappe.call({
                        method: "prompt_hr.py.expense_claim.get_tour_visit_details",
                        args: {
                            tour_visits: selected_tour_visits,
                        },
                        callback: function (r) {
                            if (!r.exc && r.message) {
                                const expense = {
                                    custom_tour_visits: r.message.custom_tour_visits,
                                    custom_tour_visit_details: r.message.custom_tour_visit_details,
                                    expense_date: values.from_date,
                                    custom_expense_end_date: values.to_date,
                                };
                                for (let i = 0; i < values.number_of_row; i++) {
                                    frm.add_child("expenses", expense);
                                }
                                frm.refresh_field("expenses");
                                dialog.hide();
                            }
                        }
                    });
                }
            }

        });

        function toggleExpenseFields(dialog) {
            let expenseType = dialog.get_value("expense_type");
            let visit_type = dialog.get_value("visit_type");
        
            // RESET ALL TO HIDDEN + NOT REQUIRED
            ["from_date", "from_time", "to_date", "to_time", "tour_visit",
            "field_visit", "service_call", "number_of_row", "add_without_fv_sc", "add_without_tv", "customer"]
                .forEach(f => {
                    dialog.set_df_property(f, "hidden", 1);
                    dialog.set_df_property(f, "reqd", 0);
                });
            if (visit_type === "General Purpose") {
                dialog.set_df_property("expense_type", "reqd", 0)
                dialog.set_df_property("expense_type", "hidden", 1)
                dialog.set_df_property("number_of_row", "hidden", 0)
            }
            else {
                dialog.set_df_property("expense_type", "hidden", 0)
                dialog.set_df_property("expense_type", "reqd", 1)
                if (expenseType === "DA") {
                    // SHOW + REQUIRE DA FIELDS
                    ["from_date", "from_time", "to_date", "to_time", "customer"].forEach(f => {
                        dialog.set_df_property(f, "hidden", 0);
                        dialog.set_df_property(f, "reqd", 1);
                    });
                } else if (expenseType === "Non DA") {
                    if (visit_type === "Field Visit") {
                        ["field_visit", "from_date", "to_date", "service_call", "number_of_row", "add_without_fv_sc"].forEach(f => {
                            dialog.set_df_property(f, "hidden", 0);
                        });
                        ["field_visit", "service_call", "from_date", "to_date",].forEach(f => {
                            dialog.set_df_property(f, "reqd", 1);
                        });
                        dialog.set_value("add_without_fv_sc", 0);
                    } else if (visit_type === "Tour Visit") {

                        ["tour_visit","number_of_row", "add_without_tv", "from_date", "to_date"].forEach(f => {
                            dialog.set_df_property(f, "hidden", 0);
                        });
                            dialog.set_df_property("tour_visit", "reqd", 1);
                            dialog.set_df_property("from_date", "reqd", 1);
                            dialog.set_df_property("to_date", "reqd", 1);
                            dialog.set_value("add_without_tv", 0);
                    }
                }
            }
        
            dialog.refresh();
        }

        dialog.show();
    });
}


function reason_for_rejection_dialog(frm) {
    return new Promise((resolve, reject) => {
        frappe.dom.unfreeze()
        
        frappe.prompt({
            label: 'Reason for rejection',
            fieldname: 'reason_for_rejection',
            fieldtype: 'Small Text',
            reqd: 1
        }, (values) => {
            if (values.reason_for_rejection) {
                frm.set_value("custom_reason_for_rejection", values.reason_for_rejection)
                frm.set_value("approval_status", "Rejected")
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
                frm.set_value("custom_reason_for_escalation", values.reason_for_escalation)
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


// ? FETCH COMMUTE DATA AND BIND EVENTS
function fetch_commute_data(frm) {
	const { employee, company } = frm.doc;
	if (!employee || !company) return;

	frappe.call({
		method: "prompt_hr.py.expense_claim.get_data_from_expense_claim_as_per_grade",
		args: { employee, company },
		callback: ({ message }) => {
			if (!message?.success) return;

			const commuteData = {
				public: message.data.allowed_local_commute_public || [],
				non_public: message.data.allowed_local_commute_non_public || []
			};

			// ? SAVE TO LOCAL STORAGE
			const key = `commute_options_${employee}_${company}`;
			localStorage.setItem(key, JSON.stringify(commuteData));

			// ? BIND CLICK EVENTS TO COMMUTE FIELDS
			commute_fields.forEach(field => {
				prompt_hr.utils.apply_click_event_on_field(
					frm,
					"expenses",
					field,
					(row_doc) => {
						const grid_row = frm.fields_dict.expenses.grid.get_row(row_doc.name);
						if (grid_row) toggle_commute_fields(frm, grid_row, row_doc);
					},
					true
				);
			});

			// ? TOGGLE ON FORM OPEN
			frm.fields_dict.expenses.grid.wrapper.on("click", ".grid-row", function () {
				const row_name = $(this).data("name");
				const grid_row = frm.fields_dict.expenses.grid.get_row(row_name);
				if (grid_row?.grid_form) {
					grid_row.grid_form.on("form_render", () => {
						toggle_commute_fields(frm, grid_row, grid_row.doc);
					});
				}
			});

			// ? TOGGLE EXISTING ROWS
			frm.doc.expenses?.forEach(row => {
				const grid_row = frm.fields_dict.expenses.grid.get_row(row.name);
				if (grid_row) toggle_commute_fields(frm, grid_row, row);
			});
		}
	});
}

// ? FIELDS TO MANAGE
const commute_fields = ["custom_mode_of_vehicle", "custom_type_of_vehicle", "custom_km"];

// ? TOGGLE FIELDS BASED ON CONDITIONS
function toggle_commute_fields(frm, grid_row, row) {
	const isLocalCommute = row.expense_type === "Local Commute";

	// ? Show or hide commute fields
	prompt_hr.utils.set_field_properties_bulk(grid_row, commute_fields, {
		hidden: !isLocalCommute,
		read_only: !isLocalCommute
	});

	if (!isLocalCommute) {
		reset_amount_read_only(grid_row);
		return;
	}

	// ? Update vehicle options
	update_type_of_vehicle_options(frm, row.custom_mode_of_vehicle);

	// ? Set or reset amount read-only
	if (row.custom_mode_of_vehicle === "Non-Public") {
		set_amount_read_only(grid_row);
	} else {
		reset_amount_read_only(grid_row);
	}
}

// ? RESET VEHICLE FIELDS
function reset_commute_fields(cdt, cdn) {
	commute_fields.forEach(field => frappe.model.set_value(cdt, cdn, field, ""));
}

// ? UPDATE VEHICLE TYPE OPTIONS
function update_type_of_vehicle_options(frm, mode) {
	const key = `commute_options_${frm.doc.employee}_${frm.doc.company}`;
	const stored = localStorage.getItem(key);
	if (!stored) return;

	const commuteData = JSON.parse(stored);
	const options = [...(mode === "Public" ? commuteData.public : commuteData.non_public || [])];

	prompt_hr.utils.update_select_field_options(frm, {
		table_field: "expenses",
		fieldname: "custom_type_of_vehicle",
		options
	});
}

// ? MARK AMOUNT READ-ONLY
function set_amount_read_only(grid_row) {
	const row = grid_row.doc;

	grid_row.set_field_property("amount", "read_only", true);

	// ? SET TO ZERO ONLY IF NOT ALREADY SET
	if (row.amount == null) {
		frappe.model.set_value(row.doctype, row.name, "amount", 0);
	}

	// ? FOR EXPANDED FORM MODE
	if (grid_row.grid_form?.fields_dict?.amount) {
		grid_row.grid_form.fields_dict.amount.df.read_only = 1;
		grid_row.grid_form.fields_dict.amount.refresh();
	}
}

// ? UNMARK AMOUNT READ-ONLY
function reset_amount_read_only(grid_row) {
	grid_row.set_field_property("amount", "read_only", false);

	if (grid_row.grid_form?.fields_dict?.amount) {
		grid_row.grid_form.fields_dict.amount.df.read_only = 0;
		grid_row.grid_form.fields_dict.amount.refresh();
	}
}

// ? PLACEHOLDER FOR CAMPAIGN MAPPING
function setCampaignFromProject(frm) {
	// Add your logic here if needed
}


function set_local_commute_monthly_expense(frm) {
    if (!frm.doc.employee) {
        const html = `
            <div style="padding: 16px; background: #fff3cd; border: 1px solid #ffeeba; border-radius: 8px; color: #856404;">
                <strong>No Employee Selected</strong><br>
                Please select an employee to view their Local Commute budget details.
            </div>
        `;
        frm.set_df_property("custom_local_commute_budget_details", "options", html);
        frm.refresh_field("custom_local_commute_budget_details");
        frappe.msgprint(("Please select an employee first."));
        return;
    }

    frappe.call({
    method: "prompt_hr.py.expense_claim.get_local_commute_expense_in_expense_claim",
    args: { employee: frm.doc.employee },
    callback: (res) => {
        const data = res.message;
        let html = "";

        if (!data) {
            html = `
                <div style="padding: 16px; background: #fff3cd; border: 1px solid #ffeeba; border-radius: 8px; color: #856404;">
                    <strong>Commute budget details are not available for this employee.</strong><br>
                    Please ensure the employee has a configured Local Commute budget.
                </div>
            `;
        } else {
            const budget = parseFloat(data.monthly_budget) || 0;
            const spent = parseFloat(data.monthly_expense) || 0;
            const remaining = parseFloat(data.remaining_budget) || 0;
            const utilization = budget > 0 ? Math.round((spent / budget) * 100) : 0;

            const statusColor = utilization >= 90
                ? "#e03131"  // Red
                : utilization >= 80
                ? "#f08c00"  // Amber
                : "#2f9e44"; // Green

            html = `
                <div style="padding: 14px; background: #f9fafb; border: 1px solid #d1d5db; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); font-size: 14px;">
                    <h3 style="margin-top: 0; margin-bottom: 12px; color: #333; font-size: 16px;">Local Commute Budget Details</h3>
                    <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                        <strong>Monthly Budget</strong>
                        <span style="color: #0b7285; font-size: 14px; font-weight: bold;">
                            ${budget > 0 ? `₹${budget.toLocaleString('en-IN')}` : "On Actuals"}
                        </span>
                    </div>
                    <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                        <strong>Amount Spent This Month</strong>
                        <span style="color: #e03131; font-size: 14px; font-weight: bold;">₹${spent.toLocaleString('en-IN')}</span>
                    </div>
                    ${budget > 0 ? `
                        <div style="display: flex; justify-content: space-between;">
                            <strong>Remaining Budget</strong>
                            <span style="color: #2f9e44; font-size: 14px; font-weight: bold;">₹${remaining.toLocaleString('en-IN')}</span>
                        </div>` : ``}
                </div>
            `;
        }

        frm.set_df_property("custom_local_commute_budget_details", "options", html);
        frm.refresh_field("custom_local_commute_budget_details");
        make_border_red_for_is_exception_records(frm)
    },
    error: (err) => {
        frappe.msgprint("Error fetching commute budget details.");
        console.error(err);
    }
});

}



//? ADDS "VIEW FIELD VISIT EXPENSES" BUTTON IF USER HAS SPECIFIC ROLE
function add_view_field_visit_expense_button(frm) {
    // ? DEFINE ALLOWED ROLES FOR BUTTON VISIBILITY
    const allowed_roles = ['Service Engineer', 'S - HR Director (Global Admin)', "S - Service Engineer", "System Manager", "S - HR L5", "S - HR L4", "S - HR L3", "S - HR L2", "S - HR L1", "S - HR L2 Manager", "S - HR Supervisor (RM)"];

    // ? CHECK IF CURRENT USER HAS ANY OF THE ALLOWED ROLES
    let can_show = 0;
    allowed_roles.forEach(role => {
        if (frappe.user.has_role(role)) {
            // ? ONLY SHOWED BUTTON IF STATE IS PENDING
            if (frm.doc.workflow_state == "Draft") {
                can_show = 1;
            }
        }
    });

    // //? EXIT IF USER ROLE NOT PERMITTED
    if (!can_show) return;

    //? ADD CUSTOM BUTTON TO THE FORM
    frm.add_custom_button(__('Get Field Visit Expenses'), function () {
        const employee = frm.doc.employee;
        const is_new = frm.is_new()
        let expense_claim_name = ""
        if (!is_new) {
            expense_claim_name = frm.doc.name
        }
        //? CHECK IF CURRENT USER IS HR USER OR HR MANAGER
        const can_edit_employee = frappe.user.has_role('S - HR Director (Global Admin)') || frappe.user.has_role("System Manager");
        //? CREATE DIALOG TO ENTER FIELD VISIT DETAILS
        const dialog = new frappe.ui.Dialog({
            title: 'Field Visit Details',
            fields: [
                {
                    label: 'Employee',
                    fieldname: 'employee',
                    fieldtype: 'Link',
                    options: 'Employee',
                    reqd: 1,
                    default: employee,
                    hidden: !is_new,
                    onchange: function () {
                        if (dialog.get_value("employee")) {
                            frappe.db.get_value('Employee', dialog.get_value("employee"), 'employee_name')
                                .then(r => {
                                    if (r.message) {
                                        dialog.set_value('employee_name', r.message.employee_name);
                                    }
                                });
                        }
                        else {
                            dialog.set_value('employee_name', "")
                        }
                    }

                },
                {
                    label: 'Employee Name',
                    fieldname: 'employee_name',
                    fieldtype: 'Data',
                    hidden: !is_new,
                    read_only: 1
                },
                {
                    label: 'From Date',
                    fieldname: 'from_date',
                    fieldtype: 'Date',
                    reqd: 1,
                    onchange: function() {
                        validate_dates_debounced(dialog)
                    }
                },
                {
                    label: 'To Date',
                    fieldname: 'to_date',
                    fieldtype: 'Date',
                    reqd: 1,
                    onchange: function() {
                        validate_dates_debounced(dialog)
                    }
                }
            ],
            primary_action_label: 'Fetch Expense Claims',
            primary_action(values) {

                frappe.call({
                    method: 'prompt_hr.py.expense_claim.get_date_wise_da_hours',
                    args: {
                        employee: values.employee,
                        from_date: values.from_date,
                        to_date: values.to_date,
                        company: frm.doc.company || "",
                        expense_claim_name: expense_claim_name,
                        type: "Field Visit"
                    },
                    callback(r) {
						try {
							if (!r.exc && r.message) {
								const { expense_claim_name, da_expense_rows, commute_expense_rows, summary_html } = r.message;

								if ((da_expense_rows?.length || commute_expense_rows?.length)) {
									if (frm.is_new()) {
										frm.doc.employee = values.employee;
										frm.doc.approval_status = "Draft";
										frm.doc.custom_type = "Field Visit";
										frm.doc.expenses = [];

										frm.refresh_field("employee");
										frm.refresh_field("approval_status");
										frm.refresh_field("custom_type");
										frm.refresh_field("expenses");
									}

									show_summary_and_insert(summary_html, da_expense_rows, commute_expense_rows);
								} else {
									frappe.msgprint(__('No entries found for selected date range.'));
								}
							}
						} 
						finally {
							dialog.hide();  // ✅ always executed
						}
					}
									});

                function show_summary_and_insert(summary_html, da_expense_rows, commute_expense_rows) {
                    frappe.msgprint({
                        title: __('Expense Claim Summary'),
                        message: summary_html,
                    });

                    [...(da_expense_rows || []), ...(commute_expense_rows || [])].forEach(row => {
                        frm.add_child('expenses', row);
                    });
                    frm.refresh_field('expenses');
                    check_and_remove_expense_buttons(frm)
                }
            }

        });

        //? FETCH EMPLOYEE NAME FROM EMPLOYEE DOC IF SET
        if (employee) {
            frappe.db.get_value('Employee', employee, 'employee_name')
                .then(r => {
                    if (r.message) {
                        dialog.set_value('employee_name', r.message.employee_name);
                    }
                });
        }

        //? SHOW THE DIALOG
        dialog.show();
    });
}

// ? FUNCTION FOR BUTTON TO ADD TOUR VISIT EXPENSE - MODIFIED TO FEED DATA INTO CURRENT FORM
function getTourVisitExpenseDialog(frm) {
    const allowed_roles = ['S - HR Director (Global Admin)', "System Manager", "S - HR L5", "S - HR L4", "S - HR L3", "S - HR L2", "S - HR L1", "S - HR L2 Manager", "S - HR Supervisor (RM)", "S - Sales Director", "S - Sales Manager", "S - Sales Supervisor", "S - Sales Executive"];
    const user_roles = frappe.user_roles;

    const has_access = user_roles.some(role => allowed_roles.includes(role));
    if (!has_access) return;

    frm.add_custom_button('Get Tour Visit Expense', () => {
        const employee = frm.doc.employee;
        const is_new = frm.is_new();
        let expense_claim_name = "";
        if (!is_new) {
            expense_claim_name = frm.doc.name;
        }

        const is_hr = user_roles.includes('S - HR Director (Global Admin)') || user_roles.includes('S - HR Supervisor (RM)') || user_roles.includes('S - HR L2 Manager');
        const is_sales = user_roles.includes('Sales User') || user_roles.includes('Sales Manager');

        //? CHECK IF CURRENT USER CAN EDIT EMPLOYEE FIELD
        const can_edit_employee = frappe.user.has_role('S - HR Director (Global Admin)') || frappe.user.has_role('S - HR Supervisor (RM)') || frappe.user.has_role('S - HR L2 Manager');

        // ? GET DEFAULT EMPLOYEE FOR SALES USERS
        let default_employee = employee;
        if (is_sales && !is_hr && !default_employee) {
            frappe.call({
                method: 'frappe.client.get_list',
                args: {
                    doctype: 'Employee',
                    filters: { user_id: frappe.session.user },
                    fields: ['name']
                },
                callback: function (r) {
                    const employee_id = r.message?.[0]?.name || '';
                    show_dialog(employee_id);
                }
            });
        } else {
            show_dialog(default_employee);
        }

        function show_dialog(default_emp) {
            const dialog = new frappe.ui.Dialog({
                title: 'Tour Visit Expense Details',
                fields: [
                    {
                        label: 'Employee',
                        fieldname: 'employee',
                        fieldtype: 'Link',
                        options: 'Employee',
                        reqd: 1,
                        default: default_emp,
                        hidden: !is_new,
                        read_only: !can_edit_employee,
                        onchange: function () {
                            if (dialog.get_value("employee")) {
                                frappe.db.get_value('Employee', dialog.get_value("employee"), 'employee_name')
                                    .then(r => {
                                        if (r.message) {
                                            dialog.set_value('employee_name', r.message.employee_name);
                                        }
                                    });
                            }
                            else {
                                dialog.set_value('employee_name', "")
                            }
                        }
    
                    },
                    {
                        label: 'Employee Name',
                        fieldname: 'employee_name',
                        fieldtype: 'Data',
                        hidden: !is_new,
                        read_only: 1
                    },
                    {
                        label: 'From Date',
                        fieldname: 'from_date',
                        fieldtype: 'Date',
                        reqd: 1,
                        onchange: function() {
                            validate_dates_debounced(dialog)
                        }
                    },
                    {
                        label: 'To Date',
                        fieldname: 'to_date',
                        fieldtype: 'Date',
                        reqd: 1,
                        onchange: function() {
                            validate_dates_debounced(dialog)
                        }
                    }
                ],
                primary_action_label: 'Fetch Tour Visit Expenses',
                primary_action(values) {
                    frappe.call({
                        method: 'prompt_hr.py.expense_claim.process_tour_visit_da',
                        args: {
                            employee: values.employee,
                            company: frm.doc.company || "",
                            from_date: values.from_date,
                            to_date: values.to_date,
                            expense_claim_name: expense_claim_name,
                            type: "Tour Visit"
                        },
                        callback(r) {
                            if (!r.exc && r.message) {
                                const { da_expense_rows, summary_html } = r.message;

                                if (da_expense_rows?.length) {
                                    if (frm.is_new()) {
                                        // * FOR NEW DOC: SET BASIC INFO AND CLEAR EXPENSES
                                        frm.doc.employee = values.employee;
                                        frm.doc.approval_status = "Draft";
                                        frm.doc.custom_type = "Tour Visit";
                                        frm.doc.expenses = [];
                                        frm.doc.custom_tour_visit = values.tour_visit;

                                        // ? REFRESH THE FIELDS TO MAKE THEM VISIBLE IN UI
                                        frm.refresh_field("employee");
                                        frm.refresh_field("approval_status");
                                        frm.refresh_field("custom_type");
                                        frm.refresh_field("expenses");
                                        frm.refresh_field("custom_tour_visit")
                                    }

                                    show_summary_and_insert(summary_html, da_expense_rows);
                                } else {
                                    frappe.msgprint(__('No expenses found for selected tour visit.'));
                                }
                                dialog.hide();
                            }
                        }
                    });

                    function show_summary_and_insert(summary_html, da_expense_rows) {
                        frappe.msgprint({
                            title: __('Tour Visit Expense Summary'),
                            message: summary_html,
                        });

                        da_expense_rows.forEach(row => {
                            frm.add_child('expenses', row);
                        });
                        frm.refresh_field('expenses');
                        check_and_remove_expense_buttons(frm)
                    }
                }
            });

            //? FETCH EMPLOYEE NAME FROM EMPLOYEE DOC IF SET
            if (default_emp) {
                frappe.db.get_value('Employee', default_emp, 'employee_name')
                    .then(r => {
                        if (r.message) {
                            dialog.set_value('employee_name', r.message.employee_name);
                        }
                    });
            }

            //? SHOW THE DIALOG
            dialog.show();
        }
    });
}

function add_extra_da(frm, from_date, from_time, to_date, to_time, customers) {
    //? CONVERT STRING TO DATE OBJECTS
    let start_date = frappe.datetime.str_to_obj(from_date);
    let end_date = frappe.datetime.str_to_obj(to_date);

    //? LOOP THROUGH EACH DATE
    for (let d = new Date(start_date); d <= end_date; d.setDate(d.getDate() + 1)) {

        //? CLONE CURRENT DATE
        let expense_date = new Date(d);

        //? DETERMINE START & END TIME
        let current_start_time, current_end_time;

        if (expense_date.getTime() === start_date.getTime()) {
            //? FIRST DATE → USE GIVEN START TIME
            current_start_time = from_time;
        } else {
            //? MIDDLE OR LAST DATE → DEFAULT 00:00:00
            current_start_time = "00:00:00";
        }

        if (expense_date.getTime() === end_date.getTime()) {
            //? LAST DATE → USE GIVEN END TIME
            current_end_time = to_time;
        } else {
            //? FIRST OR MIDDLE DATE → DEFAULT 23:59:59
            current_end_time = "23:59:59";
        }

        //? PREPARE CUSTOMER LIST STRING
        let customer_list = Array.isArray(customers) ? customers.join(", ") : customers;

        //? CREATE CHILD RECORD
        let new_expense = {
            "expense_date": frappe.datetime.obj_to_str(expense_date),
            "custom_expense_end_date": frappe.datetime.obj_to_str(expense_date),
            "custom_expense_start_time": current_start_time,
            "custom_expense_end_time": current_end_time,
            "custom_customer_details": customer_list,
            "expense_type": "DA",
            "amount": 0,
            "sanctioned_amount": 0,
            "custom_da_adjustment_type": "Not Applicable",
        };

        frm.add_child("expenses", new_expense);
    }

    //? REFRESH CHILD TABLE
    frm.refresh_field("expenses");
}

function check_and_remove_expense_buttons(frm) {
    const expenses = frm.doc.expenses || [];

    if (!frm.is_new()) return;

    if (
        expenses.length > 1 ||
        (expenses.length === 1 && expenses[0].expense_type?.trim() !== "")
    ) {
        frm.remove_custom_button("Get Field Visit Expenses");
        frm.remove_custom_button("Get Tour Visit Expense");
    }
}

function set_travel_request_details(frm) {
    if (!frm.doc.employee) {
        const html = `
            <div style="padding: 16px;background: #fff3cd; border: 1px solid #ffeeba; border-radius: 8px; color: #856404;">
                <strong>No Employee Selected</strong><br>
                Please select an employee to view their Travel Request details.
            </div>
        `;
        frm.set_df_property("custom_travel_request_details", "options", html);
        frm.refresh_field("custom_travel_request_details");
        return;
    }

    frappe.call({
        method: "prompt_hr.py.expense_claim.get_travel_request_details",
        args: { employee: frm.doc.employee },
        callback: (res) => {
            const data = res.message;
            let html = "";

            if (!data || data.length === 0) {
                html = `
                    <div style="padding: 16px; background: #fff3cd; border: 1px solid #ffeeba; border-radius: 8px; color: #856404;">
                        <strong>Travel Request details are not available for this employee.</strong><br>
                    </div>
                `;
            } else {
                data.forEach(request => {
                    html += `
                        <div style="border: 1px solid #ccc; border-radius: 8px; margin-bottom: 24px; padding: 12px; background: #fafafa;">
                            <div style="display: flex; justify-content: space-between; align-items: center; font-weight: 600; margin-bottom: 8px;">
                                <div>
                                    Travel Request - 
                                    <a href="${frappe.urllib.get_base_url()}/app/travel-request/${request.parent}" target="_blank" 
                                       style="text-decoration: none; color: #0275d8;">
                                       ${request.parent}
                                    </a>
                                </div>
                                <div style="color: #555;">${request.workflow_state}</div>
                            </div>

                            <!-- Travel Itinerary Label -->
                            <div style="font-weight: 600; margin: 6px 0; color: #333;">Travel Itinerary</div>
                            <div style="max-height: 180px; overflow-y: auto; border: 1px solid #ddd; border-radius: 4px; margin-bottom: 12px;">
                                <table style="width: 100%; border-collapse: collapse; font-size: 13px;">
                                    <thead style="background: #e9ecef;">
                                        <tr>
                                            ${request.travel_itinerary_data.length > 0
                        ? request.travel_itinerary_label.map(field => `
                                                    <th style="border: 1px solid #ccc; padding: 6px; text-align: left;">
                                                        ${field}
                                                    </th>`).join('')
                        : `<th style="padding: 6px;">No Itinerary Data</th>`
                    }
                                        </tr>
                                    </thead>
                                    <tbody>
                                        ${request.travel_itinerary_data.length > 0
                        ? request.travel_itinerary_data.map(row => {
                            const cols = Object.values(row).map(val => {
                                const isAttach = val && typeof val === 'string' &&
                                    (val.endsWith('.jpg') || val.endsWith('.png') || val.endsWith('.jpeg') || val.endsWith('.gif') ||
                                        val.endsWith('.pdf') || val.endsWith('.docx'));
                                if (isAttach) {
                                    return `<td style="border: 1px solid #ccc; padding: 6px;">
                                                <a href="${frappe.urllib.get_base_url()}${val}" target="_blank" style="color: #0275d8; font-weight: 600; cursor: pointer; text-decoration: underline;">
                                                    View
                                                </a>
                                            </td>`;
                                } else {
                                    return `<td style="border: 1px solid #ccc; padding: 6px;">${val || ''}</td>`;
                                }
                            });
                            return `<tr>${cols.join('')}</tr>`;
                        }).join('')
                        : ''
                    }
                                    </tbody>
                                </table>
                            </div>

                            <!-- Cost Label -->
                            <div style="font-weight: 600; margin: 6px 0; color: #333;">Costing Details</div>
                            <div style="max-height: 140px; overflow-y: auto; border: 1px solid #ddd; border-radius: 4px;">
                                <table style="width: 100%; border-collapse: collapse; font-size: 13px;">
                                    <thead style="background: #e9ecef;">
                                        <tr>
                                            ${request.cost_data.length > 0
                        ? request.cost_data_label.map(field => `
                                                    <th style="border: 1px solid #ccc; padding: 6px; text-align: left;">
                                                        ${field.replace(/_/g, ' ').toUpperCase()}
                                                    </th>`).join('')
                        : `<th style="padding: 6px;">No Cost Data</th>`
                    }
                                        </tr>
                                    </thead>
                                    <tbody>
                                        ${request.cost_data.length > 0
                        ? request.cost_data.map(row => {
                            const cols = Object.values(row).map(val => {
                                const isAttach = val && typeof val === 'string' &&
                                    (val.endsWith('.jpg') || val.endsWith('.png') || val.endsWith('.jpeg') || val.endsWith('.gif') ||
                                        val.endsWith('.pdf') || val.endsWith('.docx'));
                                if (isAttach) {
                                    return `<td style="border: 1px solid #ccc; padding: 6px;">
                                                <a href="${frappe.urllib.get_base_url()}${val}" target="_blank" style="color: #0275d8; font-weight: 600; cursor: pointer; text-decoration: underline;">
                                                    View
                                                </a>
                                            </td>`;
                                }
                                else {
                                    return `<td style="border: 1px solid #ccc; padding: 6px;">${val || ''}</td>`;
                                }
                            });
                            return `<tr>${cols.join('')}</tr>`;
                        }).join('')
                        : ''
                    }
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    `;
                });
            }

            frm.fields_dict['custom_travel_request_details'].wrapper.innerHTML = html;

            frm.set_df_property("custom_travel_request_details", "options", html);
            frm.refresh_field("custom_travel_request_details");
        },
        error: (err) => {
            frappe.msgprint("Error fetching travel request details.");
            console.error(err);
        }
    });
}

function validate_dates(dialog) {
    const from_date = dialog.get_value("from_date");
    const to_date = dialog.get_value("to_date");
    const from_time = dialog.get_value("from_time");
    const to_time = dialog.get_value("to_time");

    // ! VALIDATE THAT START DATE IS NOT GREATER THAN END DATE
    if (from_date && to_date && frappe.datetime.str_to_obj(from_date) > frappe.datetime.str_to_obj(to_date)) {
        dialog.set_value("from_date", "");
        dialog.set_value("to_date", "");
        frappe.throw(__("From Date cannot be after To Date"));
    }

    if (from_date && frappe.datetime.str_to_obj(from_date) > frappe.datetime.str_to_obj(frappe.datetime.get_today())) {
        dialog.set_value("from_date", "");
        frappe.throw(__("From Date cannot be a future date"));
    }

    if (to_date && frappe.datetime.str_to_obj(to_date) > frappe.datetime.str_to_obj(frappe.datetime.get_today())) {
        dialog.set_value("to_date", "");
        frappe.throw(__("To Date cannot be a future date"));
    }
    


    // ! VALIDATE THAT COMBINED FROM DATETIME IS NOT GREATER THAN TO DATETIME
    if (from_date && to_date && from_time && to_time) {
        const from_datetime_str = `${from_date} ${from_time}`;
        const to_datetime_str = `${to_date} ${to_time}`;

        const from_datetime = frappe.datetime.str_to_obj(from_datetime_str);
        const to_datetime = frappe.datetime.str_to_obj(to_datetime_str);

        if (from_datetime > to_datetime) {
            dialog.set_value("from_time", "");
            dialog.set_value("to_time", "");
            frappe.throw(__("From Date & Time cannot be after To Date & Time"));
        }
    }
}


// Debounce helper function
function debounce(func, wait) {
    let timeout;
    return function(...args) {
        clearTimeout(timeout);
        timeout = setTimeout(() => func.apply(this, args), wait);
    };
}

// Wrap the validate_dates function with debounce of 300 ms (adjust as needed)
const validate_dates_debounced = debounce(validate_dates, 300);


function handleWorkflowTransition(frm) {
    return new Promise((resolve, reject) => {

        console.log(">>> Fetching transitions for the current document...");

        frappe.workflow.get_transitions(frm.doc).then(transitions => {
            console.log("<<< Transitions fetched:", transitions);

            const selected_transition = transitions.find(
                t => t.action === frm.selected_workflow_action
            );

            const target_state = selected_transition ? selected_transition.next_state : null;
            console.log(">>> Selected transition:", selected_transition);
            console.log(">>> Target workflow state:", target_state);

            let dialog_fields = [];

            if (target_state === "Sent to Accounting Team") {
                frappe.call({
                    method: "prompt_hr.py.expense_claim.send_mail_to_accounting_team",
                    args: {
                        doctype: cur_frm.doctype,
                        docname: cur_frm.docname
                    },
                    callback: function (r) {
                        if (r.message && r.message.status === "success") {
                            frappe.msgprint(`Document Mailed To Accounting Team successfully.`);
                            resolve();
                        } else {
                            frappe.msgprint("Failed to share document.");
                            reject();
                        }
                    },
                    error: function (err) {
                        console.error("!!! Error during API call:", err);
                        frappe.msgprint("Error occurred while emailing document.");
                        reject();
                    }
                });
            
            } else {
                console.log(">>> Target state is NOT 'Sent to Accounting Team' – show all Employees, hide Role field.");

                dialog_fields = [
                    {
                        label: "Employee",
                        fieldname: "employee",
                        fieldtype: "Link",
                        options: "Employee",
                        reqd: 1,
                        get_query: function () {
                            console.log(">>> get_query called for Employee – no filter.");
                            return {};
                        }
                    }
                ];
            
                let dialog = new frappe.ui.Dialog({
                    title: __("Confirm {0}", [frm.selected_workflow_action]),
                    fields: dialog_fields,
                    primary_action_label: "Send For Approval",
                    primary_action: function (values) {
                        console.log(">>> Primary action triggered with values:", values);

                        dialog.hide();

                        console.log(">>> Calling backend API to share document...");
                        frappe.call({
                            method: "prompt_hr.py.utils.share_doc_with_employee",
                            args: {
                                employee: values.employee,
                                doctype: cur_frm.doctype,
                                docname: cur_frm.docname
                            },
                            callback: function (r) {
                                console.log("<<< API response:", r);

                                if (r.message && r.message.status === "success") {
                                    frappe.msgprint(`Document shared with ${values.employee} successfully.`);
                                    resolve();
                                } else {
                                    frappe.msgprint("Failed to share document.");
                                    console.log("!!! Document sharing failed, rejecting workflow.");
                                    reject();
                                }
                            },
                            error: function (err) {
                                console.error("!!! Error during API call:", err);
                                frappe.msgprint("Error occurred while sharing document.");
                                reject();
                            }
                        });
                    }
                });

                console.log(">>> Showing dialog to user...");
                dialog.show();
            }
        });
    });
}
