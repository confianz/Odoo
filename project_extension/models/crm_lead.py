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
        self.ensure_one()
        vals = self.create_project_vals()
        new_project = self.env['project.project'].create(vals)
        stage = self.env.ref('project_extension.development_stage')
        self.write({
            'project_id': new_project.id,
            'stage_id': stage and stage.id or self.stage_id.id,
        })
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'project.project',
            'views': [[False, 'form']],
            'target': 'current',
            'res_id': new_project.id,
        }

    @api.multi
    def action_view_project(self):
        self.ensure_one()
        action = self.env.ref('project.open_view_project_all').read()[0]
        action.update({
            'views': [(self.env.ref('project.edit_project').id, 'form')],
            'res_id': self.project_id.id,
            'target': 'current',
        })
        return action
