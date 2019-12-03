# -*- coding:utf-8 -*-
from odoo import models, fields, api, _

class WbsProjectTemplate(models.Model):
    _name = 'wbs.project.template'
    _description = 'Wbs Project Wbs Template'

    name =  fields.Char(string = 'Template Name', required=True)
    wbs_ids = fields.One2many('wbs.project','wbs_template_id', string = "WBS Lines")

class WbsProject(models.Model):
    _name = 'wbs.project'
    _description = 'Wbs Project Wbs Information'
    _rec_name = 'task_name'
    _order = 'sequence, id'

    task_name = fields.Char(string="Task Name",required=True)
    sequence = fields.Integer('Sequence', default=10)
    hour = fields.Float(string="Hour", default=0.0)
    wbs_template_id = fields.Many2one('wbs.project.template', string='Wbs Template', ondelete="cascade")
    description = fields.Text(string="Description", required=True)
    project_id = fields.Many2one('project.project', string="Project")