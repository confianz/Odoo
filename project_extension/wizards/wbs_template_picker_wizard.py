# -*- coding: utf-8 -*-

from odoo import models, fields, api, _

class WbsTemplatePickerWizard(models.TransientModel):
    _name = 'wbs.template.picker.wizard'
    _description = 'Wbs Template Picker Wizard'

    wbs_template_id = fields.Many2one('wbs.project.template', string='Wbs Template')
    project_id = fields.Many2one('project.project', string="Project")

    @api.multi
    def add_to_project(self):
        for rec in self:
            rec.project_id.wbs_line_ids.unlink()
            rec.project_id.wbs_version_count = 0
            rec.project_id.write({'wbs_line_ids':[(0,0,{'sequence':wbs_rec.sequence,
                                                        'task_name':wbs_rec.task_name,
                                                        'description':wbs_rec.description,
                                                        'hour':wbs_rec.hour}) for wbs_rec in rec.wbs_template_id.wbs_ids]})
