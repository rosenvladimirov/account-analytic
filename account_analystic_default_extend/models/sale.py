# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class SaleOrder(models.Model):
    _inherit = "sale.order"

    @api.multi
    def _prepare_invoice(self):
        operation_type = 'debit'
        invoice_vals = super(SaleOrder, self)._prepare_invoice()
        default_analytic_account = self.env['account.analytic.default'].account_get(False, self.partner_id.id, self.user_id.id,
                                                    fields.Date.today(), operation_type=operation_type,
                                                    state_id=self.partner_id.state_id.id, country_id=self.partner_id.country_id.id)
        if default_analytic_account:
            invoice_vals.update({'account_analytic_id': default_analytic_account.analytic_id.id})
            invoice_vals.update({'analytic_tag_ids' : [(6, 0, default_analytic_account.analytic_tag_ids.ids)]})

        return invoice_vals
