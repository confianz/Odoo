# -*- coding:utf-8 -*-

import re

from odoo import models, fields, api,tools, _


class HelpdeskTickets(models.Model):
    _inherit = 'helpdesk.ticket'
    @api.model
    def _get_reference1_list(self):
        installed_modules = self.env['ir.module.module']._installed()
        result = [(module,module.replace('_',' ').capitalize()) for module in \
                  ['product','project','account','sale_subscription','sale_management'] if \
                  module in installed_modules]
        return result

    @api.model
    def _get_reference2_list(self):
        installed_modules = self.env['ir.module.module']._installed()
        result = []
        if 'account' in installed_modules:
            result.append(('invoice_line', "Invoice Line"))
        if 'sale_subscription' in installed_modules:
            result.append(('sale_subscription_line', 'Sale Subscription Line'))
        if 'sale_management' in installed_modules:
            result.append(('order_line', 'Order Line'))
        return result

    priority = fields.Selection(selection_add = [('4', 'Extreme' )])
    reported_time = fields.Datetime(string = 'Reported Time')
    fix = fields.Text()
    reason = fields.Text()
    issue_reference_1 = fields.Selection(string="Reference 1", selection=_get_reference1_list)
    issue_ref1_product_id = fields.Many2one('product.product', string='Reference Product')
    issue_ref1_sale_subscription = fields.Many2one('sale.subscription', string='Reference Sale Subscription')
    issue_ref1_sale_order = fields.Many2one('sale.order', string='Reference Sale Order')
    issue_ref1_invoice = fields.Many2one('account.invoice', string='Reference Invoice')
    issue_ref1_project = fields.Many2one('project.project', string='Reference Project')
    issue_reference_2 = fields.Selection(string="Reference 2", selection=_get_reference2_list)
    issue_ref2_order_line = fields.Many2one('sale.order.line', string='Reference Order Line')
    issue_ref2_sale_subscription_line = fields.Many2one('sale.subscription.line', string='Reference Sale Scubscription Line')
    issue_ref2_invoice_line = fields.Many2one('account.invoice.line', string='Reference Invoice Line')
    stage_active = fields.Boolean(related="stage_id.is_close")
    date_of_incident = fields.Datetime(string = 'Date of Incident')
    reported_by = fields.Many2one('res.partner', string = 'Reported By')
    contact_ids = fields.Many2many('res.partner', string = 'Contacts')
    action_taken_id = fields.Many2one('ticket.action.taken', string = 'Action Taken')
    technician_id = fields.Many2one('res.partner', string = 'Technician')
    reported_by_phone = fields.Char(related='reported_by.phone', string = 'Contact Phone')
    manager_id = fields.Many2one('res.partner', string = 'Manager')
    internal_follow_up = fields.Text(string = 'Internal Follow Up')
    external_follow_up = fields.Text(string = 'External follow up')
    close_date = fields.Datetime(string="Close date", compute="_compute_close_date", store=True)

    @api.onchange('issue_reference_1','issue_reference_2','issue_ref1_sale_order','issue_ref1_sale_subscription','issue_ref1_invoice')
    def _onchange_date_clear(self):
        if self.issue_reference_1 in ['product', 'project'] :
            self.issue_ref1_product_id = self.issue_ref1_project = None
            self.issue_reference_2 = None
        elif self.issue_reference_1 == 'sale_subscription':
            self.issue_ref1_product_id = self.issue_ref1_project = None
            self.issue_reference_2 = 'sale_subscription_line'
            self.issue_ref1_sale_order = self.issue_ref1_invoice = None
            self.issue_ref2_invoice_line = self.issue_ref2_order_line =None
        elif self.issue_reference_1 == 'sale_management':
            self.issue_ref1_product_id = self.issue_ref1_project = None
            self.issue_reference_2 = 'order_line'
            self.issue_ref1_sale_subscription = self.issue_ref1_invoice = None
            self.issue_ref2_invoice_line = self.issue_ref2_sale_subscription_line  = None
        elif self.issue_reference_1 == 'account':
            self.issue_ref1_product_id = self.issue_ref1_project = None
            self.issue_reference_2 = 'invoice_line'
            self.issue_ref1_sale_order = self.issue_ref1_sale_subscription = None
            self.issue_ref2_order_line = self.issue_ref2_sale_subscription_line = None
        if not self.issue_reference_2:
            self.issue_ref1_sale_order = self.issue_ref2_order_line = None
            self.issue_ref1_sale_subscription = self.issue_ref2_sale_subscription_line = None
            self.issue_ref1_invoice = self.issue_ref2_invoice_line = None
        if self.issue_reference_2:
            self.issue_ref2_order_line = self.issue_ref2_sale_subscription_line = self.issue_ref2_invoice_line = None

    @api.multi
    def ticket_get_restored(self):
        self.ensure_one()
        initial_stage = self.env['helpdesk.stage'].search([('team_ids', 'in', [self.team_id.id])],order="sequence asc", limit = 1)
        for ticket in self:
            ticket.write({'stage_active': False, 'stage_id': initial_stage.id, 'kanban_state':'normal'})

    @api.depends('stage_id.is_close')
    def _compute_close_date(self):
        for rec in self:
            if rec.stage_id.is_close:
                rec.close_date = fields.Datetime.now()

    @api.model
    def create(self, vals):
        ticket = super(HelpdeskTickets, self).create(vals)
        if ticket.manager_id:
            ticket.message_subscribe(partner_ids=ticket.manager_id.ids)
        return ticket

    @api.multi
    def write(self, vals):
        if vals.get('manager_id'):
            self.message_subscribe([vals['manager_id']])
        res = super(HelpdeskTickets, self).write(vals)
        return res

    @api.model
    def message_new(self, msg, custom_values=None):
        body = tools.html2plaintext(msg.get('body'))
        bre = re.match(r"(.*)^-- *$", body, re.MULTILINE | re.DOTALL | re.UNICODE)
        desc = bre.group(1) if bre else None
        parent_customer = self.env['res.partner'].browse([msg.get('author_id')]).commercial_partner_id
        email_split = tools.email_split(msg.get('email_from'))
        values = dict(custom_values or {},
                      reported_time = msg.get('date'),
                      reported_by = msg.get('author_id'),
                      description = desc or body)
        create_context = dict(self.env.context or {})
        ticket = super(HelpdeskTickets, self.with_context(create_context)).message_new(msg, custom_values=values)
        partner_ids = [x for x in ticket._find_partner_from_emails(tools.email_split(msg.get('cc') or '')) if x]
        ticket_contacts = [i for i in partner_ids if i in parent_customer.child_ids.ids]
        ticket.write({'partner_id': parent_customer.id,
                      'partner_name':msg.get('email_from').split('<')[0],
                      'partner_email':email_split[0] if email_split else parent_customer.email,
                      'contact_ids':[(6,0, ticket_contacts)]})
        if partner_ids:
            ticket.message_subscribe(partner_ids)
        return ticket

    @api.model
    def get_stage_ids(self):
        result = self.env['helpdesk.stage'].search([('team_ids','in',self.team_id.ids)])
        return result