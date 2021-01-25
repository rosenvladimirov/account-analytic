# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

import logging
_logger = logging.getLogger(__name__)


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
        # _logger.info("ONCHANGE_PURCHASE_ID %s" % dict(self.env.context, force_document_type='purchaseorder'))
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

    def _prepare_tax_line_vals(self, line, tax):
        vals = super(AccountInvoice, self)._prepare_tax_line_vals(line, tax)
        self_type = self._context.get('type', False)
        if not self_type:
            self_type = self.type
        operation_type = 'debit' if self_type in ('out_invoice', 'in_refund') else 'credit'
        rec = self.env['account.analytic.default'].account_get(False, self.commercial_partner_id.id, self.user_id.id,
                                                               fields.Date.today(), operation_type=operation_type,
                                                               country_id=self.commercial_partner_id.country_id.id,
                                                               tax_id=tax['id'],
                                                               documents_type='taxes')
        if rec:
            vals.update({
                'account_analytic_id': rec.analytic_id.id,
                'analytic_tag_ids': [(6, False, rec.analytic_tag_ids.ids)],
            })
        return vals

    @api.model
    def create(self, vals):
        res = super(AccountInvoice, self).create(vals)
        if 'partner_id' in vals:
            if not res.account_analytic_id or not res.analytic_tag_ids:
                self_type = self._context.get('type', False)
                if not self_type:
                    self_type = res.type
                operation_type = 'debit' if self_type in ('out_invoice', 'in_refund') else 'credit'
                rec = self.env['account.analytic.default'].account_get(False, res.commercial_partner_id.id,
                                                                       res.user_id.id,
                                                                       fields.Date.today(),
                                                                       operation_type=operation_type,
                                                                       country_id=res.commercial_partner_id.country_id.id,
                                                                       documents_type=self_type)
                if rec:
                    if not res.account_analytic_id:
                        res.account_analytic_id = rec.analytic_id.id
                    if not res.analytic_tag_ids:
                        res.analytic_tag_ids = rec.analytic_tag_ids.ids
        return res

    @api.multi
    def write(self, vals):
        res = super(AccountInvoice, self).write(vals)
        if 'partner_id' in vals:
            for record in self:
                if  not record.account_analytic_id or not record.analytic_tag_ids:
                    self_type = self._context.get('type', False)
                    if not self_type:
                        self_type = record.type
                    operation_type = 'debit' if self_type in ('out_invoice', 'in_refund') else 'credit'
                    rec = self.env['account.analytic.default'].account_get(False, record.commercial_partner_id.id,
                                                                           record.user_id.id,
                                                                           fields.Date.today(),
                                                                           operation_type=operation_type,
                                                                           country_id=record.commercial_partner_id.country_id.id,
                                                                           documents_type=self_type)
                    if rec:
                        if not record.account_analytic_id:
                            record.account_analytic_id = rec.analytic_id.id
                        if not record.analytic_tag_ids:
                            record.analytic_tag_ids = rec.analytic_tag_ids.ids
        return res


class AccountInvoiceLine(models.Model):
    _inherit = "account.invoice.line"

    @api.onchange('product_id')
    def _onchange_product_id(self):
        res = super(AccountInvoiceLine, self)._onchange_product_id()
        self_type = self._context.get('type', False)
        if not self_type:
            self_type = self.invoice_id.type
        operation_type = 'credit' if self_type in ('out_invoice', 'in_refund') else 'debit'
        rec = self.env['account.analytic.default'].account_get(self.product_id.id, self.invoice_id.commercial_partner_id.id, self.env.uid,
                                                        fields.Date.today(), company_id=self.company_id.id, operation_type=operation_type,
                                                        categ_id=self.product_id.product_tmpl_id.categ_id.id,
                                                        country_id=self.invoice_id.commercial_partner_id.country_id.id, documents_type=self_type)
        if rec:
            self.account_analytic_id = rec.analytic_id.id
            self.analytic_tag_ids = [(6, 0, list(set(rec.analytic_tag_ids.ids + self.analytic_tag_ids.ids)))]
        return res

    def _set_additional_fields(self, invoice):
        # _logger.info("ADDITIONAL FIELDS %s:%s" % (self.account_analytic_id, self.analytic_tag_ids))
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
