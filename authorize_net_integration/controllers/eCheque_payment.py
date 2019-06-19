# -*- coding: utf-8 -*-

from odoo import http
from odoo.http import request
import werkzeug.utils


class PaymentPageCheque(http.Controller):

    @http.route(['/web/eCheque_payment'], methods=['GET', 'POST'], type='http', auth="public")
    def cheque_payment(self, **form):
        """
            submit the cheque payment form

        """

        account_name = form.get('account_name', False)
        routing_number = form.get('routing_number', False)
        account_number = form.get('account_number', False)
        bank_name = form.get('bank_name', False)
        eCheque_type = 'WEB'
        account_type = 'savings'
        amount = form.get('total', False)
        invoice = form.get('name', False)
        invoice_id = form.get('invoice_number', False)
        inv_count = form.get('inv_count', 0)
        credit_count = form.get('credit_count', 0)
        invoice_list = []
        for inv in range(int(inv_count)):
            invoice = form.get('invoice_box_' + str(inv))
            if invoice:
                invoice_list.append(int(invoice))
        if credit_count:
            for inv in range(int(credit_count)):
                invoice = form.get('credit_box_' + str(inv))
                if invoice:
                    invoice_list.append(int(invoice))
        for inv in invoice_list:
            invoice_sudo = request.env['account.invoice'].sudo().browse(int(inv))
            invoice_sudo.write({'due_amount_authorize': invoice_sudo.residual})
        auth_record = request.env['payment.token.invoice'].sudo().search(
            [('invoice_id', '=', invoice_id and int(invoice_id))], limit=1)
        company_name = auth_record.invoice_id.user_id.company_id.name
        # call from multi select invoice payment view
        if invoice_list and auth_record and auth_record.state != 'submitted':
            amount = form.get('amount', False)
            transaction_id, error = request.env['account.invoice'].sudo().aim_transaction_invoice(
                invoice_list=invoice_list, amount=round(float(amount), 2), invoice=invoice_id,
                account_name=account_name, routing_number=routing_number, \
                account_number=account_number, bank_name=bank_name, \
                eCheque_type=eCheque_type, account_type=account_type)
            if transaction_id:
                auth_record.write({'state': 'submitted'})
                invoices = []
                for inv in invoice_list:
                    invoices.append(request.env['account.invoice'].sudo().browse(inv))
                return request.render("authorize_net_integration.InvoiceResultViewSuccess",
                                      {'invoice_ids': invoices, 'type': form.get('selected_p_method', False),'amount': amount})
            elif error:
                auth_record.write({'state': 'error'})
                return werkzeug.utils.redirect(
                    '/web/payment/invoice?token=%s&error=%s' % (auth_record.token, True))
        elif auth_record and auth_record.invoice_id.state == 'paid':
            return request.render("authorize_net_integration.PaymentResultView", {'status': 'already', 'company_name': company_name})
        else:
            auth_record.state = 'expired'
            return request.render("authorize_net_integration.PaymentResultView", {'status': auth_record.state, 'company_name': company_name})














