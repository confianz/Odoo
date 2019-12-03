# -*- coding: utf-8 -*-

from odoo import models, fields, api, _

class MailComposer(models.TransientModel):
    
    _inherit = 'mail.compose.message'
    
    @api.multi
    def action_send_mail(self):
        if self.template_id == self.env.ref('project_extension.email_template_proj_proposal_customer'):
            # update state of project when proposal is send to customer
            self.env[self._context.get('active_model', 'project.project')].browse(self._context.get('active_id')).write({'state': 'send_to_customer',})
        return super(MailComposer, self).action_send_mail()
