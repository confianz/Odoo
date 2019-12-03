# -*- coding: utf-8 -*-
from odoo import models, fields, api

class AccountInvoice(models.Model):
    _inherit = 'account.invoice'
    
    project_id = fields.Many2one('project.project', string='Project')
    milestone_id = fields.Many2one('project.milestone', string='Milestone')
    
    @api.model
    def get_invoice_alert_ids(self):
        """
            Called from the email template to get the invoice_alert_ids.
                return: ids of invoice alert partners
        """
        ids = str([alerts.id for alerts in self.project_id.invoice_alert_ids.mapped(lambda partner: partner.partner_id)]).replace('[', '').replace(']', '')
        return ids
