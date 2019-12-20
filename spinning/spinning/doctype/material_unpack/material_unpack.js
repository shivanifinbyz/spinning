// Copyright (c) 2019, FinByz Tech Pvt Ltd and contributors
// For license information, please see license.txt

/* 
cur_frm.fields_dict.grade.get_query = function(doc) {
	
	return {
		filters: {
			"grade": ['in', items]
		}
	}
}; */
cur_frm.fields_dict.grade.get_query = function(doc) {
	return{
		query: "spinning.controllers.queries.grade_query",
		filters: {
			'item_code': doc.item_code
		}
	}
}
cur_frm.fields_dict.item_code.get_query = function (doc) {
    return {
        filters: {
            "has_batch_no": 1
        }
    }
};
cur_frm.fields_dict.merge.get_query = function (doc) {
    return {
        filters: {
            "item_code": doc.item_code
        }
    }
};
cur_frm.fields_dict.s_warehouse.get_query = function (doc) {
    return {
        filters: {
            "company": doc.company
        }
    }
};
cur_frm.fields_dict.t_warehouse.get_query = function (doc) {
    return {
        filters: {
            "company": doc.company
        }
    }
};
frappe.ui.form.on('Material Unpack', {	
	before_save: function(frm){
		frm.trigger('calculate_weights')
	},
	refresh: function(frm){		
		$('*[data-fieldname="packages"]').find('.grid-add-row').hide();
		if(frm.doc.__islocal){
			frm.trigger('set_t_warehouse');
		}
		
        if (!frm.doc.__is_local && frm.doc.docstatus == 1 && frm.doc.status != 'Repacked') {
            frm.add_custom_button(__("Material Repack"), function () {
                frappe.model.open_mapped_doc({
                    method: "spinning.spinning.doctype.material_unpack.material_unpack.make_repack",
                    frm: cur_frm
                })
            }, __("Create"))
        }
    
	},
	company: function(frm){
		frm.trigger('set_t_warehouse');
	},
	add_packages: function(frm){
		if(!frm.doc.merge){
			frappe.throw("Please select Merge")
		}
		if(!frm.doc.grade){
			frappe.throw("Please select Grade")
		}
		frappe.db.get_value("Company", frm.doc.company, 'default_source_warehouse', function(r){
			let warehouse = frm.doc.s_warehouse ? frm.doc.s_warehouse : r.default_source_warehouse;
			select_packages({frm: frm, warehouse: warehouse,item_code: frm.doc.item_code});
		})
	},
	item_code: function(frm){
		/* if(!frm.doc.merge){
			frappe.throw("Please select Merge")
		} */
		frappe.db.get_value("Company", frm.doc.company, 'default_source_warehouse', function(r){
			let warehouse = frm.doc.s_warehouse ? frm.doc.s_warehouse : r.default_source_warehouse;
			select_packages({frm: frm, warehouse: warehouse,item_code: frm.doc.item_code});
		})
	},
	set_t_warehouse: function(frm){
		frappe.db.get_value("Company", frm.doc.company, 'abbr', function(r){
				frm.set_value('t_warehouse', 'Unpack - '+ r.abbr)
		});
	},
	calculate_weights: function(frm){
		const total_gross_weight = frappe.utils.sum((frm.doc.packages || []).map(function(i){ return i.gross_weight }));
		const total_net_weight = frappe.utils.sum((frm.doc.packages || []).map(function(i){ return i.net_weight }));
		
		frm.set_value('total_gross_weight', total_gross_weight);
		frm.set_value('total_net_weight', total_net_weight);
	},
	grade: function (frm) {
		if(frm.doc.merge){
			frappe.call({
				method: "spinning.controllers.batch_controller.get_batch_no",
				args: {
					'args': {
						'item_code': frm.doc.item_code,
						'merge': frm.doc.merge,
						'grade':frm.doc.grade
					},
				},
				callback: function(r) {
					if(r.message){
						frm.set_value('batch_no',r.message)
					}
				 }
			});
		}
    },
	merge: function (frm) {
		if(frm.doc.grade){
			frappe.call({
				method: "spinning.controllers.batch_controller.get_batch_no",
				args: {
					'args': {
						'item_code': frm.doc.item_code,
						'merge': frm.doc.merge,
						'grade':frm.doc.grade
					},
				},
				callback: function(r) {
					if(r.message){
						frm.set_value('batch_no',r.message)
					}
				 }
			});
		}
    },
});
frappe.ui.form.on("Material Unpack Package", {
	packages_add: function(frm, cdt, cdn){
		frm.events.calculate_weights(frm);
	},

	package: function(frm, cdt, cdn){
		frm.events.calculate_weights(frm);
	},
	
	packages_remove: function(frm, cdt, cdn){
		frm.events.calculate_weights(frm);
	}
});
const select_packages = (args) => {
	frappe.require("assets/spinning/js/utils/package_selector.js", function() {
		new PackageSelector(args)
	})
}