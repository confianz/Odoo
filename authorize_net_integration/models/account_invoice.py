# coding:utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError

class AccountInvoice(models.Model):
    _inherit = 'account.invoice'
    
    transaction_id = fields.Char('Transaction ID', copy=False)
    transaction_date = fields.Datetime('Transaction Date', copy=False)    
    due_amount_authorize = fields.Float('Due')
    is_refund = fields.Boolean('Is Refunded', default=False, copy=False)
    transaction_id_refund = fields.Char("Refunded transaction ID")
    payment_id = fields.Char('Payment ID', copy=False)
    invoice_origin_id = fields.Many2one('account.invoice', "Invoice Origin ID")
    refund_invoice_ids = fields.One2many('account.invoice', 'invoice_origin_id', string="Refunded Ids")
    
    @api.multi
    def action_invoice_sent(self):
        """ Open a window to compose an email, with the invoice template
            message loaded by default, and authorize.net link.
        """
        self.ensure_one()
        if self.type in ['in_invoice', 'out_refund'] or self.state in ['paid', 'cancel']: #vendor bill & customer credit note
            return super(AccountInvoice, self).action_invoice_sent()
        template = self.env.ref('authorize_net_integration.email_template_edi_invoice', False)
        compose_form = self.env.ref('account.account_invoice_send_wizard_form', False)
        ctx = dict(
            default_model='account.invoice',
            default_res_id=self.id,
            default_use_template=bool(template),
            default_template_id=template and template.id or False,
            default_composition_mode='comment',
            mark_invoice_as_sent=True,
            custom_layout="mail.mail_notification_paynow",
            force_email=True
        )
        return {
            'name': _('Send Invoice'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'account.invoice.send',
            'views': [(compose_form.id, 'form')],
            'view_id': compose_form.id,
            'target': 'new',
            'context': ctx,
        }
        
        
    def get_invoice_payment_url(self):
        """
        return the payment url
        :return:
        """
        token = self.env['payment.token.invoice'].get_invoice_payment_record(self)
        web_root_url = self.env['ir.config_parameter'].get_param('web.base.url')
        VIEW_WEB_URL = '%s/web/payment/invoice?token=%s' % (web_root_url, token)

        return VIEW_WEB_URL
        
    
    def check_if_authorize_configured(self):
        auth_rec = self.env['authorizenet.api'].search([('active', '=', True)], limit=1, order="sequence")
        if len(auth_rec) == 1:
            return True
        else:
            return False
    
    @api.model
    def aim_transaction_invoice(self, invoice_list=None, amount=None, card=None, cvv=None, expiry=None, invoice=None,
                                account_name=None, routing_number=None, account_number=None,
                                bank_name=None, eCheque_type=None, account_type=None):
        """
        :param invoice_list: contains the invoices selected in the  website
        :param amount: the final payment amount
        :param card:
        :param cvv:
        :param expiry:
        :param account_name: account name for eCheck payments
        :param routing_number: routing number for eCheck payments
        :param account_number: account number for eCheck payments
        :param bank_name: bank name for eCheck payments
        :param eCheque_type: eCheque type for eCheck payments
        :param account_type: account type for eCheck payments
        :return:
        """
        if account_number and routing_number:
            transaction_id_aim, error = self.env['authorizenet.api'].authorize_capture_cheque_transaction_aim(
                amount=amount,
                invoice=invoice, account_name=account_name,
                routing_number=routing_number,
                account_number=account_number, bank_name=bank_name,
                eCheque_type=eCheque_type, account_type=account_type)
        else:
            transaction_id_aim, error = self.env['authorizenet.api'].authorize_capture_transaction_aim(amount, str(card), str(cvv), str(expiry), invoice)
        if error:
            self.env['error.box'].create({
                'error_message': error,
                'order': self.env['account.invoice'].browse(int(invoice)).number
            })
            return False, error
        invoices = []
        for inv in invoice_list:
            invoice = self.browse(inv)
            invoice.write({'transaction_id': transaction_id_aim, 'transaction_date': fields.Datetime.now()})
            invoices.append(invoice.id)
            if invoice.type == 'out_refund' and invoice.transaction_id:
                invoice.write({'is_refund': True})
                if invoice.invoice_origin_id:
                    invoice.invoice_origin_id.write({'is_refund': True})
        
        invoice_id = self.browse(invoices[0])
        if invoice_id:
            Journal = self.env['account.journal'].search([('is_authorizenet', '=', True)], limit=1)
            payment_type = invoice_id and invoice_id.type in ('out_invoice', 'in_refund') and 'inbound' or 'outbound'
            payment_methods = payment_type == 'inbound' and Journal.inbound_payment_method_ids or Journal.outbound_payment_method_ids
            payment_method_id = payment_methods and payment_methods[0] or False
            register_payments = self.env['account.register.payments'].with_context({
                'active_model': 'account.invoice',
                'active_ids': invoices,
                'default_transaction_id': transaction_id_aim,
                'from_authorize': 'no_discount',
            }).create({
                'payment_date': fields.Date.context_today(self),
                'journal_id': Journal.id,
                'payment_method_id': payment_method_id and payment_method_id.id,
                'amount': float(amount)
            })
            payment = self.env['account.payment']
            for payment_vals in register_payments.get_payments_vals():
                payment += self.env['account.payment'].create(payment_vals)
            payment.write({'transaction_id': transaction_id_aim})
            payment.post()
        return transaction_id_aim, error


    @api.multi
    def action_cancel(self):
        """ 
        Void payment from Authorize.Net
        @return: super
        """
        for invoice in self:
            if invoice.payment_id and not invoice.is_refund:
                profile_id = invoice.partner_id._get_profile_id()
                response, msg, code = self.env['authorizenet.api'].void_payment(profile_id, invoice.payment_id, invoice.transaction_id)
                if not response:
                    raise UserError(_("In order to cancel this order refund the settled invoices\
                                      strictly via Refund Invoice button in the invoices and try again."))
            elif invoice.transaction_id and not invoice.is_refund:
                response, msg, code = self.env['authorizenet.api'].void_transaction_aim(invoice.transaction_id)
                if not response:
                    raise UserError(_("In order to cancel this order refund the settled invoices\
                                                          strictly via Refund Invoice button in the invoices and try again."))
            if invoice.is_refund and invoice.transaction_id_refund:
                refunded_ids = invoice.refund_invoice_ids.filtered(lambda inv: inv.state in ['open','paid'])
                if refunded_ids and sum(refunded_ids.mapped('amount_total')) < invoice.amount_total:
                    # TODO partially paid credit notes?
                    raise UserError(_("You cannot cancel a partially refunded order"))
                return
            else:
                res = super(AccountInvoice, self).action_cancel()
                return res

    @api.multi
    def register_card_payments(self):
        """
                register payments and make the invoice as paid
        """

        self.ensure_one()
        self.action_invoice_open()
        Journal = self.env['account.journal'].search([('is_authorizenet', '=', True)], limit=1)
        if not Journal:
            raise UserError(_('Error! \n Please Select The Authorize.net Journal.(Accounting->configuration->journal->Authorize.net Journal->True!'))
        payment_type = self.type in ('out_invoice', 'in_refund') and 'inbound' or 'outbound'
        payment_methods = payment_type == 'inbound' and Journal.inbound_payment_method_ids or Journal.outbound_payment_method_ids
        payment_method_id = payment_methods and payment_methods[0] or False
        context = {}
        no_discount = self._context.get('card_transaction', False)
        context.update({'from_authorize': 'no_discount'})
        payment = self.env['account.payment'].with_context(context).create({
            'invoice_ids': [(6, 0, self.ids)],
            'amount': self._context.get('payment_amount', False) or self.residual,
            'payment_date': fields.Date.context_today(self),
            'communication': self.type in ('in_invoice', 'in_refund') and self.reference or self.number,
            'partner_id': self.partner_id.commercial_partner_id and self.partner_id.commercial_partner_id.id,
            'partner_type': self.type in ('out_invoice', 'out_refund') and 'customer' or 'supplier',
            'journal_id': Journal and Journal.id,
            'payment_type': payment_type,
            'payment_method_id': payment_method_id and payment_method_id.id,
            })
        return payment

    @api.multi
    def write(self, vals):
        if vals.get('payment_id', False):
            for row in self:
                row.partner_id and row.partner_id.write({'payment_id': vals.get('payment_id', False)})
        return super(AccountInvoice, self).write(vals)

    @api.model
    def create(self, vals):
        res = super(AccountInvoice, self).create(vals)
        if vals.get('payment_id', False):
            self.partner_id and self.partner_id.write({'payment_id': vals.get('payment_id', False)})
        return res









