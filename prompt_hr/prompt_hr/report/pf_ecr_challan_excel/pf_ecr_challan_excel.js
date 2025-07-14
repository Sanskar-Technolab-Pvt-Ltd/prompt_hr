// Copyright (c) 2025, Jignasha Chavda and contributors
// For license information, please see license.txt

frappe.query_reports["PF ECR Challan Excel"] = {
    filters: [
		{
			fieldname: "month",
			label: __("Month"),
			fieldtype: "Select",
			options: "Jan\nFeb\nMar\nApr\nMay\nJun\nJul\nAug\nSep\nOct\nNov\nDec",
			default: ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
			[frappe.datetime.str_to_obj(frappe.datetime.get_today()).getMonth()]

		},
		{
			fieldname: "employee",
			label: __("Employee"),
			fieldtype: "Link",
			options: "Employee"
		}
	],

    onload: function(report) {
        report.page.add_inner_button('Download Text File', async function() {
            // 1. Fetch the report data
            const result = await frappe.call({
                method: "frappe.desk.query_report.run",
                args: {
                    report_name: "PF ECR Challan Excel",
                    filters: report.get_filter_values()
                }
            });
            // 2. Process the data
            const data = result.message.result;
            const columns = result.message.columns.map(col => col.label);

            // 3. Format as text with #~# separator
            let lines = [];
            lines.push(columns.join("#~#")) ;
            data.forEach(row => {
				const rowText = Object.values(row).map(val => {
					// If value is null, undefined, or empty string
					if (val === null || val === undefined || val === '') {
						// If the value is expected to be a number, put 0, else null
						// Try to detect number type
						return typeof val === 'number' || (!isNaN(val) && val !== '') ? 0 : 'Null';
					}
					// If value is a number, return as is
					if (typeof val === 'number') return val;
					// For other types, return as is
					return val;
				}).join("#~#");
				lines.push(rowText);
			});

            const textContent = lines.join("\n");

            // 4. Trigger download
            const blob = new Blob([textContent], {type: "text/plain"});
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = "pf_ecr_challan_report.txt";
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
        }, 'Actions');
    },
};
