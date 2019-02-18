# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

import logging
_logger = logging.getLogger(__name__)


class AccountAnalyticDefault(models.Model):
    _inherit = "account.analytic.default"

    analytic_tag_ids = fields.Many2many(comodel_name='account.analytic.tag', relation="rel_default_analytic_tag", string='Debit Analytic tags', ondelete='restrict')

    categ_id = fields.Many2one('product.category', string='Internal Category', ondelete='restrict')
    state_id = fields.Many2one("res.country.state", string='State', ondelete='restrict')
    country_id = fields.Many2one('res.country', string='Country', ondelete='restrict')
    location_id = fields.Many2one('stock.location', string='Source Location', ondelete='restrict')
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
                                        ('boot', 'For Debit and Credit'),
                                        ('debit', 'For Debit'),
                                        ('credit', 'For Credit'),
                                        ], string="Operation type", help="Choice type of operation", required=True)
    documents_type = fields.Selection([
                                        ('saleorder', 'From Sale Order'),
                                        ('purchaseorder', 'From Purchase Order'),
                                        ('in_invoice', 'Ventor bill'),
                                        ('in_refund', 'Ventor Credit Note'),
                                        ('out_invoice', 'Customer invoice'),
                                        ('out_refund', 'Customer Credit Note'),
                                        ('incoming', 'Income Picking'),
                                        ('outgoing', 'Оutgoing Picking'),
                                        ], string="Document type", help="Choice oring type of documents", required=True)

    @api.model
    def _get_default(self, domain):
        return domain

    @api.model
    def _get_index(self, index):
        return index

    @api.model
    def account_get(self, product_id=None, partner_id=None, user_id=None, date=None, company_id=None, operation_type='boot', categ_id=None, state_id=None, country_id=None, location_id=None, location_usage=None, documents_type='saleorder'):
        def cat_search(cat_id):
            res = []
            cat = self.env['product.category'].browse(cat_id)
            while cat:
                res.append(cat.id)
                cat = cat.parent_id
            return res

        domain = []
        if product_id:
            domain += ['|', ('product_id', '=', product_id)]
            domain += ['|', ('categ_id', 'in', cat_search(categ_id))]
        domain += [('product_id', '=', False)]
        if partner_id:
            domain += ['|', ('partner_id', '=', partner_id)]
            domain += ['|', ('state_id', '=', state_id)]
            domain += ['|', ('country_id', '=', country_id)]
        domain += [('partner_id', '=', False)]
        if location_id:
            domain += ['&', ('location_id', '=', location_id)]
            domain += ['|', ('usage', '=', location_usage)]
        domain += [('location_id', '=', False)]
        domain += self._get_default(domain)
        if company_id:
            domain += ['|', ('company_id', '=', company_id)]
        domain += [('company_id', '=', False)]
        if user_id:
            domain += ['|', ('user_id', '=', user_id)]
        domain += [('user_id', '=', False)]
        if date:
            domain += ['|', ('date_start', '<=', date), ('date_start', '=', False)]
            domain += ['|', ('date_stop', '>=', date), ('date_stop', '=', False)]
        domain += [('operation_type', '=', operation_type), ('documents_type', '=', documents_type)]
        #_logger.info("DOMEIN: %s" % domain)
        best_index = -1
        res = self.env['account.analytic.default']
        for rec in self.search(domain):
            index = 0
            if rec.product_id: index += 1
            if rec.categ_id: index += 1
            if rec.partner_id: index += 1
            if rec.state_id: index += 1
            if rec.country_id: index += 1
            if rec.location_id: index += 1
            index += self._get_index(index)
            if rec.company_id: index += 1
            if rec.user_id: index += 1
            if rec.date_start: index += 1
            if rec.date_stop: index += 1
            if index > best_index:
                res = rec
                best_index = index
            #_logger.info("Line %s" % rec)
        return res


