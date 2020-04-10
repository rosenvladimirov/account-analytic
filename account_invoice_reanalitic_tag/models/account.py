# coding: utf-8
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from lxml import etree

from odoo import models, api, fields, _
from odoo.exceptions import UserError
#from odoo.osv.orm import setup_modifiers

import logging
_logger = logging.getLogger(__name__)


class AccountInvoice(models.Model):
    _inherit = "account.invoice"

    invoice_line_ids = fields.One2many(states={'draft': [('readonly', False)], 'edit': [('readonly', False)]})
    state = fields.Selection(selection_add=[('edit', 'Accountant mode')])

    @api.multi
    def action_invoice_edit(self):
        #_logger.info("Edit mode %s" % self.filtered(lambda inv: inv.state == 'edit'))
        if self.filtered(lambda inv: inv.state == 'edit'):
            self.filtered(lambda inv: inv.state == 'edit').write({'state': 'open'})
            return True
        if self.filtered(lambda inv: inv.state != 'open'):
            raise UserError(_("Invoice must be open mode."))
        # go from canceled state to draft state
        self.write({'state': 'edit'})
        invoice_type = {'out_invoice': ('customer invoices credit note'),
                        'in_invoice': ('vendor bill credit note')}
        message = _("This %s has been switch to Accountant mode. The document: <a href=# data-oe-model=account.invoice data-oe-id=%d>%s</a>") % (invoice_type[self.type], self.id, self.number)
        self.message_post(body=message)
        return True


class AccountInvoiceLine(models.Model):
    _inherit = "account.invoice.line"

    state = fields.Selection(related="invoice_id.state", string="Invoice status")


    def _set_to_draft(self):
        if self.invoice_id and self.invoice_id.state == 'edit':
            invoice = self.invoice_id
            #_logger.info("INVOICE %s" % invoice)
            invoice.write({'state': 'open'})
            invoice.action_invoice_cancel()
            invoice.action_invoice_draft()
            invoice.action_invoice_open()


    @api.multi
    def write(self, vals):
        res = super(AccountInvoiceLine, self).write(vals)
        self.ensure_one()
        if self.invoice_id.state == 'edit' and (vals.get('analytic_tag_ids') or vals.get('account_analytic_id')):
            self._set_to_draft()
        return res
