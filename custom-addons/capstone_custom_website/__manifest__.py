{
    'name': 'Capstone Custom Website',
    'version': '17.0.1.0.1',
    'category': 'Website',
    'summary': 'Custom homepage for Capstone Bath Fittings',
    'description': """
        Custom homepage module for Capstone Bath Fittings
        - Modern responsive design
        - Product showcase
        - Company information
        - Contact details
    """,
    'author': 'Your Name',
    'depends': ['website', 'product'],
    'data': [
        'views/website_templates.xml',
        'data/website_menu.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'capstone_custom_website/static/src/css/website.css',
            # 'capstone_custom_website/static/src/scss/website.scss'
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}