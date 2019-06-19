# -*- coding: utf-8 -*-

from odoo import models, fields, api
import hashlib
from datetime import datetime


class PaymentTokenInvoice(models.Model):
    _name = 'payment.token.invoice'
    _description = 'Payment Invoice URL Token'

    token = fields.Char("Payment token", size=128, help="Unique identifier for retrieving an invoice document.")
    invoice_id = fields.Many2one('account.invoice')
    state = fields.Selection(
        [('draft', 'Not Visited Yet'), ('visited', 'Visited'), ('submitted', 'Submitted'), ('paid', 'Paid'),
         ('expired', 'Expired'), ('error', 'Error')], string='Visitor Status', default='draft', readonly=True)

    def edi_token_recreate(self, invoice):
        db_uuid = self.env['ir.config_parameter'].get_param('database.uuid')
        record = self.search([('invoice_id', '=', invoice.id)], limit=1)
        if record:
            token = hashlib.sha256((u'%s-%s-%s' % (db_uuid, invoice.name, datetime.now())).encode('utf-8')).hexdigest()
            record.write({'token': token, 'state': 'draft'})
            return record
        else:
            return self.create_authorization_token_invoice(invoice)

    def create_authorization_token_invoice(self, invoice):
        """
                create a record with payment token,order,invoice
        """
        record = self.search([('invoice_id', '=', invoice.id)], limit=1)
        if record:
            return record
        else:
            db_uuid = self.env['ir.config_parameter'].get_param('database.uuid')
            token = hashlib.sha256((u'%s-%s-%s' % (db_uuid, invoice.name, datetime.now())).encode('utf-8')).hexdigest()
            return self.create(
                {'token': token,  'invoice_id': invoice.id})

    def get_invoice_payment_record(self, invoice):
        """
                returns a  stored payment record of current invoice.
        """

        record = self.search([('invoice_id', '=', invoice.id)], limit=1)
        if record:
            return record.token
        else:
            self.create_authorization_token_invoice(invoice)
            record = self.search([('invoice_id', '=', invoice.id)], limit=1)
            return record.token

