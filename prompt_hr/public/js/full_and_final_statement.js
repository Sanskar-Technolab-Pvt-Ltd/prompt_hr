frappe.ui.form.on("Full and Final Statement", {
  refresh: function (frm) {
    frm.events.fetch_salary_structure(frm);
    frm.events.update_reference_document_requirement(frm);
    if (!frm.is_new()) {
      const joining_date = frm.doc.date_of_joining;
      const relieving_date = frm.doc.relieving_date;
      const date_diff = moment(relieving_date).diff(joining_date, "years");
      console.log(date_diff)
      if (date_diff >= 5) {
        frappe.call({
          method:
            "prompt_hr.py.full_and_final_statement.get_gratuity_button_label",
          args: {
            employee: frm.doc.employee,
          },
          callback(r) {
            if (r.message) {
              frm.add_custom_button(r.message, () => {
                frappe.call({
                  method:
                    "prompt_hr.py.full_and_final_statement.open_or_create_gratuity",
                  args: {
                    employee: frm.doc.employee,
                  },
                  callback: function (r) {
                    if (r.message) {
                      frappe.set_route("Form", "Employee Gratuity", r.message);
                    } else {
                      frappe.route_options = {
                        "employee": frm.doc.employee
                      }
                      frappe.new_doc("Employee Gratuity")
                      
                    }
                  },
                });
              });
            }
          },
        });
      }
    }
    if (frm.doc.status == "On Hold") {
      release_fnf_button(frm)
    }
  },
  validate: function (frm) {
    frm.events.update_reference_document_requirement(frm);
  },

  employee: function (frm) {
    // Clear tables on employee change
    frm.clear_table("payables");
    frm.clear_table("receivables");
    frm.refresh_fields(["payables", "receivables"]);

    if (frm.doc.employee && frm.doc.company) {
      frm.events.get_outstanding_statements(frm);
      frm.events.fetch_salary_structure(frm);
    } else {
      frm.set_value("custom_monthly_salary", 0);
      frm.set_value("custom_unserved_notice_days", 0);
    }
  },

  // Set Monthly Salary Amount
  fetch_salary_structure: function (frm) {
    if (!frm.doc.employee || !frm.doc.company) return;

    frappe.db
      .get_list("Salary Structure Assignment", {
        fields: ["name", "base"],
        filters: {
          docstatus: 1,
          employee: frm.doc.employee,
          company: frm.doc.company,
        },
        limit: 1,
        order_by: "from_date desc",
      })
      .then((records) => {
        frm.set_value(
          "custom_monthly_salary",
          records && records.length > 0 ? records[0].base : 0
        );
      });
  },

  // Make Reference Document Non-Mandatory
  // This is to avoid mandatory errors when creating new entries in the Receivables and Payables tables
  update_reference_document_requirement: function (frm) {
    ["receivables", "payables"].forEach(function (table_field) {
      if (!frm.fields_dict[table_field] || !frm.fields_dict[table_field].grid)
        return;

      frm.fields_dict[table_field].grid.docfields.forEach(function (docfield) {
        if (docfield.fieldname === "reference_document") {
          docfield.reqd = 0;
          docfield.mandatory_depends_on = "";
        }
      });

      frm.fields_dict[table_field].grid.update_docfield_property(
        "reference_document",
        "reqd",
        0
      );
      frm.fields_dict[table_field].grid.update_docfield_property(
        "reference_document",
        "mandatory_depends_on",
        ""
      );
      frm.fields_dict[table_field].grid.refresh();
    });
  },
});


function release_fnf_button(frm) {

  frm.add_custom_button(__("Release FNF"), function () {
    frappe.call({
      method: "prompt_hr.py.full_and_final_statement.send_release_fnf_mail",
      args: {
        fnf_id: frm.doc.name
      },
      callback: function (res) {
        frm.set_value("status", "Unpaid")
        frm.save()
      }
    })
  })
}