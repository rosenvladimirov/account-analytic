# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

import logging
_logger = logging.getLogger(__name__)


class AccountAnalyticDefault(models.Model):
    _inherit = "account.analytic.default"

    analytic_tag_ids = fields.Many2many(comodel_name='account.analytic.tag', relation="rel_default_analytic_tag", string='Debit Analytic tags', ondelete='restrict')

    categ_id = fields.Many2one('product.category', string='Internal Category', ondelete='restrict', domain=[('child_id', '=', False)])
    #state_id = fields.Many2one("res.country.state", string='State', ondelete='restrict')
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
    def account_get(self, product_id=None, partner_id=None, user_id=None, date=None, company_id=None, operation_type='boot', categ_id=None, country_id=None, location_id=None, location_usage=None, documents_type='saleorder'):
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

        domain = []
        if product_id:
            domain += ['|', ('product_id', '=', product_id)]
            #domain += ['|', ('categ_id', 'in', cat_search(categ_id))]
            domain += [('categ_id', '=', categ_id)]
        domain += [('product_id', '=', False)]
        if partner_id:
            domain += ['|', ('partner_id', '=', partner_id)]
            domain += [('country_id', '=', country_id)]
        domain += [('partner_id', '=', False)]
        if location_id:
            domain += ['|', ('location_id', 'in', location_search(location_id))]
            domain += [('usage', '=', location_usage)]
        domain += [('location_id', '=', False)]
        domain = self._get_default(domain)
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
        _logger.info("DOMAIN: %s" % domain)
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
            _logger.info("Line %s:%s=>%s" % (rec.categ_id, rec.analytic_id.name, best_index))
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

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        res = super(AccountInvoice, self)._onchange_partner_id()
        # render for header
        if not self.account_analytic_id or not self.analytic_tag_ids:
            self_type = self._context.get('type', False)
            if not self_type:
                self_type = self.type
            operation_type = 'debit' if self_type in ('out_invoice', 'in_refund') else 'credit'
            rec = self.env['account.analytic.default'].account_get(False, self.commercial_partner_id.id, self.user_id.id,
                                                fields.Date.today(), operation_type=operation_type,
                                                country_id=self.commercial_partner_id.country_id.id, documents_type=self_type)
            if rec:
                if not self.account_analytic_id:
                    self.account_analytic_id = rec.analytic_id.id
                if not self.analytic_tag_ids:
                    self.analytic_tag_ids = rec.analytic_tag_ids.ids
        return res

    @api.onchange('purchase_id')
    def purchase_order_change(self):
        _logger.info("ONCHANGE_PURCHASE_ID %s" % dict(self.env.context, force_document_type='purchaseorder'))
        if not self.purchase_id:
            return {}
        if not self.partner_id:
            self.partner_id = self.purchase_id.partner_id.id

        new_lines = self.env['account.invoice.line']
        for line in self.purchase_id.order_line - self.invoice_line_ids.mapped('purchase_line_id'):
            data = self._prepare_invoice_line_from_po_line(line)
            new_line = new_lines.new(data)
            new_line.with_context(dict(self.env.context, force_document_type='purchaseorder'))._set_additional_fields(self)
            new_lines += new_line

        self.invoice_line_ids += new_lines
        self.payment_term_id = self.purchase_id.payment_term_id
        self.env.context = dict(self.env.context, from_purchase_order_change=True)
        self.purchase_id = False
        return {}


class AccountInvoiceLine(models.Model):
    _inherit = "account.invoice.line"

    @api.onchange('product_id')
    def _onchange_product_id(self):
        self_type = self._context.get('type', False)
        if not self_type:
            self_type = self.invoice_id.type
        operation_type = 'credit' if self_type in ('out_invoice', 'in_refund') else 'debit'
        res = super(AccountInvoiceLine, self)._onchange_product_id()
        rec = self.env['account.analytic.default'].account_get(self.product_id.id, self.invoice_id.commercial_partner_id.id, self.env.uid,
                                                        fields.Date.today(), company_id=self.company_id.id, operation_type=operation_type,
                                                        categ_id=self.product_id.product_tmpl_id.categ_id.id,
                                                        country_id=self.invoice_id.commercial_partner_id.country_id.id, documents_type=self_type)
        if rec:
            self.account_analytic_id = rec.analytic_id.id
            self.analytic_tag_ids = [(6, 0, list(set().union(rec.analytic_tag_ids.ids + self.analytic_tag_ids.ids)))]
        return res

    def _set_additional_fields(self, invoice):
        _logger.info("ADDITIONAL FIELDS %s:%s" % (self.account_analytic_id, self.analytic_tag_ids))
        account_analytic = self.env['account.analytic.default']

        # render for lines
        if not self.account_analytic_id or not self.analytic_tag_ids:
            self_type = self._context.get('type', False)
            if not self_type:
                self_type = invoice.type
            if self._context.get('purchaseorder', False):
                operation_type = 'debit'
            elif self._context.get('saleorder', False):
                operation_type = 'credit'
            else:
                operation_type = 'credit' if self_type in ('out_invoice', 'in_refund') else 'debit'

            rec = account_analytic.account_get(self.product_id.id, invoice.commercial_partner_id.id, self.env.uid,
                                                                fields.Date.today(), company_id=self.company_id.id, operation_type=operation_type,
                                                                categ_id=self.product_id.product_tmpl_id.categ_id.id,
                                                                country_id=invoice.commercial_partner_id.country_id.id, documents_type=self_type)
            if rec:
                if not self.account_analytic_id:
                    self.account_analytic_id = rec.analytic_id.id
                _logger.info("self.analytic_tag_ids.ids = %s" % (list(set().union(rec.analytic_tag_ids.ids + self.analytic_tag_ids.ids))))
                if self.analytic_tag_ids:
                    self.analytic_tag_ids = rec.analytic_tag_ids.ids

        # render for header
        if not invoice.account_analytic_id or not invoice.analytic_tag_ids:
            operation_type = 'credit' if operation_type == 'debit' else 'debit'
            rec = account_analytic.account_get(False, invoice.commercial_partner_id.id, invoice.user_id.id,
                                                fields.Date.today(), operation_type=operation_type,
                                                country_id=invoice.commercial_partner_id.country_id.id, documents_type=self_type)
            if rec:
                if not invoice.account_analytic_id:
                    invoice.account_analytic_id = rec.analytic_id.id
                if not invoice.analytic_tag_ids:
                    invoice.analytic_tag_ids = rec.analytic_tag_ids.ids
        super(AccountInvoiceLine, self)._set_additional_fields(invoice)
