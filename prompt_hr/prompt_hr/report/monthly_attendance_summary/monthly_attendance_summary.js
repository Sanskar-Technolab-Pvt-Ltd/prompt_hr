// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.query_reports["Monthly Attendance Summary"] = {
	filters: [
		{
			fieldname: "month",
			label: __("Month"),
			fieldtype: "Select",
			reqd: 1,
			options: [
				{ value: 1, label: __("Jan") },
				{ value: 2, label: __("Feb") },
				{ value: 3, label: __("Mar") },
				{ value: 4, label: __("Apr") },
				{ value: 5, label: __("May") },
				{ value: 6, label: __("June") },
				{ value: 7, label: __("July") },
				{ value: 8, label: __("Aug") },
				{ value: 9, label: __("Sep") },
				{ value: 10, label: __("Oct") },
				{ value: 11, label: __("Nov") },
				{ value: 12, label: __("Dec") },
			],
			default: frappe.datetime.str_to_obj(frappe.datetime.get_today()).getMonth() + 1,
		},
		{
			fieldname: "year",
			label: __("Year"),
			fieldtype: "Select",
			reqd: 1,
		},
		{
			fieldname: "employee",
			label: __("Employee"),
			fieldtype: "Link",
			options: "Employee",
			get_query: () => {
				var company = frappe.query_report.get_filter_value("company");
				return {
					filters: {
						company: company,
					},
				};
			},
		},
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
			reqd: 1,
		},
		{
			fieldname: "group_by",
			label: __("Group By"),
			fieldtype: "Select",
			options: ["", "Branch", "Grade", "Department", "Designation"],
		},
		{
			fieldname: "include_company_descendants",
			label: __("Include Company Descendants"),
			fieldtype: "Check",
			default: 1,
		},
		{
			fieldname: "summarized_view",
			label: __("Summarized View"),
			fieldtype: "Check",
			default: 0,
		},
	],
	onload: function (report) {
		// "Pending Leaves" button
        report.page.add_inner_button(
            __("Pending Leaves"),
            function() {
                let month = report.get_filter_value('month');
                if (!month) {
                    frappe.msgprint(__('Please select a month.'));
                    return;
                }

                frappe.set_route('query-report', 'Pending Leave Approval', {
                    month: report.get_filter_value('month'),
                    workflow_state: "Pending",
					status: "Open"
                });
            },
            __("Pending Requests")
			
        );

        // "Pending Attendance Regularization" button
        report.page.add_inner_button(
            __("Pending Attendance Regularization"),
            function() {
                let month = report.get_filter_value('month');
				console.log(month)
                if (!month) {
                    frappe.msgprint(__('Please select a month.'));
                    return;
                }
                frappe.set_route('query-report', 'Pending Regularization Request', {
					month: report.get_filter_value('month'),
                    status: "Pending"
                });
            },
            __("Pending Requests")
		);
		

		const legend_text = `
			<div id="attendance-legend" style="margin-top: 8px; margin-left: 13px; display: flex; gap: 18px; align-items: center; flex-wrap: wrap;">
				
				<span style="display:flex; align-items:center; gap:6px;">
				<b> P = Present </b>
				<!-- <span style="width:10px; height:10px; background:#6AA84F; border-radius:50%; display:inline-block;"></span> -->
				</span>
				
				<span style="display:flex; align-items:center; gap:6px;">
					<!-- <span style="width:10px; height:10px; background:#FFA500; border-radius:50%; display:inline-block;"></span> -->
					<b> HD = Half Day </b>
				</span>

				<span style="display:flex; align-items:center; gap:6px;">
					<!-- <span style="width:10px; height:10px; background:#CCCC00; border-radius:50%; display:inline-block;"></span> -->
					<b> H = Holiday </b>
				</span>

				<span style="display:flex; align-items:center; gap:6px;">
					<!-- <span style="width:10px; height:10px; background:#9999FF; border-radius:50%; display:inline-block;"></span> -->
					<b> WO = WeekOff </b>
				</span>

				<span style="display:flex; align-items:center; gap:6px;">
					<!-- <span style="width:10px; height:10px; background:#E06666; border-radius:50%; display:inline-block;"></span> -->
					<b> A = Absent </b>
				</span>

				<span style="display:flex; align-items:center; gap:6px;">
					<!-- <span style="width:10px; height:10px; background:#6D9EEB; border-radius:50%; display:inline-block;"></span> -->
					<b> M = Mispunch </b>
				</span>

			</div>
		`;

		setTimeout(() => {
			// Avoid duplicate insertion on refresh
			if (!$("#attendance-legend").length) {
				$(legend_text).insertAfter($(".chart-wrapper"));
			}
		}, 500);


		return frappe.call({
			method: "hrms.hr.report.monthly_attendance_sheet.monthly_attendance_sheet.get_attendance_years",
			callback: function (r) {
				var year_filter = frappe.query_report.get_filter("year");
				year_filter.df.options = r.message;
				year_filter.df.default = r.message.split("\n")[0];
				year_filter.refresh();
				year_filter.set_input(year_filter.df.default);
			},
		});
	},
	formatter: function (value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		const summarized_view = frappe.query_report.get_filter_value("summarized_view");
		const group_by = frappe.query_report.get_filter_value("group_by");

		if (group_by && column.colIndex === 1) {
			value = "<strong>" + value + "</strong>";
		}

		if (!summarized_view) {
			if ((group_by && column.colIndex > 7) || (!group_by && column.colIndex > 6)) {
				// if (value == "P" || value == "WFH")
				// 	value = "<span style='color:green'>" + value + "</span>";
				// else if (value == "A") value = "<span style='color:red'>" + value + "</span>";
				// else if (value == "HD") value = "<span style='color:orange'>" + value + "</span>";
				// else if (value == "L") value = "<span style='color:#318AD8'>" + value + "</span>";
				if (value === "WFH" || value.startsWith("P"))
					value = "<span style='color:green'>" + value + "</span>";
				else if (value.startsWith("A"))
					value = "<span style='color:red'>" + value + "</span>";
				else if (value.startsWith("HD"))
					value = "<span style='color:orange'>" + value + "</span>";
				else if (value.startsWith("L") && !value.startsWith("LWP"))
					value = "<span style='color:#318AD8'>" + value + "</span>";
			}
		}

		return value;
	},
};