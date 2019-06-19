# -*- coding: utf-8 -*-

from odoo import models, fields, api,_
from dateutil.relativedelta import relativedelta
from odoo.exceptions import Warning, UserError


class AccountPayment(models.Model):
    _inherit = "account.payment"

    transaction_id = fields.Char(string='Authorize.net Transaction ID', copy=False)
    transaction_partner_id = fields.Many2one('res.partner', string='Authorized Customer', copy=False)
    payment_id = fields.Char(string='Authorize.net Payment ID', copy=False)

    @api.model
    def default_get(self, fields):

        '''updates the super method prepared dict of values with additional three fields
            triggered by pressing register payment button in credit invoice form'''

        res = super(AccountPayment, self).default_get(fields)
        invoice = self.env['account.invoice'].browse(self._context.get('active_id'))
        if invoice.transaction_id:
            res.update({'transaction_partner_id': invoice.partner_id.id, 'transaction_id': invoice.transaction_id, 'payment_id': invoice.payment_id or None})
        return res

    @api.multi
    def post(self):
        """
        change the payment status when the invoice is paid
        :return:
        """
        res = super(AccountPayment, self).post()
        for record in self:
            for inv in record.invoice_ids:
                if inv.type == 'out_refund' and self._context.get('refund_mode', False):
                    if inv.payment_id:

                        t_id = self.env['authorizenet.api'].refund_payment(inv.partner_id.profile_id,
                                                                               inv.payment_id,
                                                                               inv.transaction_id, record.amount, inv.number)

                        if not t_id:
                            if inv.invoice_origin_id and record.amount < inv.invoice_origin_id.amount_total:
                                raise UserError(_("You can refund partially strictly after the invoice amount is settled through authorize.net. Try again after 24 hours"))
                            response, msg, code = self.env['authorizenet.api'].void_payment(inv.partner_id.profile_id,inv.payment_id,inv.transaction_id)
                            if not response:
                                raise UserError('Authorize.Net Warning-%s\n%s' % (msg, code))
                            inv.write({'is_refund': True})
                            if inv.invoice_origin_id:
                                inv.invoice_origin_id.write({'is_refund': True})
                        else:
                            inv.write({'is_refund': True, 'transaction_id_refund': t_id})
                            if inv.invoice_origin_id:
                                inv.invoice_origin_id.write({'is_refund': True, 'transaction_id_refund': t_id})
                    elif inv.transaction_id:

                        t_id = self.env['authorizenet.api'].refund_payment_aim(inv.transaction_id, record.amount, inv.number)

                        if not t_id:
                            if inv.invoice_origin_id and record.amount < inv.invoice_origin_id.amount_total:
                                raise UserError(_("You can refund partially strictly after the invoice amount is settled through auth.net. Try after 24 hours"))
                            response, msg, code = self.env['authorizenet.api'].void_transaction_aim(inv.transaction_id)
                            if not response:
                                raise UserError('Authorize.Net Warning-%s\n%s' % (msg, code))
                            inv.write({'is_refund': True})
                            if inv.invoice_origin_id:
                                inv.invoice_origin_id.write({'is_refund': True})
                        else:
                            inv.write({'is_refund': True, 'transaction_id_refund': t_id})
                            if inv.invoice_origin_id:
                                inv.invoice_origin_id.write({'is_refund': True, 'transaction_id_refund': t_id})

        return res


class AccountRegisterPayment(models.TransientModel):
    _inherit = "account.register.payments"

    def create_payments(self):
        context = dict(self._context)
        if all(invoice.type == 'out_refund' for invoice in self.invoice_ids):
            for invoice in self.invoice_ids:
                invoice.write({'is_refund': True})
                invoice.invoice_origin_id and invoice.invoice_origin_id.write({'is_refund': True})
        else:
            context.update({'refund_mode': True})
        res = super(AccountRegisterPayment, self.with_context(context)).create_payments()
        return res

AccountRegisterPayment()





# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
