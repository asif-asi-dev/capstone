# -*- coding: utf-8 -*-
{
    'name': "capstone_route_field_service",

    'summary': "Short (1 phrase/line) summary of the module's purpose",

    'description': """
Long description of module's purpose
    """,

    'author': "My Company",
    'website': "https://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.2',

    # any module necessary for this one to work correctly
    'depends': ['base', 'crm', 'sale', 'hr_expense'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'data/day_data.xml',
        'views/views.xml',
        'views/fsm_area_view.xml',
        'views/fsm_route_assignment_view.xml',
        'views/fsm_route_view.xml',
        'views/fsm_shop_visit_view.xml',
        'views/crm_lead_view.xml',
        'data/fsm_shop_visit_sequence.xml',
        'views/sale_order_view.xml',
        'views/hr_expense_view.xml',
        'views/partner_view.xml'
    ],
    # only loaded in demonstration mode
}

