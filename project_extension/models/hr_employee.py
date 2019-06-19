# -*- coding:utf-8 -*-
from odoo import models, fields, api, _

class HrEmployee(models.Model):
    _inherit = 'hr.employee'
    
    employee_rate = fields.Monetary(string='Employee Work Rate', help="The rate @ which the company charges the customer for 1 hour of work time")
