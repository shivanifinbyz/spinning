cur_frm.fields_dict['items'].grid.get_field("merge").get_query = function(doc, cdt, cdn) {
	let d = locals[cdt][cdn];

	return {
		filters: {
			"item_code": d.item_code
		}
	}
};
cur_frm.fields_dict['items'].grid.get_field("grade").get_query = function(doc, cdt, cdn) {
	let d = locals[cdt][cdn];

	return {
		query: 'spinning.controllers.queries.grade_query',
		filters: {
			"item_code": d.item_code
		}
	}
};
frappe.ui.form.on("Stock Reconciliation Item", {
	grade: function (frm, cdt, cdn) {
		let d = locals[cdt][cdn];
		if(d.merge){
			frappe.call({
				method: "spinning.controllers.batch_controller.get_batch_no",
				args: {
					'args': {
						'item_code': d.item_code,
						'merge': d.merge,
						'grade':d.grade
					},
				},
				callback: function(r) {
					if(r.message){
						frappe.model.set_value(d.doctype,d.name,'batch_no',r.message)
					}
				 }
			});
		}
    },
	merge: function (frm, cdt, cdn) {
		let d = locals[cdt][cdn];
		if(d.grade){
			frappe.call({
				method: "spinning.controllers.batch_controller.get_batch_no",
				args: {
					'args': {
						'item_code': d.item_code,
						'merge': d.merge,
						'grade':d.grade
					},
				},
				callback: function(r) {
					if(r.message){
						frappe.model.set_value(d.doctype,d.name,'batch_no',r.message)
					}
				 }
			});
		}
    },
});
