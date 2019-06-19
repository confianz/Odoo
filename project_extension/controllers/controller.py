# -*- coding: utf-8 -*-

from odoo import fields, http, _
from odoo.http import request
from odoo.exceptions import AccessError, MissingError
from odoo.addons.portal.controllers.mail import _message_post_helper
from odoo.tools import consteq
from werkzeug.exceptions import NotFound, Forbidden

def _has_token_access(res_model, res_id, token=''):
    record = request.env[res_model].browse(res_id).sudo()
    token_field = request.env[res_model]._mail_post_token_field
    return (token and record and consteq(record[token_field], token))

class ProjectController(http.Controller):
    
    @http.route(['/proposal/version', '/proposal/version/<int:res_id>'], type='http', auth='user', website=True)
    def project_proposal_page(self, res_id, access_token=None, **kwargs):
        try:
            proposal_sudo = request.env['proposal.version'].sudo().browse(res_id)
        except (AccessError, MissingError):
            return {'error': _('Invalid Proposal')}
        values = {
            'proposal_version': proposal_sudo,
#            'token': access_token,
            'bootstrap_formatting': True,
            'user_id': request.env.user,
#            'partner_id': proposal_sudo.partner_id.id,
            'report_type': 'html',
        }
        return request.render('project_extension.proposal_portal_user_template', values)
        
        
    @http.route(['/proposal/version/<int:res_id>/accept'], type='http', auth="user", website=True)
    def user_approve_proposal(self, res_id, access_token=None, **kwargs):
        try:
            proposal_sudo = request.env['proposal.version'].sudo().browse(res_id)
        except (AccessError, MissingError):
            return {'error': _('Invalid order')}
        user_id = request.env.user
        if  kwargs.get('accept_message'):
            message = "'<b>%s</b>' Accepted with message <br/> '%s'." % (proposal_sudo.name, kwargs.get('accept_message'))
        else:
            message = "'<b>%s</b>' Accepted."  % (proposal_sudo.name)
        _message_post_helper(
            res_model='proposal.version',
            res_id=proposal_sudo.id,
            message=message,
#            attachments=[('%s.pdf' % order_sudo.name, pdf)],
            **({'token': access_token} if access_token else {}))
        proposal_sudo.check_for_user_approval(user_id)
        return request.redirect(proposal_sudo.get_portal_url(query_string='&message=sign_ok'))
    
    
    @http.route(['/proposal/version/<int:res_id>/decline'], type='http', methods=['POST'], auth='user', website=True)
    def user_decline_proposal(self, res_id, access_token=None, **post):
        try:
            proposal_sudo = request.env['proposal.version'].sudo().browse(res_id)
        except (AccessError, MissingError):
            return request.redirect('/my')

        message = "<b>%s</b> Rejected with message <br/> '%s'" % (proposal_sudo.name, post.get('decline_message'))
        query_string = False
        if message:
            proposal_sudo.action_reject_proposal()
            _message_post_helper(message=message, res_id=res_id, res_model='proposal.version', **{'token': access_token} if access_token else {})
        else:
            query_string = "&message=cant_reject"
        return request.redirect(proposal_sudo.get_portal_url(query_string=query_string))
        
        
    @http.route(['/project/proposal', '/project/proposal/<int:res_id>'], type='http', auth='public', website=True)
    def project_proposal_customer_page(self, res_id, token, **kwargs):
        if token:
                try:
                    _has_token_access(res_model='proposal.version', res_id=res_id, token=token)
                    proposal = self._document_check_access(model_name='proposal.version', document_id=res_id, access_token=token)
                except (AccessError, MissingError):
                    raise Forbidden()
                values = {
                    'proposal_version': proposal,
                    'bootstrap_formatting': True,
                    'user_id': request.env.user,
                    'partner_id': proposal.partner_id.id,
                    'token': token,
                    'report_type': 'html',
                }
                return request.render('project_extension.proposal_portal_customer_template', values)
    
    
    @http.route(['/project/proposal/<int:res_id>/accept'], type='http', auth="public", website=True)
    def customer_proposal_accept(self, res_id, token=None, **kwargs):
        try:
            proposal = request.env['proposal.version'].sudo().browse(res_id)
            project = proposal.project_id
        except (AccessError, MissingError):
            return {'error': _('Invalid order')}
        user_id = request.env.user
        proposal.update({'customer_done': True})
        project.write({'state': 'proposal_accepted', 'customer_accepted_proposal_id': proposal.id, })
        if  kwargs.get('accept_message'):
            message = "<b>%s</b> Accepted By Customer <b>%s</b> with message <br/> '%s'" % (proposal.name, project.partner_id.name, kwargs.get('accept_message'))
        else:
            message = "<b>%s</b> Accepted By Customer <b>%s</b>" % (proposal.name, project.partner_id.name)
        project.message_post(body=message)
        proj_seq_id = project.create_new_project_invoice_sequence()
        return request.redirect(project.get_portal_url(query_string='&message=sign_ok'))
    
    
    @http.route(['/project/proposal/<int:res_id>/decline'], type='http', methods=['POST'], auth='public', website=True)
    def customer_decline_proposal(self, res_id, token=None, **post):
        try:
            proposal = request.env['proposal.version'].sudo().browse(res_id)
            project = proposal.project_id
        except (AccessError, MissingError):
            return request.redirect('/my')
        proposal.update({'customer_done': True})
        project.write({'state': 'customer_rejected'})
        message = "<b>%s</b> Rejected By Customer <b>%s</b> with message <br/> '%s'" % (proposal.name, project.partner_id.name, post.get('decline_message'))
        project.message_post(body=message)
        query_string = False
        return request.redirect(project.get_portal_url(query_string=query_string))
    
    
    @http.route(['/user/accepted/time'], type='json', auth="public", website=True)
    def get_get_user_approved_time(self, **kwargs):
        if 'res_id' in kwargs:
            return request.env['proposal.version'].sudo().browse(kwargs.get('res_id')).user_approved_time
    
    def _document_check_access(self, model_name, document_id, access_token=None):
        document = request.env[model_name].browse([document_id])
        document_sudo = document.sudo().exists()
        if not document_sudo:
            raise MissingError("This document does not exist.")
        try:
            document.check_access_rights('read')
            document.check_access_rule('read')
        except AccessError:
            if not access_token or not consteq(document_sudo.access_token, access_token):
                raise
        return document_sudo
        
        
        
        
        
        
        
