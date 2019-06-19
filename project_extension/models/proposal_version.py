# -*- coding:utf-8 -*-
from odoo import models, fields, api, _

class ProposalVersion(models.Model):
    
    _name = 'proposal.version'
    _inherit = ['mail.thread', 'portal.mixin']
    _description = 'Project Proposal Versions'
    
    name = fields.Char(string='Name')
    project_id = fields.Many2one('project.project', string='Project', required=True)
    state = fields.Selection([('draft', 'Draft'),
                              ('waiting_approval', 'Waiting Approval'),
                              ('single_user_approved', 'Single User Approved'),
                              ('accepted', 'Accepted'),
                              ('rejected', 'Rejected')], track_visibility='onchange')
    partner_id = fields.Many2one('res.partner', string='Customer')
    attachment_ids = fields.Many2many('ir.attachment', string='Proposal Documents')
    proposed_amount = fields.Float(string='Proposed Amount')
    approval_1_user_id = fields.Many2one('res.users', related='project_id.approval_1_user_id')
    approval_2_user_id = fields.Many2one('res.users', related='project_id.approval_2_user_id')
    user_1_approved = fields.Boolean(copy=False)
    user_2_approved = fields.Boolean(copy=False)
    customer_done = fields.Boolean(copy=False, help='To check if the proposal is already accepted or rejected by customer')
    user_approved_time = fields.Datetime(help="Used to filter chatter messages for customer in portal")
    
    @api.multi
    def check_for_user_approval(self, user_id):
        for proposal in self:
            if proposal.project_id.state != 'cancel':
                if proposal.approval_1_user_id == user_id:
                    proposal.action_user_1_approved()
                elif proposal.approval_2_user_id == user_id:
                    proposal.action_user_2_approved()
            else:
                proposal.message_post(body="Project Cancelled! Cannot Accept")
    
    @api.multi
    def action_confirm_proposal(self):
        for proposal in self:
            proposal.update({'state': 'accepted', 'user_approved_time': fields.Datetime.now()})
            proposal.project_id.action_approved()
            proposal.project_id.write({'user_approved_proposal_id': proposal.id})
    
    @api.multi
    def action_reject_proposal(self):
        for proposal in self:
            proposal.update({'state': 'rejected'})
            proposal.project_id.action_waiting_proposal()
    
    @api.multi
    def action_user_1_approved(self):
        for proposal in self:
            proposal.update({'user_1_approved': True, 'state': 'single_user_approved'})
            proposal.project_id.update({'user_1_approved': True})
            proposal.action_check_if_both_user_approved()
    
    @api.multi
    def action_user_2_approved(self):
        for proposal in self:
            proposal.update({'user_2_approved': True, 'state': 'single_user_approved'})
            proposal.project_id.update({'user_2_approved': True})
            proposal.action_check_if_both_user_approved()
    
    @api.multi
    def action_check_if_both_user_approved(self):
        for proposal in self:
            if proposal.user_1_approved and proposal.user_2_approved:
                proposal.action_confirm_proposal()
            if proposal.approval_1_user_id == proposal.approval_2_user_id:
                proposal.update({'user_1_approved': True, 'user_2_approved': True})
                proposal.project_id.update({'user_1_approved': True, 'user_2_approved': True})
                proposal.action_confirm_proposal()
    
    @api.multi
    def check_if_already_done_by_user(self, user_id=None):
        """
            To check if proposal if already accepted or rejected by the user.
            Used to compute visibility of approve and reject buttons in portal.
        """
        for proposal in self:
            if proposal.state == 'rejected' or proposal.approval_1_user_id == user_id and proposal.user_1_approved:
                return True
            elif proposal.state == 'rejected' or proposal.approval_2_user_id == user_id and proposal.user_2_approved:
                return True
            else:
                return False

    @api.multi
    def check_if_already_done_by_customer(self):
        """
            To check if proposal if already accepted or rejected by the customer.
            Used to compute visibility of accept and reject buttons in portal.
        """
        for proposal in self:
            if proposal.customer_done == True:
                return True
            else:
                return False

    @api.model
    def get_attachment_url(self, download=False):
        """
            Return the url to fetch an attachment to print or download.
                @param download: if the url is requested by download button.
                return: The url to the document
        """
        self.ensure_one()
        url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        attachment = self.attachment_ids
        if len(attachment) == 1:
            mimetype = attachment.mimetype.split('/')[-1]
            if download:
                url += "/web/content/ir.attachment/%s/datas/proposal_document.%s?download=True" % (str(attachment.id),  str(mimetype))
            else:
                url += "/web/content/ir.attachment/%s/datas/proposal_document.%s" % (str(attachment.id), str(mimetype))
            return url
        
    @api.model
    def check_attachment_mimetype(self):
        """
            Calculates if the attachment is a pdf or an image
            return: 'pdf' if a pdf document else 'image'
        """
        self.ensure_one()
        attachment = self.attachment_ids
        if len(attachment) == 1:
            if attachment.mimetype.split('/')[-1] == 'pdf':
                return 'pdf'
            elif attachment.mimetype.split('/')[-1] in ['gif','jpe','jpeg','jpg','png']:
                return 'image'
        return False    
    
    @api.multi
    def get_attachment_datas(self):
        self.ensure_one()
        attachment = self.attachment_ids
        if len(attachment) == 1:
            return attachment.datas
        
        
        
        
        
        
        
        
        
        
        
        
