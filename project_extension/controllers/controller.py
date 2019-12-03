# -*- coding: utf-8 -*-

import werkzeug.utils
from collections import OrderedDict
from operator import itemgetter

from odoo import fields, http, _
from odoo.http import request
from odoo.exceptions import AccessError, MissingError
from odoo.osv import expression
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager
from odoo.addons.portal.controllers.mail import _message_post_helper
from odoo.addons.portal.controllers.mail import PortalChatter
from odoo.tools import consteq
from odoo.tools import groupby as groupbyelem
from werkzeug.exceptions import NotFound, Forbidden

from odoo.osv.expression import OR



def _has_token_access(res_model, res_id, token=''):
    record = request.env[res_model].browse(res_id).sudo()
    token_field = request.env[res_model]._mail_post_token_field
    return (token and record and consteq(record[token_field], token))


class PortalChatter(PortalChatter):

    @http.route('/mail/chatter_fetch', type='json', auth='public', website=True)
    def portal_message_fetch(self, res_model, res_id, domain=False, limit=10, offset=0, **kw):
        if not domain:
            domain = []
        field_domain = request.env[res_model]._fields['website_message_ids'].domain
        if callable(field_domain):
            field_domain = field_domain(request.env[res_model])
        domain = expression.AND([domain, field_domain, [('res_id', '=', res_id)]])
        Message = request.env['mail.message']
        if kw.get('token'):
            access_as_sudo = _has_token_access(res_model, res_id, token=kw.get('token'))
            if not access_as_sudo:
                raise Forbidden()
            if not request.env['res.users'].has_group('base.group_user'):
                domain = expression.AND(
                    [['&', ('subtype_id', '!=', False), ('subtype_id.internal', '=', False)], domain])
            if request.env['res.users'].has_group('base.group_portal'):
                domain = expression.AND(
                    [domain, field_domain, [('read_by_customer', '=', True)]])
            Message = request.env['mail.message'].sudo()
        return {
            'messages': Message.search(domain, limit=limit, offset=offset).portal_message_format(),
            'message_count': Message.search_count(domain)
        }


