# -*- coding: utf-8 -*-
from odoo import models, fields, api

class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'
    
    timesheet_invoice_id = fields.Many2one('account.invoice', string="Invoice", readonly=True, copy=False, help="Invoice created from the timesheet")
    timesheet_invoice_type = fields.Selection([
        ('billable_time', 'Billable Time'),
        ('non_billable', 'Non Billable'),
        ], string="Billable Type", readonly=True)
    charge_amount = fields.Float(compute='_compute_charge_amount', store=True, help="Timesheet amount to charge the customer")
    billable = fields.Boolean(string="Billable")
    
    @api.multi
    @api.depends('employee_id.employee_rate','unit_amount')
    def _compute_charge_amount(self):
        for rec in self:
            rec.charge_amount = rec.employee_id.employee_rate * rec.unit_amount
    
    @api.model
    def create(self, vals):
        res = super(AccountAnalyticLine, self).create(vals)
        if vals.get('billable') in [True, False]:
            if vals.get('billable') == True:
                res.update({'timesheet_invoice_type':'billable_time'})
            else: 
                res.update({'timesheet_invoice_type':'non_billable'})
        return res
        
    @api.multi
    def write(self, vals):
        if vals.get('billable') in [True, False]:
            if vals.get('billable') == True:
                vals.update({'timesheet_invoice_type':'billable_time'})
            else:
                vals.update({'timesheet_invoice_type':'non_billable'})
        return super(AccountAnalyticLine, self).write(vals)
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
