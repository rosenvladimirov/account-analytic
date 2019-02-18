# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class ProcurementRule(models.Model):
    _inherit = 'procurement.rule'

    @api.multi
    def _prepare_purchase_order_line(self, product_id, product_qty, product_uom, values, po, supplier):
        res = self._prepare_purchase_order_line(product_id, product_qty, product_uom, values, po, supplier)
        return res

    def _prepare_purchase_order(self, product_id, product_qty, product_uom, origin, values, partner):
        res = self._prepare_purchase_order(product_id, product_qty, product_uom, origin, values, partner)
        return res