class ProjectController(http.Controller):

    @http.route(['/proposal/version', '/proposal/version/<int:res_id>'], type='http', auth='user', website=True)
    def project_proposal_page(self, res_id, access_token=None, **kwargs):
        try:
            proposal_sudo = request.env['proposal.version'].sudo().browse(res_id)
        except (AccessError, MissingError):
            return {'error': _('Invalid Proposal')}
        values = {
            'proposal_version': proposal_sudo,
            'bootstrap_formatting': True,
            'user_id': request.env.user,
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
        if kwargs.get('accept_message'):
            message = "'<b>%s</b>' Accepted with message <br/> '%s'." % (
                proposal_sudo.name, kwargs.get('accept_message'))
        else:
            message = "'<b>%s</b>' Accepted." % (proposal_sudo.name)
        _message_post_helper(
            res_model='proposal.version',
            res_id=proposal_sudo.id,
            message=message,
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
            _message_post_helper(message=message, res_id=res_id, res_model='proposal.version',
                                 **{'token': access_token} if access_token else {})
        else:
            query_string = "&message=cant_reject"
        return request.redirect(proposal_sudo.get_portal_url(query_string=query_string))

    @http.route(['/project/proposal', '/project/proposal/<int:res_id>'], type='http', auth='public', website=True)
    def project_proposal_customer_page(self, res_id, access_token, **kwargs):
        if access_token:
            try:
                _has_token_access(res_model='proposal.version', res_id=res_id, token=access_token)
                proposal = self._document_check_access(model_name='proposal.version', document_id=res_id,
                                                       access_token=access_token)
            except (AccessError, MissingError):
                raise Forbidden()
            values = {
                'proposal': proposal,
                'bootstrap_formatting': True,
                'user_id': request.env.user,
                'partner_id': proposal.partner_id.id,
                'token': access_token,
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
        if kwargs.get('accept_message'):
            message = "<b>%s</b> Accepted By Customer <b>%s</b> with message <br/> '%s'" % (
                proposal.name, project.partner_id.name, kwargs.get('accept_message'))
        else:
            message = "<b>%s</b> Accepted By Customer <b>%s</b>" % (proposal.name, project.partner_id.name)
        project.message_post(body=message)
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
        message = "<b>%s</b> Rejected By Customer <b>%s</b> with message <br/> '%s'" % (
            proposal.name, project.partner_id.name, post.get('decline_message'))
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


class CustomerPortal(CustomerPortal):

    def _prepare_portal_layout_values(self):
        values = super(CustomerPortal, self)._prepare_portal_layout_values()
        values['proposal_count'] =request.env['proposal.version'].search_count([])
        return values

    def _proposal_get_page_view_values(self, proposal, access_token, **kwargs):
        values = {
            'page_name': 'proposals',
            'bootstrap_formatting': True,
            'report_type':'html',
            'proposal': proposal,
        }
        return self._get_page_view_values(proposal, access_token, values, 'my_proposal_history', False, **kwargs)

    @http.route(['/my/proposals','/my/proposal/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_proposals(self, page=1,date_begin=None, date_end=None, sortby=None, filterby=None, groupby='project',search=None, search_in='content', **kw):
        values = self._prepare_portal_layout_values()
        Proposal = request.env['proposal.version']
        searchbar_sortings = {
            'date': {'label': _('Newest'), 'order': 'create_date desc'},
            'name': {'label': _('Name'), 'order': 'name'},
        }
        searchbar_groupby = {
            'none': {'input': 'none', 'label': _('None')},
            'project': {'input': 'project', 'label': _('Project')},
        }
        searchbar_filters = {
            'all': {'label': _('All'), 'domain': []},
        }
        projects = request.env['project.project'].search([])
        for project in projects:
            searchbar_filters.update({
                str(project.id): {'label': project.name, 'domain': [('project_id', '=', project.id)]}
            })

        project_groups = request.env['proposal.version'].read_group([('project_id', 'not in', projects.ids)],
                                                                    ['project_id'], ['project_id'])
        for group in project_groups:
            proj_id = group['project_id'][0] if group['project_id'] else False
            proj_name = group['project_id'][1] if group['project_id'] else _('Others')
            searchbar_filters.update({
                str(proj_id): {'label': proj_name, 'domain': [('project_id', '=', proj_id)]}
            })

        if not sortby:
            sortby = 'date'
        order = searchbar_sortings[sortby]['order']
        if not filterby:
            filterby = 'all'
        domain = searchbar_filters[filterby]['domain']
        archive_groups = self._get_archive_groups('proposal.version', domain)
        if date_begin and date_end:
            domain += [('create_date', '>', date_begin), ('create_date', '<=', date_end)]

        proposal_count = Proposal.search_count(domain)

        pager = portal_pager(
            url="/my/proposals",
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby, 'filterby': filterby,'search_in': search_in, 'search': search},
            total=proposal_count,
            page=page,
            step=self._items_per_page
        )
        if groupby == 'project':
            order = "project_id, %s" % order
        proposals = request.env['proposal.version'].search(domain, order=order, limit=self._items_per_page,
                                                           offset=(page - 1) * self._items_per_page)
        request.session['my_proposal_history'] = proposals.ids[:100]

        if groupby == 'project':
            grouped_proposals = [request.env['proposal.version'].concat(*g) for k, g in
                                 groupbyelem(proposals, itemgetter('project_id'))]
        else:
            grouped_proposals = [proposals]
        values.update({
            'date': date_begin,
            'date_end': date_end,
            'page_name': 'proposals',
            'archive_groups': archive_groups,
            'grouped_proposals':grouped_proposals,
            'default_url': '/my/proposals',
            'pager': pager,
            'searchbar_sortings': searchbar_sortings,
            'searchbar_groupby': searchbar_groupby,
            'searchbar_filters': OrderedDict(sorted(searchbar_filters.items())),
            'sortby': sortby,
            'groupby': groupby,
            'filterby': filterby
        })
        return request.render('project_extension.portal_my_proposals',values)

    @http.route(['/my/proposal/<int:proposal_id>'], type='http', auth="user", website=True)
    def portal_my_proposal(self, proposal_id=None, access_token=None, **kw):
        try:
            project_sudo = self._document_check_access('proposal.version', proposal_id, access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        values = self._proposal_get_page_view_values(project_sudo, access_token, **kw)
        return request.render("project_extension.portal_my_proposal", values)

