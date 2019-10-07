# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    "name" : "Fill analistic tag on invoice in open mode",
    "version" : "11.0.1.0",
    "author" : "Rosen Vladimirov",
    'category': 'hidden',
    "description": """
    """,
    'depends': [
        'account',
    ],
    "demo" : [],
    "data" : [
        'views/account_invoice_view.xml',
    ],
    'license': 'AGPL-3',
    'installable': True,
}
