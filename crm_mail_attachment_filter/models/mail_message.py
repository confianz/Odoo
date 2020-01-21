# -*- encoding: utf-8 -*-

from odoo import api, fields, models


class MailMessage(models.Model):
    _inherit = "mail.message"

    @api.model
    def create(self, vals):
        message = super(MailMessage, self).create(vals)
        if message.message_type == 'email' and message.model == 'crm.lead' and message.res_id:
            attachments = message.attachment_ids.filtered(
                lambda rec: 'image/' in rec.mimetype and rec.res_model == 'crm.lead' and rec.res_id == message.res_id)
            attachments.write({'active': False})

        return message


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:l
