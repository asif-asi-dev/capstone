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
    'version': '17.0.0.4',
    'depends': ['base', 'stock', 'account', 'mail', 'repair'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/complaint_assignment_views.xml',
        'views/complaint_management_views.xml',
        'views/complaint_type_view.xml',
        'data/complaint_sequence.xml',
        'data/assignment_sequence.xml',
        'wizard/feedback_wizard_view.xml',
        'views/template_complaint_form.xml',
        'views/menu.xml',
    ],
}

