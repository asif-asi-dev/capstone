# -*- coding: utf-8 -*-
{
    'name': "Capstone Base",
    'summary': "Base module for Capstone specific configurations and staff structure.",
    'description': """
        This module defines the basic structure for Capstone, including:
        - Staff Grouping Structure
        - Basic configurations
    """,
    'author': "My Company",
    'website': "https://www.yourcompany.com",
    'category': 'Customizations',
    'version': '17.0.1.0.0',
    'depends': ['base', 'web_responsive'],
    'data': [
        'security/groups.xml',
        'views/web_responsive_patch.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
