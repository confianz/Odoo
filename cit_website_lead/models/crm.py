# -*- encoding: utf-8 -*-

from odoo import api, fields, models


class CRMLead(models.Model):
    _inherit = "crm.lead"

    service_type = fields.Selection([
        ('web', 'Web Application'),
        ('mobile', 'Mobile Application'),
        ('erp', 'ERP Application'),
        ('others', 'Others'),
        ], string="Service Type", default="erp")
    comments = fields.Text(string="Comments")
    budget = fields.Char(string="Project Budget")
    page_name = fields.Char(string="Page Name")
    page_slug = fields.Char(string="Page Slug")


CRMLead()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
