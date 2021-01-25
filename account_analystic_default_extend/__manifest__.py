# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Account Analytic Defaults extend',
    'version': '1.0',
    'category': 'Accounting',
    'description': """
Set default values for your analytic accounts.
==============================================

Allows to automatically select analytic accounts based on criterions:
---------------------------------------------------------------------
    * Product
    * Category
    * Partner
    * Country
    * State
    * User
    * Company
    * Location in store
    * Date
    """,
    'website': 'https://www.odoo.com/page/accounting',
    'depends': ['account_analytic_default', 'account', 'sale', 'stock'],
    'data': [
        'views/account_analytic_default_view.xml',
        'views/account_invoice_views.xml',
    ],
    'installable': True,
}
