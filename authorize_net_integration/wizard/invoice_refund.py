# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError

class AccountInvoiceRefund(models.TransientModel):
    _inherit = "account.invoice.refund"

    @api.multi
    def invoice_refund(self):
        context = dict(self._context or {})
        res = super(AccountInvoiceRefund, self).invoice_refund()
        invoice = self.env['account.invoice'].browse(context.get('active_id'))
        if invoice and invoice.payment_id and res.get('domain', False):
            refunded_invoice = self.env['account.invoice'].search(res.get('domain', False))
            refunded_invoice.write({'payment_id': invoice.payment_id, 'invoice_origin_id': invoice.id, 'transaction_date': invoice.transaction_date, 'transaction_id': invoice.transaction_id})
        elif invoice and invoice.transaction_id and res.get('domain', False):
            refunded_invoice = self.env['account.invoice'].search(res.get('domain', False))
            refunded_invoice.write({'transaction_id': invoice.transaction_id, 'invoice_origin_id': invoice.id, 'transaction_date': invoice.transaction_date})
        return res
