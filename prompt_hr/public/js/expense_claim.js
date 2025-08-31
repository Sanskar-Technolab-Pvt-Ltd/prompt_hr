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

		create_payment_entry_button(frm);
		add_view_field_visit_expense_button(frm);
		fetch_commute_data(frm);
		set_local_commute_monthly_expense(frm);
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
        claim_extra_field_visit_expenses(frm)
    },
    after_save: function(frm) {  
        setTimeout(() => {  
            frm.reload_doc();  
        }, 50);  
    },
    before_workflow_action: function (frm) {

        // ! IF "REJECT" ACTION, PROCEED IMMEDIATELY
        if (frm.selected_workflow_action === "Reject" || frm.selected_workflow_action === "Send For Approval") {
            console.log(">>> Workflow action is 'Reject' – proceeding without dialog.");
            return Promise.resolve();
        }

        frappe.dom.unfreeze();  // ! ENSURE UI IS UNFROZEN
        console.log(">>> Workflow action:", frm.selected_workflow_action);

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
                    console.log(">>> Target state is 'Sent to Accounting Team' – filtering Employees by 'Accounts User' role.");

                    dialog_fields = [
                        {
                            label: "Role",
                            fieldname: "role",
                            fieldtype: "Link",
                            options: "Role",
                            reqd: 1,
                            default: "Accounts User",
                            read_only: 1
                        },
                        {
                            label: "Employee",
                            fieldname: "employee",
                            fieldtype: "Link",
                            options: "Employee",
                            reqd: 1,
                            get_query: function () {
                                console.log(">>> get_query called for Employee – filter by Accounts User.");
                                return {
                                    query: "prompt_hr.py.expense_claim.get_employees_by_role",
                                    filters: { role: "Accounts User" }
                                };
                            }
                        }
                    ];
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
                }

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
            });
        });
    },
	employee: (frm) => { 
		fetch_commute_data(frm); 
		set_local_commute_monthly_expense(frm); 
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
    
            // COLLECT EXCEPTION MESSAGE WITH ROW NUMBER
            exceptionMessages.push(
                `Row ${rowDoc?.idx}: ${rowDoc?.expense_type} allowance limit has been crossed.`
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
// ? CREATE PAYMENT ENTRY BUTTON
function create_payment_entry_button(frm) {
	if (frm.doc.docstatus !== 0 || frm.doc.workflow_state !== "Sent to Accounting Team") return;

	frm.page.actions.parent().remove();

	frm.add_custom_button(__('Create Payment Entry'), () => {
		if (frm.doc.approval_status !== "Approved") {
			frappe.throw(__('Expense Claim must be approved before creating a payment entry.'));
		}

		const proceed = () => {
			frm.set_value("workflow_state", "Expense Claim Submitted");
			frm.savesubmit().then(() => frm.events.make_payment_entry(frm));
		};

		if (!frm.doc.payable_account) {
			const d = new frappe.ui.Dialog({
				title: __('Create Payment Entry'),
				fields: [{
					fieldtype: 'Link',
					fieldname: 'payable_account',
					label: __('Payable Account'),
					options: 'Account',
					reqd: 1,
					get_query: () => frm.fields_dict["payable_account"].get_query()
				}],
				primary_action_label: __('Create'),
				primary_action(values) {
					frm.set_value("payable_account", values.payable_account);
					d.hide();
					proceed();
				}
			});
			d.show();
		} else {
			proceed();
		}
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
                    reqd: 1
                },
                {
                    label: 'To Date',
                    fieldname: 'to_date',
                    fieldtype: 'Date',
                    reqd: 1
                }
            ],
            primary_action_label: 'Fetch Expense Claims',
            primary_action(values) {
                // ? VALIDATE DATE RANGE
                if (values.from_date > values.to_date) {
                    frappe.throw(__('From Date cannot be after To Date.'));
                    return;
                }

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

// ? FUNCTION TO ADD BUTTON EXTRA FIELD VISIT CLAIM
function claim_extra_field_visit_expenses(frm) {
    const allowed_roles = ['Service Engineer', 'S - HR Director (Global Admin)', "S - Service Engineer", "System Manager", "S - HR L5", "S - HR L4", "S - HR L3", "S - HR L2", "S - HR L1", "S - HR L2 Manager", "S - HR Supervisor (RM)"];
    const user_roles = frappe.user_roles;

    const has_access = user_roles.some(role => allowed_roles.includes(role));
    if (!has_access) return;

    // ? ADD CLAIM EXTRA FIELD VISIT EXPENSE BUTTON
    frm.add_custom_button("Claim Extra Field Visit Expense", () => {
        // ! THROW MESSAGE IF EMPLOYEE IS NOT SELECTED
        if (!frm.doc.employee) {
            frappe.msgprint({
                title: __('Missing Employee'),
                message: __('Please select an Employee before proceeding.'),
                indicator: 'red'
            });
            return;
        }
        // ----------------------------------
        // CACHE FOR FIELD VISIT
        // ----------------------------------
        let field_visit_cache = [];

        frappe.db.get_list("Field Visit", {
            fields: ["name"],
            filters: {
                service_mode: "On Site(Customer Premise)",
                field_visited_by: frm.doc.employee
            },
            limit_page_length: 0
        }).then(records => {
            field_visit_cache = records.map(r => r.name);
        });

        // ----------------------------------
        // CACHE FOR SERVICE CALL BASED ON FIELD VISIT
        // ----------------------------------
        let service_call_cache = {};
        function load_service_calls_for_visits(field_visits) {
            let cache_key = field_visits.sort().join(",");
            if (service_call_cache[cache_key]) {
                return Promise.resolve(service_call_cache[cache_key]);
            }
            return frappe.call({
                method: "prompt_hr.py.expense_claim.get_service_calls_from_field_visits",
                args: {
                    field_visits: field_visits,
                    txt: ""
                }
            }).then(r => {
                let list = (r.message || []).map(d => ({ value: d.name, label: __(d.name), description: "" }));
                service_call_cache[cache_key] = list;
                return list;
            });
        }
        const dialog = new frappe.ui.Dialog({
            title: "Claim Extra Field Visit Expense",
            fields: [
                {
                    label: "Field Visit",
                    fieldname: "field_visit",
                    fieldtype: "MultiSelectList",
                    options: "Field Visit",
                    reqd: 1,
                    get_data: function (txt) {
                        return field_visit_cache
                            .filter(d => !txt || d.toLowerCase().includes(txt.toLowerCase()))
                            .map(d => ({ value: d, description: "" }));
                    }
                },
                {
                    label: "Service Call",
                    fieldname: "service_call",
                    fieldtype: "MultiSelectList",
                    options: "Service Call",
                    reqd: 1,
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
                {
                    label: "Number of Row",
                    fieldname: "number_of_row",
                    fieldtype: "Int",
                    reqd: 1,
                    default: 1,
                    min: 1,
                    max: 4
                },
                {
                    label: "Add Without Field Visit and Service Call",
                    fieldname: "add_without_fv_sc",
                    fieldtype: "Check",
                    onchange: function () {
                        const isRequired = !dialog.get_value("add_without_fv_sc");
                        dialog.set_df_property("field_visit", "reqd", isRequired);
                        dialog.set_df_property("service_call", "reqd", isRequired);
                        dialog.set_df_property("field_visit", "hidden", !isRequired);
                        dialog.set_df_property("service_call", "hidden", !isRequired);
                        
                        dialog.fields_dict.field_visit.refresh();
                        dialog.fields_dict.service_call.refresh();
                    }
                },

            ],
            primary_action_label: "Add Expense",
            primary_action(values) {
                if (values.number_of_row > 4) {
                    frappe.msgprint(__("Number of Row cannot be greater than 4"));
                    return;
                }

                if (values.add_without_fv_sc){
                    for (let i = 0; i < values.number_of_row; i++) {
                        frm.add_child("expenses", {});
                    }
                    frm.refresh_field("expenses");
                    dialog.hide();
                }
                else {

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
            }
        });

        dialog.show();
    })
}
