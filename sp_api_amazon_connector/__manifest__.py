# -*- coding: utf-8 -*-
{
    'name': 'Amazon Connector',
    'version': '16.0.1.0.0',
    'summary': 'Base connector for the Amazon SP-API. Other modules depend on it.',
    'description': """
        Base module that handles authentication and communication with the
        Amazon Selling Partner API (SP-API).

        Features:
        - Credential configuration from the Odoo UI
        - Automatic access token renewal (expires every hour)
        - Reusable call() method for other modules to build on
        - API call log for troubleshooting
    """,
    'author': 'Gabriel Cabalin',
    'website': 'https://es.fiverr.com/s/aekWpAG',
    'images': ['static/description/banner.png'],
    'category': 'Technical',
    'depends': ['base'],
    'data': [
        'security/ir.model.access.csv',
        'data/amazon_marketplace_data.xml',
        'views/menu_root_views.xml',
        'views/amazon_connection_views.xml',
        'views/amazon_connector_settings_views.xml',
        'views/amazon_api_log_views.xml',
        'views/amazon_marketplace_views.xml',
        'views/menu_views.xml',
        'data/cron.xml',
    ],

    'installable': True,
    'application': False,  # It's a technical library/connector, not a standalone app
    'license': 'LGPL-3',
}
