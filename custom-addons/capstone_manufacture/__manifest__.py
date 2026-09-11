{
    'name': 'Capstone Manufacture',
    'version': '17.0.2.0.0',
    'category': 'Manufacturing/Manufacturing',
    'summary': 'Employee access, output locations, and piece or batch manufacturing costs',
    'author': 'Capstone',
    'license': 'LGPL-3',
    'depends': ['mrp_account', 'hr'],
    'data': [
        'security/manufacture_security.xml',
        'views/mrp_workcenter_views.xml',
        'views/mrp_bom_views.xml',
        'views/mrp_production_views.xml',
        'views/mrp_costing_views.xml',
    ],
    'installable': True,
    'application': False,
}
