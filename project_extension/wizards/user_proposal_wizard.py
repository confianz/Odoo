# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError

class UserProposalWizard(models.TransientModel):
    _name = 'user.proposal.wizard'
    _description = 'User Proposal Wizard'
    
    name = fields.Char(string='Name')
    proposal_doc = fields.Binary(string='Proposal Doc')
    file_name = fields.Char()
    project_id = fields.Many2one('project.project', string='Project', required=True)
    proposed_amount = fields.Float(string='Proposed Amount', required=True)
    approval_1_user_id = fields.Many2one('res.users', related='project_id.approval_1_user_id')
    approval_2_user_id = fields.Many2one('res.users', related='project_id.approval_2_user_id')
    proposal_version_id = fields.Many2one('proposal.version', string='Proposal Version')
    
    @api.multi
    @api.onchange('file_name')
    def _onchange_file_name(self):
        project_no = self.env['proposal.version'].search_count([('project_id', '=', self.project_id.id)])
        if self.file_name:
            file_name = self.file_name.split('.')
            del file_name[-1]
            self.name = str(' '.join(file_name)) + str(' version ') + str(project_no + 1)
    
    @api.model
    def default_get(self, vals):
        res = super(UserProposalWizard, self).default_get(vals)
        if self._context.get('active_model') == 'project.project':
            res.update({'proposed_amount': self.env['project.project'].browse(self.env.context.get('active_id')).project_cost})
        return res
    
    
    @api.multi
    def proposal_wizard_save(self):
        for proposal in self:
            new_proposal = self.env['proposal.version'].create({
                                            'name': proposal.name,
                                            'partner_id': proposal.project_id.partner_id.id,
                                            'project_id': proposal.env.context.get('default_project_id', proposal.project_id.id),
                                            'state': 'waiting_approval',
                                            'proposed_amount': proposal.proposed_amount,
                                            })
            new_proposal.write({'attachment_ids': [(0,0,
                                    {'name': proposal.file_name,
                                     'datas_fname': proposal.file_name,
                                     'res_name': new_proposal.name,
                                     'res_model': new_proposal._name,
                                     'res_id': new_proposal.id,
                                     'datas': proposal.proposal_doc,
                                     'public': True,
                                    }
                                    )]
                                })
            self.write({'proposal_version_id': new_proposal.id})
            proposal.project_id.update({'project_cost': self.proposed_amount,})
            proposal.action_send_proposal_to_user()
            proposal.project_id.action_waiting_approval()
     
            
    @api.multi
    def action_send_proposal_to_user(self):
        self.ensure_one()
        template = self.env.ref('project_extension.email_template_proj_proposal_user')
        template.send_mail(self.project_id.id, force_send=True)
        return True
    
    @api.constrains('proposed_amount', 'proposal_doc')
    def check_amount_not_null(self):
        for rec in self:
            if rec.proposed_amount == 0:
                raise UserError(_("Proposed Amount is empty"))
            elif rec.proposal_doc == None:
                raise UserError(_("Proposal Document is empty"))
    
