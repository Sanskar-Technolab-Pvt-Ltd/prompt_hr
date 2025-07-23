frappe.ui.form.off("Leave Policy Assignment", "set_effective_date")
frappe.ui.form.on("Leave Policy Assignment", {
  // Set default filter on refresh based on company
  refresh: function (frm) {
    if (frm.doc.employee) {
      // Get gender of the selected employee
      frappe.db.get_value("Employee", frm.doc.employee, "gender", function (r) {
        if (r && r.gender) {
          // Set dynamic query for leave_policy based on gender and company
          frm.set_query("leave_policy", () => {
            return {
              query:
                "prompt_hr.overrides.leave_policy_assignment_override.filter_leave_policy_for_display",
              filters: {
                gender: r.gender,
                company: frm.doc.company,
              },
            };
          });
        }
      });
    }
  },

  // Triggered when employee is selected/changed
  employee: function (frm) {
    // Reset the leave_policy field
    frm.set_value("leave_policy", null);

    // Proceed only if company is selected
    if (frm.doc.employee) {
      // Get gender of the selected employee
      frappe.db.get_value("Employee", frm.doc.employee, "gender", function (r) {
        if (r && r.gender) {
          // Set dynamic query for leave_policy based on gender and company
          frm.set_query("leave_policy", () => {
            return {
              query:
                "prompt_hr.overrides.leave_policy_assignment_override.filter_leave_policy_for_display",
              filters: {
                gender: r.gender,
                company: frm.doc.company,
              },
            };
          });
        }
      });
    } else {
      // If no company is selected, allow all policies (or fallback to empty filter)
      frm.set_query("leave_policy", function () {
        return {
          filters: {},
        };
      });
    }
  },

  set_effective_date: function (frm) {
		if (frm.doc.assignment_based_on == "Leave Period" && frm.doc.leave_period) {
			frappe.model.with_doc("Leave Period", frm.doc.leave_period, function () {
				let from_date = frappe.model.get_value(
					"Leave Period",
					frm.doc.leave_period,
					"from_date",
				);
				let to_date = frappe.model.get_value(
					"Leave Period",
					frm.doc.leave_period,
					"to_date",
				);
				frm.set_value("effective_from", from_date);
				frm.set_value("effective_to", to_date);
			});
		} else if (frm.doc.assignment_based_on == "Joining Date" && frm.doc.employee) {
			frappe.model.with_doc("Employee", frm.doc.employee, function () {
				let from_date = frappe.model.get_value(
					"Employee",
					frm.doc.employee,
					"date_of_joining",
				);
				frm.set_value("effective_from", from_date);
				frappe.call({
          method: "frappe.client.get_list",
          args: {
            doctype: "Leave Period",
            filters: {
              from_date: ["<=", frm.doc.effective_from],
              to_date: [">=", frm.doc.effective_from],
              is_active: 1,
            },
            fields: ["to_date"],
            limit_page_length: 1
          },
          callback: function (r) {
            if (r.message && r.message.length > 0) {
              //? SET "EFFECTIVE_TO" TO "TO_DATE" OF MATCHING LEAVE PERIOD
              frm.set_value("effective_to", r.message[0].to_date);
            } else {
              //? IF NOT FOUND, SET "EFFECTIVE_TO" TO 31ST DECEMBER OF THAT YEAR
              const from_dt = frappe.datetime.str_to_obj(frm.doc.effective_from);
              const dec_31_dt = new Date(from_dt.getFullYear(), 11, 31);  // Month 11 = December
              const datetime_str = frappe.datetime.obj_to_str(dec_31_dt);
              frm.set_value("effective_to", datetime_str);
            }
          }
        });

			});
		}
		frm.refresh();
	},
});
