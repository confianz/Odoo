# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
{
    'name': 'Authorize.Net Integration',
    'version': '1.1',
    'category': 'Accounting & Finance',
    'summary': "Accounting",
    'description': """
Authorize.Net Payment Gateway Integration.
==========================================
Authorize.Net Payment Gateway Integration module for making payments through authorize.net gateway
       """,
    'author': 'Confianz Global',
    'website': 'https://confianzit.com',
    'images': [],
    'data': [
            "wizard/make_payment_view.xml",
            "security/authorize_security.xml",
            "security/ir.model.access.csv",
            "views/index.xml",
            "views/payment_invoice.xml",
            "views/api_view.xml",
            "views/invoice_success.xml",
            "views/account_invoice_view.xml",
            "views/account_journal_view.xml",
            "views/result_page_payment.xml",
            "views/partner_view.xml",
            "data/mail_template.xml",
            "views/account_payment_view.xml",
#           "views/customer_payment_view.xml",
#           "views/payment_succesful_page.xml",
#           "views/payment_term_view.xml",
#           "data/mail_template_acknowledge.xml",
             ],

    'depends': ['account','sales_team',],
    'installable': True,
    'auto_install': False,
    'application': False,
}



# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
