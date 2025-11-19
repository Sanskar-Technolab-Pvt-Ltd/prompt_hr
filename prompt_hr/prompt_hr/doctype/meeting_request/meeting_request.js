frappe.ui.form.on("Meeting Request", {
    onload(frm) {
        updateRelatedToOptions(frm);

        if(!frm.doc.organizor_name){
            frappe.call({
                method:"prompt_marketing.prompt_marketing.doctype.tour_visit.tour_visit.get_employee_for_user",
                callback:function(r){
                    if(r.message){
                        frm.set_value("organizor_name", r.message.name);
                        frm.set_value("organizer_name", r.message.employee_name);
                    }
                }
            });
        }
    },

    // ? FUNCTIONALITY TO OPEN NEXT MEETING POP UP
    next_action_required(frm){
        nextMeetingPopUp(frm);
    }
});

// ? FUNCTION TO UPDATE RELATED TO OPTIONS
function updateRelatedToOptions(frm) {
    frm.set_query("related_to", function () {
        return {
            filters: [["name", "in", ["Customer", "Lead", "Opportunity"]]]
        };
    });
    frm.refresh_field("related_to");
}

// ? CHILD TABLE FILTER
cur_frm.fields_dict["table_qygi"].grid.get_field("related_to").get_query = function() {
    return {
        filters: {
            name: ["in", ["User", "Contact", "Customer"]]
        }
    };
};

// ======================================================
// =============== NEXT MEETING CREATION =================
// ======================================================

// ? FUNCTION TO CREATE POP UP FOR NEXT MEETING
function nextMeetingPopUp(frm) {

    // ? IF NEXT MEETING REQUIRED IS CHECKED BY USER
    if (frm.doc.next_action_required) {

        // ? OPEN DIALOG FOR NEXT MEETING DETAILS
        let d = new frappe.ui.Dialog({
            title: "Enter Next Meeting Details",
            fields: [
                {
                    label: "Next Meeting Type",
                    fieldname: "next_action_type",
                    fieldtype: "Select",
                    options: ["Offline", "Online", "On Site", "Call"],
                    reqd: 1
                },
                {
                    label: "Meeting Title",
                    fieldname: "meeting_title",
                    fieldtype: "Data",
                    reqd: 1,
                    default: frm.doc.meeting_title
                },
                // {
                //     label: "Next Meeting Date",
                //     fieldname: "next_action_date",
                //     fieldtype: "Date",
                //     reqd: 1
                // },
                {
                    label: "From Time",
                    fieldname: "from_time",
                    fieldtype: "Datetime",
                },
                {
                    label: "To Time",
                    fieldname: "to_time",
                    fieldtype: "Datetime",
                },
                {
                    label: "Meeting Agenda / Notes",
                    fieldname: "next_action_agenda",
                    fieldtype: "Small Text"
                },
                // {
                //     label: "Assigned To",
                //     fieldname: "assigned_to",
                //     fieldtype: "Link",
                //     options: "User",
                //     reqd: 1,
                //     default: frappe.session.user
                // }
            ],
            primary_action_label: "Submit",

            // ? ON SUBMIT
            primary_action(values) {

                // ? SET VALUES TO CURRENT MEETING REQUEST
                frm.set_value("next_action_type", values.next_action_type);
                frm.set_value("next_action_date", values.from_time);
                frm.set_value("next_action_agenda", values.next_action_agenda);
                frm.set_value("assigned_to", values.assigned_to);
                frm.save();

                d.hide();

                // ? PREPARE NEXT MEETING DOCUMENT

                let meeting_doc = {
                    doctype: "Meeting Request",
                    meeting_title: values.meeting_title,
                    organizor_name: frm.doc.organizor_name,
                    organizer_name: frm.doc.organizer_name,
                    // date: values.next_action_date,
                    from_time: values.from_time,
                    to_time: values.to_time,
                    mode: values.next_action_type,
                    city: frm.doc.city,
                    product_category: frm.doc.product_category,
                    related_to: frm.doc.related_to,
                    related_to_form: frm.doc.related_to_form,
                    next_action_of: frm.doc.name,
                };

                // ? INSERT THE NEW MEETING REQUEST DOC
                insertMeetingDoc(meeting_doc, values);
            }
        });

        d.show();
    }
}

// ? FUNCTION TO INSERT THE NEW MEETING DOC
function insertMeetingDoc(meeting_doc, values) {

    frappe.call({
        method: "frappe.client.insert",
        args: { doc: meeting_doc },
        callback: function (r) {
            if (!r.exc) {

                // ? SUCCESS MESSAGE
                frappe.show_alert({
                    message: __("Next Meeting created successfully"),
                    indicator: "green"
                });

                // ? ASSIGN CREATED MEETING TO USER
                assignMeetingUser(r, values);
            }
        }
    });
}

// ? FUNCTION TO ASSIGN THE CREATED MEETING DOC TO USER
function assignMeetingUser(r, values) {

    frappe.call({
        method: "frappe.desk.form.assign_to.add",
        args: {
            doctype: r.message.doctype,
            name: r.message.name,
            assign_to: [values.assigned_to] || frappe.session.user
        },
        callback: function (res) {
            if (!res.exc) {
                frappe.show_alert({
                    message: __("The meeting has been assigned to {0}", [values.assigned_to]),
                    indicator: "green"
                });
            }
        }
    });
}