class AccountInvoice(models.Model):
    _inherit = "account.invoice"


    account_analytic_id = fields.Many2one('account.analytic.account', string='Analytic Account')
    analytic_tag_ids = fields.Many2many('account.analytic.tag', string='Analytic Tags')


    @api.model
    def line_get_convert(self, line, part):
        res = super(AccountInvoice, self).line_get_convert(line, part)
        if line['type'] == 'dest':
            res['analytic_account_id'] = self.account_analytic_id.id
            res['analytic_tag_ids'] = [(6, 0, self.analytic_tag_ids.ids)]
        return res

    @api.model
    def create(self, vals):
        if 'partner_id' in vals:
            documents_type = self._context.get('type', 'out_invoice')
            operation_type = 'debit' if documents_type in ('out_invoice', 'in_refund') else 'credit'
            rec = self.env['account.analytic.default'].account_get(partner_id=vals['partner_id'], user_id=vals['user_id'], date=fields.Date.today(),
                                                                   company_id=vals['company_id'], operation_type=operation_type, documents_type=documents_type)
            if rec:
                vals['account_analytic_id'] = rec.analytic_id.id
                vals['analytic_tag_ids'] = [(6, 0, res.analytic_tag_ids.ids)]
        return super(AccountInvoice, self).create(vals)

    @api.multi
    def write(self, vals):
        res = super(AccountInvoice, self).write(vals)
        if 'partner_id' in vals:
            partner_id = self.env['res.partner'].browse(vals['partner_id']).commercial_partner_id
            documents_type = self.type
            operation_type = 'debit' if documents_type in ('out_invoice', 'in_refund') else 'credit'
            rec = self.env['account.analytic.default'].account_get(partner_id=partner_id.id, user_id=self.user_id, country_id=partner_id.country_id.id,
                                                                date=fields.Date.today(), company_id=self.company_id.id, operation_type=operation_type, documents_type=documents_type)
            if rec:
                self.account_analytic_id = self.analytic_id.id
                self.analytic_tag_ids = [(6, 0, self.analytic_tag_ids.ids)]
        return res

    def _prepare_invoice_line_from_po_line(self, line):
        documents_type = self.type
        operation_type = 'debit' if documents_type in ('out_invoice', 'in_refund') else 'credit'
        res = self._prepare_invoice_line_from_po_line(line)
        rec = self.env['account.analytic.default'].account_get(self.product_id.id, self.invoice_id.commercial_partner_id.id, self.env.uid,
                                                            fields.Date.today(), company_id=self.company_id.id, operation_type=operation_type,
                                                            categ_id=self.product_id.product_tmpl_id.categ_id.id, state_id=self.invoice_id.commercial_partner_id.state_id.id,
                                                            country_id=self.invoice_id.commercial_partner_id.country_id.id, documents_type=documents_type)
        if rec:
            if not res['account_analytic_id']:
                res['account_analytic_id'] = rec.analytic_id.ids
            res['analytic_tag_ids'] = [(6, 0, list(set().union(rec.analytic_tag_ids.ids + self.analytic_tag_ids and self.analytic_tag_ids.ids or [])))]
        return res


class AccountInvoiceLine(models.Model):
    _inherit = "account.invoice.line"

    @api.onchange('product_id')
    def _onchange_product_id(self):
        operation_type = 'credit' if self.invoice_id.type in ('out_invoice', 'in_refund') else 'debit'
        documents_type = self.type
        res = super(AccountInvoiceLine, self)._onchange_product_id()
        rec = self.env['account.analytic.default'].account_get(self.product_id.id, self.invoice_id.commercial_partner_id.id, self.env.uid,
                                                            fields.Date.today(), company_id=self.company_id.id, operation_type=operation_type,
                                                            categ_id=self.product_id.product_tmpl_id.categ_id.id, state_id=self.invoice_id.commercial_partner_id.state_id.id,
                                                            country_id=self.invoice_id.commercial_partner_id.country_id.id, documents_type=documents_type)
        if rec:
            self.account_analytic_id = rec.analytic_id.id
            self.analytic_tag_ids = [(6, 0, rec.analytic_tag_ids.ids + self.analytic_tag_ids.ids)]
        return res

    def _set_additional_fields(self, invoice):
        _logger.info("DEFAULT %s:%s" % (self.invoice_id.account_analytic_id, self.invoice_id.analytic_tag_ids))
        if not self.account_analytic_id or not self.analytic_tag_ids:
            operation_type = 'credit' if self.invoice_id.type in ('out_invoice', 'in_refund') else 'debit'
            documents_type = self.type
            rec = self.env['account.analytic.default'].account_get(self.product_id.id, self.invoice_id.commercial_partner_id.id, self.env.uid,
                                                                fields.Date.today(), company_id=self.company_id.id, operation_type=operation_type,
                                                                categ_id=self.product_id.product_tmpl_id.categ_id.id, state_id=self.invoice_id.commercial_partner_id.state_id.id,
                                                                country_id=self.invoice_id.commercial_partner_id.country_id.id, documents_type=documents_type)
            if rec:
                if not self.account_analytic_id:
                    self.account_analytic_id = rec.analytic_id.id
                if not self.analytic_tag_ids:
                    self.analytic_tag_ids = [(6, 0, list(set().union(rec.analytic_tag_ids.ids + self.analytic_tag_ids and self.analytic_tag_ids.ids or [])))]

        if not self.invoice_id.account_analytic_id or not self.invoice_id.analytic_tag_ids:
            operation_type = 'debit' if self.invoice_id.type in ('out_invoice', 'in_refund') else 'credit'
            documents_type = self.type
            rec = self.env['account.analytic.default'].account_get(self.product_id.id, self.invoice_id.commercial_partner_id.id, self.env.uid,
                                                                fields.Date.today(), company_id=self.company_id.id, operation_type=operation_type,
                                                                categ_id=self.product_id.product_tmpl_id.categ_id.id, state_id=self.invoice_id.commercial_partner_id.state_id.id,
                                                                country_id=self.invoice_id.commercial_partner_id.country_id.id, documents_type=documents_type)
            if rec:
                self.invoice_id.account_analytic_id = rec.analytic_id.id
                self.invoice_id.analytic_tag_ids = [(6, 0, rec.analytic_tag_ids.ids + self.analytic_tag_ids.ids)]
                self.invoice_id.invalidate_cache(['account_analytic_id', 'analytic_tag_ids'], self.invoice_id)
        super(AccountInvoiceLine, self)._set_additional_fields(invoice)
