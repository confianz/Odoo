# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
import werkzeug.utils
import re


class PaymentPageWeb(http.Controller):
    
    def check_string(self, inp_string):
        op_string = ''
        if inp_string :
            op_string = inp_string.replace('&', 'and') # replaces '&' with 'and'
            op_string = re.sub('<.+?>', ' ', op_string) # removes any characters in between '<' and '>'
            op_string = re.sub('@.+', ' ', op_string) # removes any character that comes after '@'
            op_string = re.sub('[^-_A-Za-z0-9]', ' ', op_string)  # repaced all the special character except ,-_
        return op_string
    
            
    @http.route(['/web/verification/invoice'], methods=['GET', 'POST'], type='http', auth="public")
    def customer_verification_invoice(self, **form):
        """
        details of card after submission
        authorization and capture payments
        """
        invoice_id = form['invoice_number']
        auth_record = request.env['payment.token.invoice'].sudo().search([('invoice_id', '=', int(invoice_id))], limit=1)
        company_name = auth_record.invoice_id.user_id.company_id.name
        if auth_record.state != 'submitted':
            invoice_list = []
            amount = form['invoice_amount']
            card = form['card']
            cvv = form['cvv']
            expiry = form['month'] + form['year']
            inv_count = form.get('inv_count', 0)
            credit_count = form.get('credit_count', 0)
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
            invoice_sudo = request.env['account.invoice'].sudo().browse(int(invoice_id))
            invoice_sudo.write({'due_amount_authorize': invoice_sudo and invoice_sudo.residual})
            transaction_id, error = request.env['account.invoice'].sudo().aim_transaction_invoice(invoice_list, amount, card, cvv, expiry, invoice_id)
            if transaction_id:
                auth_record.write({'state': 'submitted'})
                invoices = []
                for inv in invoice_list:
                    invoices.append(request.env['account.invoice'].sudo().browse(inv))
                return request.render("authorize_net_integration.InvoiceResultViewSuccess", {'invoice_ids': invoices, 'type': form.get('selected_p_method', False), 'amount': amount})
            elif error:
                auth_record.write({'state': 'error'})
                return werkzeug.utils.redirect('/web/payment/invoice?token=%s&error=%s' % (auth_record.token, True))
        elif auth_record.invoice_id.state == 'paid':
            return request.render("authorize_net_integration.PaymentResultView", {'status': 'already', 'company_name': company_name})
        else:
            auth_record.state = 'expired'
            return request.render("authorize_net_integration.PaymentResultView", {'status': auth_record.state, 'company_name': company_name})


            
    @http.route(['/web/payment/invoice'], type='http', auth="public")
    def customer_confirmation_invoice(self, token, error=None):
        """
            redirect to the payment page
        """
        auth_record = request.env['payment.token.invoice'].sudo().search([('token', '=', token)])
        invoice_ids = request.env['account.invoice'].sudo().search([('id', '=', auth_record.invoice_id.id)])
        company_name = auth_record.invoice_id.user_id.company_id.name
        if auth_record:
            auth_record.state = 'draft'
            warning = False
            if error:
                warning = request.env['error.box'].sudo().search([('order', '=', auth_record.invoice_id.number)],
                                                                 order='id DESC', limit=1)
                warning = self.check_string(warning.error_message)
                warning = warning.split("-")
                if len(warning) > 1:
                    warning = warning and warning[1]
            if auth_record.invoice_id.state == 'paid':
                return request.render("authorize_net_integration.PaymentResultView", {'status': 'invoice-paid', 'company_name': company_name})
            elif auth_record.invoice_id.state != 'open':
                return request.render("authorize_net_integration.PaymentResultView", {'status': 'not_exist', 'company_name': company_name})
            invoice_ids = sorted(invoice_ids, key=lambda a: a.date_due)
            journal_rec = request.env['account.journal'].sudo().search([('is_authorizenet', '=', True)], limit=1)
            return request.render("authorize_net_integration.InvoicePaymentView", {'invoice_ids': invoice_ids, 'invoice_id': auth_record.invoice_id,  'warning': warning, 'auth_record': auth_record, 'company_name': company_name})
        else:
            return request.render("authorize_net_integration.PaymentResultView", {'status': 'not_exist', 'company_name': company_name})
            
            
            
            
            
            
            
            
            
