# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

from dateutil.relativedelta import relativedelta

class ProjectInvoiceWizard(models.TransientModel):
    _name = 'project.invoice.wizard'
    _description = 'Project Invoice Wizard'
    
    project_id = fields.Many2one('project.project', string='Project',required=True)
    project_invoice_line_ids = fields.One2many('project.invoice.line', 'invoice_wizard_id', string='Invoice Lines')
    partner_id  = fields.Many2one('res.partner', string='Customer', required=True)
    amount_total = fields.Monetary(string='Total', currency_field='currency_id', compute='_compute_amount')
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.user.company_id.currency_id)
    invoice_type = fields.Selection([('actual_invoice','Task Based Invoice'), ('early_invoice','Early Invoice')], string="Invoice Type")

    @api.one
    @api.depends('project_invoice_line_ids.price')
    def _compute_amount(self):
        self.amount_total = sum(line.price for line in self.project_invoice_line_ids)
    
    @api.model
    def default_get(self, fields):
        res = super(ProjectInvoiceWizard, self).default_get(fields)
        if self.env.context.get('active_model', '') == 'project.project':
            Line_OB =self.env['project.invoice.line']
            for project in self.env['project.project'].browse(self._context.get('active_ids', 0)):
                inv_line = []
                inv_line.append(Line_OB.create({
                                                 'product_id': project.product_id.id,
                                                 'description': project.product_id.description_sale or project.product_id.name,
                                                 'price': project.product_id.lst_price,
                                                }).id)
                if project.extra_invoice_line_ids:
                    for line in project.extra_invoice_line_ids:
                        inv_line.append(Line_OB.create({
                                                 'product_id': line.product_id.id,
                                                 'description': line.description,
                                                 'price': line.amount,
                                                }).id)

                res.update({
                            'project_invoice_line_ids': inv_line,
                            })
        
        return res
    
    @api.multi
    def create_invoice(self):
        for record in self:
            if record.invoice_type == 'early_invoice' and record.project_id.project_type not in ['fte']:
                raise ValidationError(_('Early Invoice Creation Only For FTE Projects.'))
            journal = self.env['account.journal'].search([('type', '=', 'sale')], limit=1)
            product_account_id = record.project_id.product_id.property_account_income_id.id
            product_category_account_id = record.project_id.product_id.categ_id.property_account_income_categ_id.id
            journal_account_id = journal.default_credit_account_id.id
            if product_account_id:
                account_id = product_account_id
            elif product_category_account_id:
                account_id = product_category_account_id
            else:
                account_id = journal_account_id
            if not account_id:
                raise UserError(_("Account not set"))
            invoice = self.env['account.invoice'].create({
                                                'partner_id': record.partner_id.id,
                                                'date_invoice': fields.Date.today(),
                                                'type': 'out_invoice',
                                                'project_id': record.project_id.id,
                                                'origin': record.project_id.name,
                                                'move_name': record.project_id.get_next_project_sequence_number(),
                                                'invoice_line_ids': [(0, 0, {
                                                                    'product_id': line.product_id.id,
                                                                    'name': line.description,
                                                                    'quantity': line.qty,
                                                                    'account_id': account_id,
                                                                    'price_unit': line.price,
                                                                    }) for line in record.project_invoice_line_ids]
                                                })
            if record.invoice_type == 'early_invoice':
                record.project_id.early_invoice = True
                record.project_id.last_billed_date = fields.Date.today()
                record.project_id.calculate_next_billing_date()
            customer_invoice_form_id = self.env.ref('account.invoice_form').id
            return {'type': 'ir.actions.act_window',
                    'res_model': 'account.invoice',
                    'views': [[customer_invoice_form_id, 'form']],
                    'res_id': invoice.id,
                    'target': 'current',
                   }


ProjectInvoiceWizard()


class ProjectInvoiceLine(models.TransientModel):
    _name = 'project.invoice.line'
    _description = 'Project Invoice Line'
    
    product_id = fields.Many2one('product.product', string='Products')
    description = fields.Text(string='Description', required=True)
    price = fields.Float(string='Price')
    qty = fields.Integer(string='Quantity', default=1)
    invoice_wizard_id = fields.Many2one('project.invoice.wizard', string='Invoice Wizard')
    
    @api.model
    @api.onchange('product_id', 'qty')
    def onchange_product(self):
        self.description = self.product_id.description_sale if self.product_id.description_sale else self.product_id.name
        self.price = self.qty*self.product_id.lst_price
        
ProjectInvoiceLine()
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
