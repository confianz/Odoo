# -*- encoding: utf-8 -*-

from odoo import api, fields, models


class MarketingActivity(models.Model):
    _inherit = 'marketing.activity'

    def execute_on_traces(self, traces):
        limit = int(self.env['ir.config_parameter'].sudo().get_param('mass_mail.trace_limit', '50'))
        traces = traces[:limit]
        return super(MarketingActivity, self).execute_on_traces(traces)


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
