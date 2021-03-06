# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    @api.multi
    def _prepare_invoice_line(self, qty):
        operation_type = 'credit'
        documents_type = 'saleorder'
        res = super(SaleOrderLine, self)._prepare_invoice_line(qty)
        default_analytic_account = self.env['account.analytic.default'].account_get(self.product_id.id, self.order_id.partner_id.id, self.order_id.user_id.id,
                                                    fields.Date.today(), operation_type=operation_type, categ_id=self.product_id.product_tmpl_id.categ_id.id,
                                                    country_id=self.order_id.partner_id.country_id.id, documents_type=documents_type)
        if default_analytic_account:
            res.update({'account_analytic_id': default_analytic_account.analytic_id.id})
            res.update({'analytic_tag_ids' : [(6, 0, default_analytic_account.analytic_tag_ids.ids)]})
        return res
