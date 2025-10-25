# -*- coding: utf-8 -*-
{
    'name': "capstone_complaint_management",

    'summary': "Short (1 phrase/line) summary of the module's purpose",

    'description': """
Long description of module's purpose
    """,
    'author': "My Company",
    'website': "https://www.yourcompany.com",
    'category': 'Uncategorized',
    'version': '17.0.0.8',
    'depends': ['base', 'stock', 'account', 'mail', 'repair', 'capstone_sales_return_custom'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/complaint_sequence.xml',
        'data/assignment_sequence.xml',
        'views/complaint_assignment_views.xml',
        'views/complaint_management_views.xml',
        'views/complaint_type_view.xml',
        'wizard/feedback_wizard_view.xml',
        'views/template_complaint_form.xml',
        'views/sale_return_request_view.xml',
        'views/repair_view.xml',
        'views/menu.xml',
    ],
}

