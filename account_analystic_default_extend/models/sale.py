# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class SaleOrder(models.Model):
    _inherit = "sale.order"

    @api.multi
    def action_invoice_create(self, grouped=False, final=False):
        self = self.with_context(dict(self._context, force_document_type='saleorder'))
        return super(SaleOrder, self).action_invoice_create(grouped=grouped, final=final)

    #@api.multi
    #def _prepare_invoice(self):
    #    invoice_vals = super(SaleOrder, self)._prepare_invoice()
    #    default_analytic_account = self.env['account.analytic.default'].account_get(False, self.partner_id.id, self.user_id.id,
    #                                                fields.Date.today(), operation_type='debit',
    #                                                country_id=self.partner_id.country_id.id, documents_type='out_invoice')
    #    if default_analytic_account:
    #        invoice_vals.update({'account_analytic_id': default_analytic_account.analytic_id.id})
    #        invoice_vals.update({'analytic_tag_ids' : [(6, 0, default_analytic_account.analytic_tag_ids.ids)]})
    #    return invoice_vals