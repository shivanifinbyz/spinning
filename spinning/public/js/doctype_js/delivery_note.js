this.frm.add_fetch('batch_no', 'merge', 'merge');
this.frm.add_fetch('batch_no', 'grade', 'grade');

this.frm.cscript.onload = function(frm) {
	this.frm.set_query("batch_no", "items", function(doc, cdt, cdn) {
		let d = locals[cdt][cdn];

		if(!d.item_code){
			frappe.throw(__("Please enter Item Code to get batch no."));
		}
		else{
			return {
				query: "spinning.controllers.queries.batch_query",
				filters: {
					'item_code': d.item_code,
					'warehouse': d.warehouse
				}
			}
		}
	});
}

cur_frm.set_query("shipping_address_name", function () {
	return {
		query: "frappe.contacts.doctype.address.address.address_query",
		filters: { link_doctype: "Customer", link_name: cur_frm.doc.customer }
	};
});

cur_frm.fields_dict.packages.grid.get_field('package').get_query = function(doc) {
	let items = [...new Set((frm.doc.items || []).map(function(i){return i.item_code}))]
	return {
		filters: {
			"status": ["!=", "Out of Stock"],
			"item_code": ['in', items]
		}
	}
}

cur_frm.fields_dict.taxes_and_charges.get_query = function(doc){
	return {
		"filters": {
			'company': doc.company
		}
	};
}

frappe.ui.form.on("Delivery Note", {
	onload: function (frm) {
		if(!frm.doc.tc_name){
			frm.set_value("tc_name", "Delivery Challan Terms");
		}
	},
	
	validate: function(frm){
		frm.events.set_items_as_per_packages(frm);
	},

	before_save: function (frm) {
		frm.trigger("cal_total_for_packages");
	},

	cal_total_for_packages: function (frm) {
		let total_gross_weight = frappe.utils.sum((frm.doc.packages || []).map(row => row.gross_weight));
		let total_tare_weight = frappe.utils.sum((frm.doc.packages || []).map(row => row.tare_weight));
		let total_net_weight = frappe.utils.sum((frm.doc.packages || []).map(row => row.net_weight));
		let total_spools = frappe.utils.sum((frm.doc.packages || []).map(row => row.spools));

		frm.set_value('total_gross_weight', flt(total_gross_weight, 3));
		frm.set_value('total_tare_weight', flt(total_tare_weight, 3));
		frm.set_value('total_net_weight', flt(total_net_weight, 3));
		frm.set_value('total_spools', flt(total_spools, 3));
		frm.set_value('total_packages', frm.doc.packages.length || 0);
	},

	add_packages: function(frm){
		frappe.db.get_value("Company", frm.doc.company, 'default_source_warehouse', function(r){
			select_packages({frm: frm, merge: frm.doc.merge, warehouse: frm.doc.set_warehouse || r.default_source_warehouse});
		})
	},

	set_batches_and_remove_items(frm){
		frm.doc.items.forEach(function(row) {
			let packages = frm.doc.packages.filter(d => d.item_code == row.item_code)

			if(packages.length && !row.batch_no){
				row.merge = packages[0].merge;
				row.grade = packages[0].grade;
				row.batch_no = packages[0].batch_no;
				row.qty = 1;
			}
		});

		let to_remove = [];

		frm.doc.items.reverse().forEach(function(row){
			if(row.batch_no == undefined || row.batch_no == ''){
				to_remove.push(row.idx - 1);
			}
		})

		to_remove.forEach(function(i){
			frm.get_field('items').grid.grid_rows[i].remove();
		});

		frm.refresh_field('items');
	},

	set_items_as_per_packages: function(frm) {

		let to_remove = [];
		let item_merge_grade_row_dict = {};
		let item_row_dict = {};
		let package_items = {};

		frappe.run_serially([
			() => {
				frm.doc.items.forEach(function(row){
					frappe.call({
						method: 'frappe.client.get_value',
						args: {
							doctype: "Item",
							filters: {
								name: row.item_code,
							},
							fieldname: 'has_batch_no'
						},
						async: false,
						callback: function(r){
							if(r.message.has_batch_no){
								to_remove.push(row.idx - 1);
								if (row.merge && row.grade) {
									let item_merge_grade = row.item_code.toString() + row.merge.toString() + row.grade.toString()
									if(!(item_merge_grade in item_merge_grade_row_dict)){
										console.log("Adding Item to Merge Dict" + item_merge_grade);
										item_merge_grade_row_dict[item_merge_grade] = Object.assign({}, row);
									}
								}
								if(!(row.item_code in item_row_dict)){
									item_row_dict[row.item_code.toString()] = Object.assign({}, row);
								}
							
							}
						}
						
					})
				});
				console.log("item merge grade dict");
				console.log(item_merge_grade_row_dict);
			},
			() => {
				to_remove.reverse().forEach(function(i){
					frm.get_field('items').grid.grid_rows[i].remove();
				});
			},
			() => {
				frm.doc.packages.forEach(function(row){
					let key = [row.item_code, row.merge, row.grade, row.batch_no];
					let item_merge_grade = row.item_code.toString() + row.merge.toString() + row.grade.toString()
					if(!(key in package_items)){
						if (item_merge_grade_row_dict[item_merge_grade]){
							console.log("Merge Grade Item Received");
							console.log(item_merge_grade_row_dict[item_merge_grade])
							package_items[key] = Object.assign({}, item_merge_grade_row_dict[item_merge_grade]);
						}
						else{
							package_items[key] = Object.assign({}, item_row_dict[row.item_code]);
							console.log("Merge Grde Item Not Received");
							console.log(item_row_dict[row.item_code]);

						}
						package_items[key]['net_weight'] = 0;
						package_items[key]['gross_weight'] = 0;
						package_items[key]['packages'] = 0;
						package_items[key]['no_of_spools'] = 0;

					}

					package_items[key]['warehouse'] = row.warehouse;
					package_items[key]['net_weight'] += row.net_weight;
					package_items[key]['gross_weight'] += row.gross_weight;
					package_items[key]['no_of_spools'] += row.spools;
					package_items[key]['packages'] += 1;
					console.log("final Package_item Dict")
					console.log(package_items[key])
				});
			},
			() => {
				$.each(package_items || {}, function(key, args){
					let keys = key.split(",");
					let values = Object.assign({}, args);

					delete values['idx'];
					delete values['name'];

					values.amount = flt(args.rate) * flt(args.net_weight);
					values.merge = keys[1];
					values.grade = keys[2];
					values.batch_no = keys[3];
					values.qty = args.net_weight
					values.gross_wt = args.gross_weight
					values.spools = args.no_of_spools
					values.no_of_packages = args.packages

					frm.add_child('items', values);
				});
			}, 
			() => frm.refresh_field('items'),
		]);
	},
});


frappe.ui.form.on("Delivery Note Item", {
	item_code: function (frm, cdt, cdn) {
		let d = locals[cdt][cdn];
		setTimeout(function(){
			frappe.db.get_value("Batch", d.batch_no, ['merge', 'grade'], function(r){
				frappe.model.set_value(cdt, cdn, 'merge', r.merge);
				frappe.model.set_value(cdt, cdn, 'grade', r.grade);
				
				select_packages({frm: frm, item_code: d.item_code, merge: d.merge, warehouse: d.warehouse});
			});
		}, 1000);
	},
});


const select_packages = (args) => {
	frappe.require("assets/spinning/js/utils/package_selector.js", function() {
		new PackageSelector(args)
	})
}
