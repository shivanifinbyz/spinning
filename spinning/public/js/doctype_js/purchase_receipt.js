/* this.frm.dashboard.add_transactions({
	'label': "Stock Entry",
	'items': ['Stock Entry']
}); */
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
cur_frm.fields_dict.taxes_and_charges.get_query = function(doc){
	return {
		"filters": {
			'company': doc.company
		}
	};
}

/* cur_frm.fields_dict['items'].grid.get_field("grade").get_query = function(doc) {
	return {
		filters: {
			"supplier": doc.supplier
		}
	}
}; */
cur_frm.fields_dict.package_item.get_query = function (doc) {
    return {
        filters: {
            "item_group": doc.package_type
        }
    }
};

frappe.ui.form.on('Purchase Receipt', {
	onload: function(frm){
		frm.trigger('override_merge_new_doc');
		frm.trigger('override_grade_new_doc');
		frm.trigger('set_options_for_row_ref');
		frm.trigger('duplicate_row_button_add');
	},
	validate: function(frm){
		
		$.each(frm.doc.items || [], function(i, d) {
			if(d.merge){	
				/* frappe.call({
					method:"spinning.controllers.merge_validation.validate_merge_with_doc",
					args:{
						doc: d,
						merge: d.merge,
						item_code:d.item_code
					},
					callback: function(r){
						console.log(r)
						frappe.validated = false;
					}
				})  */
				 frappe.db.get_value("Merge",d.merge,'item_code',function(r){
					if(r){
						if(r.item_code!=d.item_code){
							frappe.msgprint(__("Please select correct merge for the item"))
							frappe.validated = false;
						}
					}
				}) 
			}
		});
	}, 
	/* validate: function(frm){
		frm.trigger('set_total_qty');
	},

	set_total_qty: function(frm){
		frm.doc.items.forEach(function(row){
			frappe.db.get_value("Item", row.item_code, 'has_batch_no', function(r){
				if(r.has_batch_no){
					let qty = frappe.utils.sum(
						(frm.doc.packages || []).map(function(c){ return c.row_ref == row.idx ? c.net_weight : 0}));

					frappe.model.set_value(row.doctype, row.name, 'qty', qty);
					frappe.model.set_value(row.doctype, row.name, 'received_qty', qty);
				}
			})
		});
	}, */
	
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

	set_options_for_row_ref: function(frm){
		let options = [];
		let row_ref_doc_field = frm.get_docfield("packages", "row_ref");
		const items_length = frm.doc.items.length;

		for(let i = 1; i <= items_length; i++){
			options.push(i.toString())
		}
		row_ref_doc_field.options = options.join("\n");
	},
	
	cal_total_package_gross_wt: function(frm){
		const total_gross_wt = frappe.utils.sum((frm.doc.packages || []).map(function(i){ return i.gross_weight }));
		frm.set_value("total_package_gross_weight", flt(total_gross_wt));
	},

	cal_total_package_net_wt: function(frm){
		const total_net_wt = frappe.utils.sum((frm.doc.packages || []).map(function(i){ return i.net_weight }));
		frm.set_value("total_package_net_weight", flt(total_net_wt));
	},
	package_item: function(frm) {
		$.each(frm.doc.packages || [], function(i, d) {
			d.package_item = frm.doc.package_item;
		});
		refresh_field("packages");
	},
	package_type: function(frm) {
		$.each(frm.doc.packages || [], function(i, d) {
			d.package_type = frm.doc.package_type;
		});
		refresh_field("packages");
	},
	is_returnable: function(frm) {
		$.each(frm.doc.packages || [], function(i, d) {
			d.is_returnable = frm.doc.is_returnable;
		});
		refresh_field("packages");
	},
	returnable_by: function(frm) {
		$.each(frm.doc.packages || [], function(i, d) {
			d.returnable_by = frm.doc.returnable_by;
		});
		refresh_field("packages");
	},
	duplicate_row_button_add: function(frm){
		var parent_div = cur_frm.fields_dict.items.$wrapper.find(".grid-buttons")
		$(parent_div).append('<button type="reset" class="btn btn-xs btn-default grid-duplicate-rows hidden">Duplicate</button>')
	}
});

frappe.ui.form.on('Purchase Receipt Item', {
	items_add: function(frm, cdt, cdn){
		frm.events.set_options_for_row_ref(frm);
	},

	items_remove: function(frm, cdt, cdn){
		frm.events.set_options_for_row_ref(frm);
	}
});

frappe.ui.form.on("Purchase Receipt Package Detail", {
	gross_weight: function(frm, cdt, cdn){
		frm.events.cal_total_package_gross_wt(frm)
	},

	net_weight: function(frm, cdt, cdn){
		frm.events.cal_total_package_net_wt(frm)
	},

	packages_remove: function(frm, cdt, cdn){
		frm.events.cal_total_package_net_wt(frm)
	},
	packages_add: function(frm, cdt, cdn){
		var row = locals[cdt][cdn];
		row.package_item = frm.doc.package_item;
		row.package_type = frm.doc.package_type;
		row.is_returnable = frm.doc.is_returnable;
		row.returnable_by = frm.doc.returnable_by;
		frm.refresh_field("packages");
	},

});

let $item_wrapper = cur_frm.fields_dict.items.$wrapper
$item_wrapper.on('click', '.grid-row-check:checkbox', (e) => {
	let duplicate_rows_button = cur_frm.$wrapper.find('.grid-duplicate-rows')
		duplicate_rows_button.toggleClass('hidden',cur_frm.fields_dict.items.$wrapper.find('.grid-body .grid-row-check:checked:first').length ? false : true);
})

$item_wrapper.on('click','.grid-duplicate-rows', function() {
	cur_frm.get_field('items').grid.get_selected_children().forEach((doc) => {
		cur_frm.get_field('items').grid.add_new_row(doc.idx+1, null, null, doc);
	});
	cur_frm.refresh_field("items");
});
