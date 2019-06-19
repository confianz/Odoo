# -*- coding:utf-8 -*-
from odoo import models,fields,api,_

class CrmLead(models.Model):
    
    _inherit = 'crm.lead'
    
    project_id = fields.Many2one('project.project', string='Project')
    
    @api.multi
    def create_project_vals(self):
        for opportunity in self:
            vals = {
                    'name': opportunity.name,
                    'lead_id': opportunity.id,
                    'partner_id': opportunity.partner_id.id,
                    'user_id': opportunity.user_id.id,
                    'privacy_visibility': 'followers',
                    'state': 'draft',
                   }
            return vals
    
    @api.multi
    def create_project_from_lead(self):
        for opportunity in self:
            vals = opportunity.create_project_vals()
            new_project = self.env['project.project'].create(vals)
            opportunity.write({'project_id': new_project.id})
            return {
            'type': 'ir.actions.act_window',
            'res_model': 'project.project',
            'views': [[False, 'form']],
            'target': 'current',
            'res_id': new_project.id,
                   }
                   
                   
