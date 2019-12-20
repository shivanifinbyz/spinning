cur_frm.fields_dict['items'].grid.get_field("merge").get_query = function(doc, cdt, cdn) {
	let d = locals[cdt][cdn];

	return {
		filters: {
			"item_code": d.item_code
		}
	}
};

/* cur_frm.fields_dict['items'].grid.get_field("grade").get_query = function(doc) {
	return {
		filters: {
			"supplier": doc.supplier
		}
	}
}; */

this.frm.fields_dict.taxes_and_charges.get_query = function(doc){
	return {
		"filters": {
			'company': doc.company
		}
	};
}

frappe.ui.form.on('Purchase Invoice', {
	onload: function(frm){
		frm.trigger('override_merge_new_doc');
		frm.trigger('override_grade_new_doc');
	},
	override_merge_new_doc: function(frm){
		let merge_field = cur_frm.get_docfield("items", "merge")

		merge_field.get_route_options_for_new_doc = function(row){
			return {
				'item_code': row.doc.item_code
			}
		}
	},
	override_grade_new_doc: function(frm){
		let grade_field = cur_frm.get_docfield("items", "grade")

		grade_field.get_route_options_for_new_doc = function(row){
			return {
				'supplier': frm.doc.supplier
			}
		}
	},
});
