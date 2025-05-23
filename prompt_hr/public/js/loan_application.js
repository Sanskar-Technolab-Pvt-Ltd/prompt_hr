frappe.ui.form.on("Loan Application", {
    company: function(frm) {
        if (frm.doc.company) {
            console.log(frm.doc.company);
            frappe.db.get_list("Loan Product", {
                filters: {
                    company: frm.doc.company
                },
                limit: 1
            }).then((loan_products) => {
                console.log(loan_products);
                if (loan_products.length > 0) {
                    frm.set_value("loan_product", loan_products[0].name);
                } 
            });
        }
    }
});
