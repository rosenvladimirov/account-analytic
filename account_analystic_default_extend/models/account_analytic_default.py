# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _

import logging
_logger = logging.getLogger(__name__)


class AccountAnalyticDefault(models.Model):
    _inherit = "account.analytic.default"

    analytic_tag_ids = fields.Many2many(comodel_name='account.analytic.tag', relation="rel_default_analytic_tag", string='Debit Analytic tags', ondelete='restrict')

    categ_id = fields.Many2one('product.category', string='Internal Category', ondelete='restrict', domain=[('child_id', '=', False)])
    #state_id = fields.Many2one("res.country.state", string='State', ondelete='restrict')
    country_id = fields.Many2one('res.country', string='Country', ondelete='restrict')
    location_id = fields.Many2one('stock.location', string='Source Location', ondelete='restrict')
    tax_id = fields.Many2one('account.tax', string='Tax', ondelete='restrict')
    usage = fields.Selection([
        ('supplier', 'Vendor Location'),
        ('view', 'View'),
        ('internal', 'Internal Location'),
        ('customer', 'Customer Location'),
        ('inventory', 'Inventory Loss'),
        ('procurement', 'Procurement'),
        ('production', 'Production'),
        ('transit', 'Transit Location')], string='Location Type',
        help="* Vendor Location: Virtual location representing the source location for products coming from your vendors"
             "\n* View: Virtual location used to create a hierarchical structures for your warehouse, aggregating its child locations ; can't directly contain products"
             "\n* Internal Location: Physical locations inside your own warehouses,"
             "\n* Customer Location: Virtual location representing the destination location for products sent to your customers"
             "\n* Inventory Loss: Virtual location serving as counterpart for inventory operations used to correct stock levels (Physical inventories)"
             "\n* Procurement: Virtual location serving as temporary counterpart for procurement operations when the source (vendor or production) is not known yet. This location should be empty when the procurement scheduler has finished running."
             "\n* Production: Virtual counterpart location for production operations: this location consumes the raw material and produces finished products"
             "\n* Transit Location: Counterpart location that should be used in inter-company or inter-warehouses operations")
    operation_type = fields.Selection([
                                        ('boot', _('For Debit and Credit')),
                                        ('debit', _('For Debit')),
                                        ('credit', _('For Credit')),
                                        ], string="Operation type", help="Choice type of operation", required=True)
    documents_type = fields.Selection([
                                        ('saleorder', _('From Sale Order')),
                                        ('purchaseorder', _('From Purchase Order')),
                                        ('in_invoice', _('Ventor bill')),
                                        ('in_refund', _('Ventor Credit Note')),
                                        ('out_invoice', _('Customer invoice')),
                                        ('out_refund', _('Customer Credit Note')),
                                        ('incoming', _('Income Picking')),
                                        ('outgoing', _('Оutgoing Picking')),
                                        ('taxes', _('Taxes in document'))
                                        ], string="Document type", help="Choice oring type of documents", required=True)

    @api.model
    def _get_default(self, domain):
        return domain

    @api.model
    def _get_index(self, index):
        return index

    @api.model
    def account_get(self, product_id=None, partner_id=None, user_id=None, date=None, company_id=None, operation_type='boot', categ_id=None, country_id=None, location_id=None, location_usage=None, tax_id=None, documents_type='saleorder'):
        def cat_search(cat_id):
            res = []
            cat = self.env['product.category'].browse(cat_id)
            while cat:
                res.append(cat.id)
                cat = cat.parent_id
                _logger.info("Category %s" % cat.name)
            return res

        def location_search(location_id):
            res = []
            location = self.env['stock.location'].browse(location_id)
            while location:
                res.append(location.id)
                location = location.location_id
            return res

        domain = [('operation_type', '=', operation_type), ('documents_type', '=', documents_type)]
        # first add static filters for AND
        if company_id:
            domain += [('company_id', '=', company_id)]
        #domain += [('company_id', '=', False)]
        # domain += ['|', ('categ_id', 'in', cat_search(categ_id))]
        #if user_id: # One user make for all users
        #    domain += [('user_id', '=', user_id)]
        if not partner_id:
            domain += [('partner_id', '=', False)]
        if not location_id:
            domain += [('location_id', '=', False)]
        if not product_id:
            domain += [('product_id', '=', False)]
        # After add OR filters
        if product_id:
            domain += ['|', ('product_id', '=', product_id), ('product_id', '=', False)]
            domain += ['|', ('categ_id', '=', categ_id), ('categ_id', '=', False)]
        if partner_id:
            domain += ['|', ('partner_id', '=', partner_id), ('partner_id', '=', False)]
            domain += ['|', ('country_id', '=', country_id), ('country_id', '=', False)]
        if location_id:
            domain += ['|', ('location_id', 'in', location_search(location_id)), ('location_id', '=', False)]
            domain += ['|', ('usage', '=', location_usage)]
        if tax_id:
            domain += ['|', ('tax_id', '=', tax_id), ('tax_id', '=', False)]
        domain = self._get_default(domain)
        if date:
            domain += ['|', ('date_start', '<=', date), ('date_start', '=', False)]
            domain += ['|', ('date_stop', '>=', date), ('date_stop', '=', False)]
        #_logger.info("DOMAIN: %s" % domain)
        best_index = -1
        res = self.env['account.analytic.default']
        for rec in self.search(domain):
            index = 0
            if rec.product_id: index += 1
            if rec.categ_id: index += 1
            if rec.partner_id: index += 1
            if rec.country_id: index += 1
            if rec.location_id: index += 1
            index = self._get_index(index)
            if rec.company_id: index += 1
            if rec.user_id: index += 1
            if rec.date_start: index += 1
            if rec.date_stop: index += 1
            if index > best_index:
                res = rec
                best_index = index
            #_logger.info("Line %s:%s=>%s" % (rec.categ_id, rec.analytic_id.name, best_index))
        return res
