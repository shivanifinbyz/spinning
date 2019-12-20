PackageSelector = Class.extend({
	init: function (opts) {
		$.extend(this, opts);
		this.setup();
	},

	setup: function(){
		this.set_variables();
		this.make_dialog();
	},

	set_variables: function() {
		this.merge = this.merge ? this.merge : this.frm.doc.merge;
		this.grade = '';
		this.package_data = [];
	},

	make_dialog: function(){
		let me = this;

		let fields = [
			{
				label: __("Source Warehouse"),
				fieldtype:'Link',
				fieldname: 'warehouse',
				options: 'Warehouse',
				default: me.warehouse,
				read_only: 0,
				reqd: 1,
				get_query: function(){
					return {
						filters: {
							"is_group": 0,
							"company" : me.frm.doc.company
						}
					}
				},
			},

			{fieldtype:'Column Break'},

			{
				label: __('Item Code'),
				fieldtype:'Link',
				fieldname: 'item_code',
				options: 'Item',
				default: me.item_code,
				read_only: me.item_code ? 1 : 0,
				reqd: 1,
				get_query: function(){
					let items = [...new Set((me.frm.doc.items || me.frm.doc.item_code).map(function(i){return i.item_code}))]
					
					return {
						filters: {
							"item_code": ['in', items]
						}
					}
				},
			},

			{fieldtype:'Column Break'},

			{
				label: __("Merge"),
				fieldtype:'Link',
				fieldname: 'merge',
				options: 'Merge',
				default: me.merge,
				read_only: me.merge ? 1 : 0,
				reqd: 1,
				get_query: function(){
					let item_code = me.dialog.get_value('item_code');

					return {
						filters: {
							"item_code": item_code
						}
					}
				},
				change: function(){
					let merge = this.get_value();
					let item_code = this.layout.get_value('item_code');

					let filters = {'warehouse': this.warehouse}

					if(me.merge == merge)
						return;

					me.merge = merge;

					if(item_code){
						filters['item_code'] = item_code
					}
					else {
						return;
					}
					filters['merge'] = merge;

					me.get_packages(filters)
				}
			},

			{
				label: __('Filters'),
				fieldtype: 'Section Break',
			},
			{
				label: __("Grade"),
				fieldtype:'Link',
				fieldname: 'grade',
				options: 'Grade',
				get_query: function(){
					let item_code = me.dialog.get_value('item_code');

					return {
						query: 'spinning.controllers.queries.grade_query',
						filters: {
							"item_code": item_code
						}
					}
				},
				change: function(){
					me.set_filtered_package_data();
				},
			},

			{
				label: __("Package"),
				fieldtype: 'Data',
				fieldname: 'package',
				onchange: function(){
					me.set_filtered_package_data();
				},
			},

			{fieldtype:'Column Break'},
			
			{
				label: __("Paper Tube"),
				fieldtype:'Link',
				fieldname: 'paper_tube',
				options: 'Item',
				get_query: function(){
					return {
						filters: {
							'item_group': "Paper Tube"
						}
					}
				},
				change: function(){
					me.set_filtered_package_data();
				},
			},

			{fieldtype:'Column Break'},

			{
				label: __("Spools"),
				fieldtype:'Int',
				fieldname: 'spools',
				change: function(){
					me.set_filtered_package_data();
				},
			},

			{
				label: __("Total Qty"),
				fieldtype: 'Float',
				fieldname: 'total_qty',
				default: '0.0',
				read_only: 1,
			},

		]

		fields = fields.concat(this.get_package_fields());

		this.dialog = new frappe.ui.Dialog({
			title: __("Add Packages"),
			fields: fields,
		});

		let filters = {
			'item_code': this.item_code,
			'warehouse': this.warehouse,
			'merge': this.merge,
		}

		this.get_packages(filters);

		this.dialog.set_primary_action(__("Add"), function(){
			me.values = me.dialog.get_values();
			me.set_packages_in_frm();
			me.dialog.hide();
		});

		let $package_wrapper = this.get_package_wrapper();

		$($package_wrapper).find('.grid-remove-rows').hide();
		$($package_wrapper).find('.grid-add-row').hide();

		this.dialog.show();

		this.bind_events();
	},

	get_package_fields: function(){
		let me = this;

		return [
			{ fieldtype: 'Section Break', label: __('Packages') },
			{
				label: __("Don't show already selected"),
				fieldtype:'Check',
				fieldname: 'remove_selected',
				default: 0,
				change: function(){
					me.set_filtered_package_data();
				},
			},
			{
				fieldname: 'packages',
				label:'',
				fieldtype: "Table",
				read_only: 1,
				fields:[
					{
						'label': 'Package',
						'fieldtype': 'Link',
						'fieldname': 'package',
						'options': 'Package',
						'read_only': 1,
						'in_list_view': 1,
					},
					{
						'label': 'Spools',
						'fieldtype': 'Int',
						'fieldname': 'spools',
						'read_only': 1,
						'in_list_view': 1,
					},
					{
						'label': 'Item Code',
						'fieldtype': 'Link',
						'fieldname': 'item_code',
						'options': 'Item',
						'read_only': 1,
					},
					{
						'label': 'Item Name',
						'fieldtype': 'Data',
						'fieldname': 'item_name',
						'read_only': 1,
					},
					{
						'label': 'Warehouse',
						'fieldtype': 'Link',
						'fieldname': 'warehouse',
						'options': 'Warehouse',
						'read_only': 1,
					},
					{
						'label': 'Batch No',
						'fieldtype': 'Link',
						'fieldname': 'batch_no',
						'options': 'Batch',
						'read_only': 1,
					},
					{
						'label': 'Merge',
						'fieldtype': 'Link',
						'fieldname': 'merge',
						'options': 'Merge',
						'read_only': 1,
					},
					{
						'label': 'Grade',
						'fieldtype': 'Link',
						'fieldname': 'grade',
						'options': 'Grade',
						'read_only': 1,
					},
					{
						'label': 'Gross Weight',
						'fieldtype': 'Float',
						'fieldname': 'gross_weight',
						'read_only': 1,
						'in_list_view': 1,
					},
					{
						'label': 'Net Weight',
						'fieldtype': 'Float',
						'fieldname': 'net_weight',
						'read_only': 1,
						'in_list_view': 1,
					},
					{
						'label': 'Tare Weight',
						'fieldtype': 'Float',
						'fieldname': 'tare_weight',
						'read_only': 1,
					},
				],
				in_place_edit: true,
				// data: this.data,
				get_data: function(){
					return ;
				}
			}
		]
	},

	get_package_wrapper: function(){
		return this.dialog.get_field('packages').$wrapper;
	},

	get_selected_packages: function() {
		let me = this;
		let selected_packages = [];
		let $package_wrapper = this.get_package_wrapper();
		let packages = this.dialog.get_value('packages');

		$.each($package_wrapper.find('.form-grid > .grid-body > .rows > .grid-row'), function (idx, row) {
			var pkg = $(row).find('.grid-row-check:checkbox');

			let package = packages[idx];
			
			if($(pkg).is(':checked')){
				selected_packages.push(package);
				package.__checked = 1;
			} else {
				package.__checked = 0;
			}
		});

		return selected_packages;
	},
	
	bind_events: function($wrapper) {
		let me = this;

		let $package_wrapper = me.get_package_wrapper();

		$package_wrapper.on('click', '.grid-row-check:checkbox', (e) => {
			// let packages = me.dialog.get_value('packages');
			// let selected_packages = me.get_selected_packages();
			// let total_qty = frappe.utils.sum((selected_packages || []).map(row => row.net_weight));
			// me.dialog.set_value('total_qty', total_qty);

			me.update_package_data();
		})

	},

	set_packages_in_frm: function () {
		let me = this;
		let selected_packages = this.get_selected_packages();

		(selected_packages || []).forEach(function(d){
			d.__checked = 0;
			me.frm.add_child('packages', d);
		})

		let total_gross_weight = frappe.utils.sum((this.frm.doc.packages || []).map(row => row.gross_weight));
		let total_tare_weight = frappe.utils.sum((this.frm.doc.packages || []).map(row => row.tare_weight));
		let total_net_weight = frappe.utils.sum((this.frm.doc.packages || []).map(row => row.net_weight));
		let total_spools = frappe.utils.sum((this.frm.doc.packages || []).map(row => row.spools));

		this.frm.set_value('total_gross_weight', flt(total_gross_weight, 3));
		this.frm.set_value('total_tare_weight', flt(total_tare_weight, 3));
		this.frm.set_value('total_net_weight', flt(total_net_weight, 3));
		this.frm.set_value('total_spools', flt(total_spools, 3));
		this.frm.set_value('total_packages', this.frm.doc.packages.length || 0);

		refresh_field('packages');
	},

	get_package_filters: function(){
		let me = this;
		let values = this.dialog.get_values();
		let filters = {
			'warehouse': this.warehouse
		};

		if(!values.item_code){
			frappe.throw(__("Please set Item Code!"))
		} else {
			filters['item_code'] = values.item_code;
		}

		if(!values.merge){
			frappe.throw(__("Please set Merge!"))
		} else {
			filters['merge'] = values.merge;
		}

		if(values.grade){
			filters['grade'] = values.grade;
		}

		if(values.paper_tube){
			filters['paper_tube'] = values.paper_tube;
		}

		if(values.spools){
			filters['spools'] = values.spools;
		}

		if(values.package){
			filters['package'] = values.package;
		}

		return filters;
	},

	set_filtered_package_data: function() {
		let me = this;
		let filters = this.get_package_filters();
		let packages = this.dialog.fields_dict.packages;

		let data = this.package_data.filter(function(row){
			let flag = 1;

			$.each(filters, function(key, value){
				if(row[key].toString().indexOf(value.toString()) > -1 && flag){
					flag = 1;
				} else { flag = 0 }

				if(flag == 0) {
					return false;
				}
			})

			return flag == 1;
		});

		let filtered_data = me.get_remove_selected_packages(data);

		// packages.grid.df.data = data;
		packages.grid.df.data = filtered_data;
		packages.grid.refresh();
	},

	get_packages: function(filters){
		let me = this;
		let packages = this.dialog.fields_dict.packages;

		if(!filters['item_code']){
			packages.grid.df.data = [];
			packages.grid.refresh();
			return;
		}


		filters['company'] = me.frm.doc.company;
		filters['purchase_date'] = ["<=", me.frm.doc.posting_date];
		let raw_filters = ` and CONCAT(purchase_date, " ", purchase_time) <= "${me.frm.doc.posting_date} ${me.frm.doc.posting_time}"`

		frappe.call({
			method: "spinning.spinning.doctype.package.package.get_packages",
			freeze: true,
			args: {
				'filters': filters,
				'raw_filters': raw_filters,
			},
			callback: function(r){
				packages.grid.df.data = r.message;
				packages.grid.refresh();
				me.set_package_data();
			},
		});
	},

	set_package_data: function() {
		let me = this;
		this.package_data = this.dialog.get_value('packages');
	},

	update_package_data: function() {
		let me = this;
		let selected_packages = this.get_selected_packages();
		let total_qty = 0;

		this.package_data.forEach(function(row) {
			selected_packages.forEach(function(d) {
				if(row.package == d.package) {
					row.__checked = d.__checked;
				}
			});

			if(row.__checked){
				total_qty += row.net_weight;
			}
		});

		me.dialog.set_value('total_qty', total_qty);
	},

	get_remove_selected_packages: function(data) {
		let me = this;
		let remove_selected = this.dialog.get_value('remove_selected');

		if(!remove_selected){
			return data;
		} else {
			let filtered_data = data.filter(function(row) {
				return !me.package_exists(row.package);
			});

			return filtered_data;
		}
	},

	package_exists: function(package){
		const packages = this.frm.doc.packages.map(data => data.package);
		return (packages && in_list(packages, package)) ? true : false;
	},
});
