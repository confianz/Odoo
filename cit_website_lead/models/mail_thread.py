# -*- encoding: utf-8 -*-

from odoo import api, fields, models


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    @api.model
    def message_route(self, message, message_dict, model=None, thread_id=None, custom_values=None):
        if 'lead_id' in message_dict.get('body', ''):
            return []
        else:
            return super(MailThread, self).message_route(message, message_dict, model, thread_id, custom_values)


MailThread()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
