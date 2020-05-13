# -*- coding:utf-8 -*-
from odoo import models, fields, api, _

class ProjectExtraInvoiceLine(models.Model):
    _name = 'project.extra.invoice.line'
    _description = 'Extra invoiceable lines for project'

    sequence = fields.Integer('Sequence', default=10)
    product_id = fields.Many2one('product.product', string="Product")
    description = fields.Text(string="Description", required=True)
    project_id = fields.Many2one('project.project', string="Project")
    account_id = fields.Many2one('account.account', string="Account", required=True)
    quantity = fields.Integer(string='Quantity', default=1)
    amount = fields.Float(string="Amount", required=True, default=0.00)
    project_id = fields.Many2one('project.project', string="Project")

    @api.onchange('product_id')
    def _onchange_product_id(self):

        product_desc = self.product_id.description_sale if (
                    self.product_id and self.product_id.description_sale) else (self.product_id.description or self.product_id.name)
        journal = self.env['account.journal'].search([('type', '=', 'sale')], limit=1)
        product_account_id = self.project_id.product_id.property_account_income_id.id
        product_category_account_id = self.project_id.product_id.categ_id.property_account_income_categ_id.id
        journal_account_id = journal.default_credit_account_id.id
        lst_price = self.product_id.lst_price
        if product_account_id:
            account_id = product_account_id
        elif product_category_account_id:
            account_id = product_category_account_id
        else:
            account_id = journal_account_id 
      
        return {'value':{
                        'description': product_desc, 
                        'account_id': account_id,
                        'amount': lst_price
                        }
                    
                    }