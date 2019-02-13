# coding: utf-8
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api, fields, _

import logging
_logger = logging.getLogger(__name__)


class StockMove(models.Model):
    _inherit = "stock.move"

    def _prepare_account_move_line(self, qty, cost, credit_account_id, debit_account_id):
        res = super(StockMove, self)._prepare_account_move_line(qty, cost, credit_account_id, debit_account_id)
        diff_line = False
        # [(0, 0, debit_line_vals), (0, 0, credit_line_vals), ...]
        od, fd, debit_line_vals = res[0] # debit tuple
        oc, fc, credit_line_vals = res[1] # credit tuple
        if len(res) > 2:
            diff_line = True
            od, fd, price_diff_line = res[2] # diff tuple

        operation_type = 'debit'
        default_analytic_account = self.env['account.analytic.default'].account_get(self.product_id.id, self.partner_id.id, self.picking_id.user_id.id,
                                                    fields.Date.today(), operation_type=operation_type, categ_id=self.product_id.product_tmpl_id.categ_id.id,
                                                    state_id=self.partner_id.state_id.id, country_id=self.partner_id.country_id.id,
                                                    location_id=self.location_dest_id.id, location_usage=self.location_dest_id.usage)
        if default_analytic_account:
            debit_line_vals.update({'account_analytic_id': default_analytic_account.analytic_id.id})
            debit_line_vals.update({'analytic_tag_ids' : [(6, 0, default_analytic_account.analytic_tag_ids.ids)]})

        operation_type = 'credit'
        default_analytic_account = self.env['account.analytic.default'].account_get(self.product_id.id, self.partner_id.id, self.picking_id.user_id.id,
                                                    fields.Date.today(), operation_type=operation_type, categ_id=self.product_id.product_tmpl_id.categ_id.id,
                                                    state_id=self.partner_id.state_id.id, country_id=self.partner_id.country_id.id,
                                                    location_id=self.location_id.id, location_usage=self.location_id.usage)
        if default_analytic_account:
            credit_line_vals.update({'account_analytic_id': default_analytic_account.analytic_id.id})
            credit_line_vals.update({'analytic_tag_ids' : [(6, 0, default_analytic_account.analytic_tag_ids.ids)]})

        if diff_line:
            if price_diff_line['credit'] - price_diff_line['debit'] > 0.0:
                operation_type = 'credit'
            else:
                operation_type = 'debit'
            default_analytic_account = self.env['account.analytic.default'].account_get(self.product_id.id, self.partner_id.id, self.picking_id.user_id.id,
                                                        fields.Date.today(), operation_type=operation_type, categ_id=self.product_id.product_tmpl_id.categ_id.id,
                                                        state_id=self.partner_id.state_id.id, country_id=self.partner_id.country_id.id,
                                                        location_id=self.location_dest_id.id, location_usage=self.location_dest_id.usage)
            if default_analytic_account:
                price_diff_line.update({'account_analytic_id': default_analytic_account.analytic_id.id})
                price_diff_line.update({'analytic_tag_ids' : [(6, 0, default_analytic_account.analytic_tag_ids.ids)]})

        return res
