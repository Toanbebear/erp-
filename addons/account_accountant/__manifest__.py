# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Accounting',
    'version': '1.1',
    'category': 'Accounting/Accounting',
    'sequence': 35,
    'summary': 'Manage financial and analytic accounting',
    'description': """
Accounting Access Rights
========================
It gives the Administrator user access to all accounting features such as journal items and the chart of accounts.

It assigns manager and user access rights to the Administrator for the accounting application and only user rights to the Demo user.
""",
    'website': 'https://www.odoo.com/page/accounting',
    'depends': ['account'],
    'data': [
        'data/account_accountant_data.xml',
        'data/digest_data.xml',
        'security/account_accountant_security.xml',
        'views/account_accountant_templates.xml',
        'views/account_move_views.xml',
        'views/digest_views.xml',
        'views/res_config_settings_views.xml',
        'views/product_views.xml',
        'wizard/account_change_lock_date.xml',
    ],
    'demo': ['data/account_accountant_demo.xml'],
    'test': [],
    'installable': True,
    'auto_install': False,
    'application': True,
    'uninstall_hook': "uninstall_hook",
    'license': 'OEEL-1',
}
