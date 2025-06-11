// Copyright (c) 2025, Jignasha Chavda and contributors
// For license information, please see license.txt

frappe.ui.form.on("Candidate Portal", {
	refresh(frm) {
		if (frm.doc.offer_letter) {
			// Change the input field's display text but keep the value
			const input = frm.fields_dict.offer_letter.$wrapper.find("input");
			if (input.length) {
				input
					.css("cursor", "pointer")
					.css("color", "black")
					.css("text-decoration", "underline")
					.val("Click Here")
					.on("click", function () {
						window.open(frm.doc.offer_letter, "_blank");
					});
			}
		}
	}
});


