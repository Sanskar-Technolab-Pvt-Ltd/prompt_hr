// Copyright (c) 2025, Jignasha Chavda and contributors
// For license information, please see license.txt

frappe.query_reports["Travel Expense Report"] = {
	filters: [
        {
            fieldname: "from_date",
            label: __("From Date"),
            fieldtype: "Date",
            reqd: 1,
            default: frappe.datetime.month_start()
        },
        {
            fieldname: "to_date",
            label: __("To Date"),
            fieldtype: "Date",
            reqd: 1,
            default: frappe.datetime.month_end()
        },
        {
            fieldname: "company",
            label: __("Company"),
            fieldtype: "Link",
            options: "Company",
            reqd: 0
        },
		{
			fieldname: "employee",
			label: __("Employee"),
			fieldtype: "Link",
			options: "Employee",
			reqd: 0
		},
		{
			fieldname: "city",
			label: __("City"),
			fieldtype: "MultiSelectList",
			options: "Village or City",
			reqd: 0,
			get_data: function(txt) {
				return frappe.db.get_link_options("Village or City", txt);
			}
		},
		{
			fieldname: "status",
			label: __("Status"),
			fieldtype: "Select",
			options: [
				{ value: "0", label: __("Draft") },
				{ value: "1", label: __("Submitted") },
				{ value: "2", label: __("Cancelled") }
			],
			reqd: 0
		},
		{
			fieldname: "expense_claim_type",
			label: __("Expense Type"),
			fieldtype: "Link",
			options: "Expense Claim Type",
			reqd: 0
		}, 
	{
		fieldname: "department",
		label: __("Department"),
		fieldtype: "MultiSelectList",
		options: "Department",
		reqd: 0,
		get_data: function (txt) {
			let employee = frappe.query_report.get_filter_value("employee");
		
			if (employee) {
				return frappe.db.get_value("Employee", employee, "department").then(r => {
					if (r && r.message && r.message.department) {
						const dept = r.message.department;
		
						if (!txt || dept.toLowerCase().includes(txt.toLowerCase())) {
							return frappe.db.get_link_options("Department", txt, {name: dept});
						}
					}
					return [];
				});
			}
		
			// ? If no employee selected, fall back to normal list
			return frappe.db.get_link_options("Department", txt);
		}
		
	},
	{
		fieldname: "designation",
		label: __("Designation"),
		fieldtype: "Link",
		options: "Designation",
		reqd: 0,
		get_query: function () {
			return {
				query: "prompt_hr.prompt_hr.report.travel_expense_report.travel_expense_report.get_employee_designations",
				filters: {employee: frappe.query_report.get_filter_value("employee")}
			};
		}
	},
	{
		fieldname: "grade",
		label: __("Grade"),
		fieldtype: "Link",
		options: "Employee Grade",
		reqd: 0,
		get_query: function () {
			return {
				query: "prompt_hr.prompt_hr.report.travel_expense_report.travel_expense_report.get_employee_grades",
				filters: {employee: frappe.query_report.get_filter_value("employee")}
			};
		}
	},	
	{
		fieldname: "tour_visit",
		label: __("Tour Visit"),
		fieldtype: "MultiSelectList",
		options: "Tour Visit",
		reqd: 0,
		get_data: function(txt) {
			return frappe.db.get_link_options("Tour Visit", txt);
		}
	},
	{
		fieldname: "field_visit",
		label: __("Field Visit"),
		fieldtype: "MultiSelectList",
		options: "Field Visit",
		reqd: 0,
		get_data: function(txt) {
			return frappe.db.get_link_options("Field Visit", txt);
		}
	},
	{
		fieldname: "service_call",
		label: __("Service Call"),
		fieldtype: "MultiSelectList",
		options: "Service Call",
		reqd: 0,
		get_data: function(txt) {
			return frappe.db.get_link_options("Service Call", txt);
		}
	},
	{
		fieldname: "customer",
		label: __("Customer"),
		fieldtype: "MultiSelectList",
		options: "Customer",
		reqd: 0,
		get_data: function(txt) {
			return frappe.db.get_link_options("Customer", txt);
		}
	}

    ],

	onload: function(report) {		

		// Override get_filters_html_for_print to only show non-null filters
        report.get_filters_html_for_print = function() {
            const applied_filters = this.get_filter_values();
            return Object.keys(applied_filters)
                .map((fieldname) => {
                    const docfield = frappe.query_report.get_filter(fieldname).df;
                    const value = applied_filters[fieldname];

                    if (docfield.hidden_due_to_dependency) {
                        return null;
                    }

                    // Skip filters with null, undefined, or empty values
                    if (value === null || value === undefined || value === "" || 
                        (Array.isArray(value) && value.length === 0)) {
                        return null;
                    }

                    return `<div class="filter-row">
                        <b>${__(docfield.label, null, docfield.parent)}:</b> ${frappe.format(value, docfield)}
                    </div>`;
                })
                .filter(html => html !== null)
                .join("");
        }; 
	}
};
