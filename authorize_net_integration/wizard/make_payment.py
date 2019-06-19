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

from odoo import models, fields, api
from odoo.tools.translate import _
from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.exceptions import UserError


class make_payment(models.TransientModel):
    _name = "make.payment"
    _description = "Make Payment Class"
   
    @api.model
    def _get_payment_ids(self):
        if not self.env.context.get('active_id'):
            return []
        partner_brw = self.env['res.partner'].browse(self.env.context.get('default_partner_id', 0))
        profile_id = partner_brw and partner_brw._get_profile_id() or False
        if not profile_id: 
            return []
        res = self.env['authorizenet.api']._get_profile(profile_id) 
        return self.env['authorizenet.api']._get_payment_ids(res)

    @api.model 
    def _get_last_payment_id(self):
        active_obj = self.env.context.get('active_model', False)
        if not active_obj:
            return False
        partner_brw = self.env['res.partner'].browse(self.env.context.get('default_partner_id', 0))
        return partner_brw.profile_id and partner_brw.payment_id or False

    @api.model
    def _get_partner_id(self):
        partner_brw = self.env['res.partner'].browse(self.env.context.get('default_partner_id', 0))
        return partner_brw.id       

    @api.model
    def _payment_count(self):
        partner_brw = self.env['res.partner'].browse(self.env.context.get('default_partner_id', 0))        
        profile_id = partner_brw and partner_brw._get_profile_id() or False
        if not profile_id: 
            return 0
        res = self.env['authorizenet.api']._get_profile(profile_id) 
        return len(self.env['authorizenet.api']._get_payment_ids(res))         

    card_no = fields.Char('Credit Card Number', size=16)
    card_code = fields.Char('CVV', size=4)
    exp_month = fields.Selection([('01','January'),('02','February'),('03','March'),('04','April'),('05','May'),('06','June'),('07','July'),('08','August'),('09','September'),('10','October'),('11','November'),('12','December')],'Card Expiration Month')
    exp_year = fields.Selection([(num, str(num)) for num in range(datetime.now().year,(datetime.now().year)+11)], 'Card Expiration Year')
    partner_id = fields.Many2one('res.partner',"Partner Invoice Address", default =_get_partner_id)
    payment_id = fields.Selection(_get_payment_ids, 'Your last Card')
    is_correction = fields.Boolean('Is Correction')
    payment_nos = fields.Integer('Payment Numbers', default=_payment_count)

    @api.one
    def authorize_transaction(self):
        """
        create authorizenet payment and  authorize transaction

        """
        authorize_obj = self.env['authorizenet.api']
        active_brw = self.env[self.env.context.get('active_model')].browse(self.env.context.get('active_id', []))

        invoice = ''
        if self.env.context.get('active_model', '') == 'account.invoice':
            invoice = active_brw.origin
            InvoiceRec = active_brw
        profile_id = self.partner_id._get_profile_id()
        if self.is_correction:
            try:
                authorize_obj.void_payment(profile_id, active_brw.payment_id, active_brw.transaction_id)
            except:
                pass
        expiry_date = '%s-%s' % (self.exp_year, self.exp_month)
        if not profile_id:
            profile_id = authorize_obj.create_authorizenet_profile(self.partner_id)
            self.commit_cursor(self.partner_id and self.partner_id, profile_id)
        payment_id = self.payment_id
        if not payment_id:
            payment_id = authorize_obj.create_payment_profile(profile_id, self.partner_id, self.card_no, self.card_code,
                                                              expiry_date)

        journal_rec = self.env['account.journal'].sudo().search([('is_authorizenet','=', True)], limit=1)
        payment = InvoiceRec.register_card_payments()
        transaction_id = authorize_obj.authorize_payment(profile_id, payment_id, InvoiceRec.residual, InvoiceRec.number)
        payment.write(
            {'transaction_id': transaction_id, 'payment_id': payment_id})
        self.env['authorizenet.api'].capture_payment(profile_id, payment_id, transaction_id, InvoiceRec.residual)
        InvoiceRec.write(
            {'transaction_id': transaction_id, 'payment_id': payment_id,
             'transaction_date': datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT)})

        payment.post()
        return self.write({'card_no': '', 'card_code': ''})

    def commit_cursor(self, partner_id, profile_id=False, context=None):
        """
        except raise would hinder commiting data
        (writing profile id to partner)
        couldnt get new api to create and commit
        data using new cursor
        so executing the old fashioned way
        """
        if partner_id and profile_id:
            partner_id.write({'profile_id': profile_id})
            self.env.cr.commit()
        return True

make_payment()




# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:  
