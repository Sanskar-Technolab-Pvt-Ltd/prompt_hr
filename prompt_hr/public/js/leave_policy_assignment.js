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
});
