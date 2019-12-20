from frappe import _

def get_data():
	return {
		'fieldname': 'reference_docname',
		'non_standard_fieldnames': {
			'Material Repack': 'material_unpack',
		},
		'transactions': [
			{	
				'label': _('Stock Entry'),
				'items': ['Stock Entry']
			},	
			{	
				'label': _('Repack'),
				'items': ['Material Repack']
			},
		]
	}