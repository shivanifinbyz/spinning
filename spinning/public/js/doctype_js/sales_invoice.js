this.frm.add_fetch('batch_no', 'merge', 'merge');
this.frm.add_fetch('batch_no', 'grade', 'grade');

this.frm.cscript.onload = function (frm) {
    this.frm.set_query("batch_no", "items", function (doc, cdt, cdn) {
        let d = locals[cdt][cdn];

        if (!d.item_code) {
            frappe.throw(__("Please enter Item Code to get batch no."));
        }
        else {
            return {
                query: "spinning.api.get_batch_no",
                filters: {
                    'item_code': d.item_code,
                    'warehouse': d.warehouse
                }
            }
        }
    });
}
