# -*- coding: utf-8 -*-

from odoo import models, fields, api

class ProjectTask(models.Model):
    
    _inherit = 'project.task'
    
    milestone_id = fields.Many2one('project.milestone', string='Milestone')
    project_type = fields.Selection([('milestone', 'Milestone'), ('fte', 'FTE'), ('time_sheet', 'Timesheet')], related="project_id.project_type", string='Type')
