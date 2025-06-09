// ? MAIN FORM EVENTS
frappe.ui.form.on('Expense Claim', {
	refresh(frm) {
		create_payment_entry_button(frm);
		fetch_commute_data(frm);
	},
	employee: fetch_commute_data,
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
		reset_commute_fields(row.doctype, row.name);
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
