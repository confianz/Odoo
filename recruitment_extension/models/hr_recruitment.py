# -*- encoding: utf-8 -*-

import json

from odoo import api, fields, models


class HrJob(models.Model):
    _inherit = "hr.job"

    country_id = fields.Many2one('res.country', string="Country")
    location = fields.Char(compute="_compute_location", readonly=True, store=False)
    loc_code = fields.Char(compute="_compute_location", readonly=True, store=False)
    job_description = fields.Text(string="Job Description")

    @api.multi
    def _compute_location(self):
        for job in self:
            if job.country_id:
                job.location = job.country_id and job.country_id.name or ''
                job.loc_code = job.country_id and job.country_id.code or ''

    @api.model
    def get_open_positions(self):
        """
        This function is used for XMLRPC call.

        :rtype  : `json str`
        :returns: open job positions
        """
        domain = [('state', '=', 'recruit')]
        fields = ['id', 'name', 'description', 'location', 'loc_code', 'job_description']

        jobs = self.sudo().search_read(domain, fields, order='id desc')

        return json.dumps(jobs)


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
