# -*- coding: utf-8 -*- 
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class ProjectMilestone(models.Model):
    _name = 'project.milestone'
    _inherit = 'mail.thread'
    _description = 'Project Milestones'
    
    name = fields.Char(string='Name')
    start_date = fields.Date(string='Start Date')
    end_date = fields.Date(string='End Date')
    invoice_type = fields.Selection([('fixed', 'Fixed'), ('percent', 'Percent')])
    invoice_percent = fields.Integer(string="Invoice Percent")
    amount = fields.Float(string='Amount')
    project_id = fields.Many2one('project.project', string='Project')
    invoice_ids = fields.One2many('account.invoice', 'milestone_id', string='Invoice')
    invoiced = fields.Boolean(copy=False)
    invoice_count = fields.Integer(string='Invoice Count', compute='_compute_milestone_invoice')
    invoice_number = fields.Char(compute='_compute_invoice_number')
    active = fields.Boolean(string='Active', copy=False, default=True)
    task_ids = fields.One2many('project.task', 'milestone_id', string='Tasks')
    task_count = fields.Integer(string='Task Count', compute='_compute_task_count')
    
    @api.multi
    def _compute_milestone_invoice(self):
        for milestone in self:
            milestone.invoice_count = self.env['account.invoice'].search_count([('project_id', '=', milestone.project_id.id), ('milestone_id', '=', milestone.id), ('type', '=', 'out_invoice')])
    
    @api.multi
    def _compute_invoice_number(self):
        for milestone in self:
            milestone_invoice = self.env['account.invoice'].search([('project_id', '=', milestone.project_id.id), ('milestone_id', '=', milestone.id), ('type', '=', 'out_invoice')], limit=1)
            if len(milestone_invoice) == 1:
                milestone.invoice_number = milestone_invoice.number
            else:
                milestone.invoice_number = False
            
    @api.multi
    def _compute_task_count(self):
        for milestone in self:
            milestone.task_count = self.env['project.task'].search_count([('project_id', '=', milestone.project_id.id), ('milestone_id', '=', milestone.id)])        
    
    @api.model
    @api.onchange('invoice_percent')
    def _compute_amount(self):
        for milestone in self:
            milestone.update({'amount': (milestone.project_id.project_cost * milestone.invoice_percent) / 100})
    
    @api.multi
    def action_view_invoice(self):
        invoices = self.mapped('invoice_ids')
        action = self.env.ref('account.action_invoice_tree1').read()[0]
        if len(invoices) > 1:
            action['domain'] = [('id', 'in', invoices.ids)]
        elif len(invoices) == 1:
            action['views'] = [(self.env.ref('account.invoice_form').id, 'form')]
            action['res_id'] = invoices.ids[0]
        else:
            action = {'type': 'ir.actions.act_window_close'}
        return action
    
    @api.multi
    def action_view_tasks(self):
        action = self.env.ref('project.act_project_project_2_project_task_all').read()[0]
        action['domain'] = [('project_id', '=', self.project_id.id), ('milestone_id', '=', self.id)]
        action['context'] = {'default_project_id': self.project_id.id, 'default_milestone_id': self.id}
        return action
    
    @api.multi
    def create_milestone_invoice(self, cron_mode='off'):
        """
            Method called by both cron and button. Creates invoice for milestone.
                @param cron_mode: Identify where the method is called from. If called from button, context is passed.
                return: invoice created for milestone.
        """
        for milestone in self:
            if not milestone.invoiced:
                invoice = self.env['account.invoice'].create({
                    'partner_id': milestone.project_id.partner_id.id,
                    'date_invoice': milestone.start_date,
                    'type': 'out_invoice',
                    'project_id': milestone.project_id.id,
                    'user_id':milestone.project_id.user_id.id,
                    'milestone_id': milestone.id,
                    'origin': milestone.name,
                    'move_name': milestone.project_id.get_next_project_sequence_number(),
                    'invoice_line_ids': milestone.project_id._prepare_extra_invoice_lines(milestone.project_id, milestone)
                    })
                milestone.update({'invoiced': True})
                if cron_mode != 'on' and cron_mode != 'off':    #assert cron is off, context passed as parameter, so copy it.
                    context = dict(cron_mode)
                    cron_mode = 'off'
                if cron_mode == 'off':
                    if context.get('model') == 'project.milestone':
                        customer_invoice_form_id = self.env.ref('account.invoice_form').id
                        return {'type': 'ir.actions.act_window',
                                'res_model': 'account.invoice',
                                'views': [[customer_invoice_form_id, 'form']],
                                'res_id': invoice.id,
                                'target': 'current',
                               }
                elif cron_mode == 'on':
                    return invoice
    
    @api.model
    def invoice_project_milestones(self):
        """
            Called from cron to invoice milestones that have start date as of today.
                return: True
        """
        today_uninvoiced_rec = self.search([('start_date', '=', fields.Date.today()), ('invoiced', '=', False), ('active', '=', True), ('project_id.state', '=', 'proposal_accepted')])
        for rec in today_uninvoiced_rec:
            invoice = rec.create_milestone_invoice(cron_mode='on')
            project_id = rec.project_id
            project_id.send_invoice_alerts(invoice_id=invoice, invoice_alert_ids=project_id.invoice_alert_ids)
        return True
        

        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
