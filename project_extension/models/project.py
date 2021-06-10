# -*- coding:utf-8 -*-
from docutils.parsers.rst.directives import unchanged_required
from odoo import models, fields, api, _
from datetime import date, timedelta
import dateutil.relativedelta
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError

import json

class ProjectProject(models.Model):
    _inherit = 'project.project'

    date_end = fields.Date(string='End Date')

    invoice_alert_ids = fields.Many2many('res.users')
    product_id = fields.Many2one('product.product', string='Invoice Product')
    approval_1_user_id = fields.Many2one('res.users', string='Approval 1 User')
    approval_2_user_id = fields.Many2one('res.users', string='Approval 2 User')
    user_1_approved = fields.Boolean(string='User 1 Approved', copy=False)
    user_2_approved = fields.Boolean(string='User 2 Approved', copy=False)
    project_type = fields.Selection([
        ('milestone', 'Milestone'),
        ('fte', 'FTE'),
        ('hourly', 'Hourly'),
        ], default='milestone', string='Type')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('waiting_proposal', 'Waiting Proposal'),
        ('waiting_approval', 'Waiting Approval'),
        ('proposal_approved', 'User Approved'),
        ('send_to_customer', 'Send to Customer'),
        ('proposal_accepted', 'Accepted'),
        ('customer_rejected', 'Rejected'),
        ('closed', 'Closed'),
        ('cancel', 'Cancelled'),
    ], default='draft', track_visibility='onchange')
    lead_id = fields.Many2one('crm.lead', string='Lead/Opportunity')
    proposal_version_ids = fields.One2many('proposal.version', 'project_id', string='Proposal Version')
    proposal_count = fields.Integer(compute='_compute_proposal_count', string='Proposal Count')
    milestone_count = fields.Integer(compute='_compute_milestone_count', string='Milestone Count')
    invoice_count = fields.Integer(compute='_compute_invoice_count', string="Invoice Count")
    invoice_ids = fields.One2many('account.invoice', 'project_id', string='Invoices')
    milestone_ids = fields.One2many('project.milestone', 'project_id', string='Project Milestones')
    project_cost = fields.Float(string='Project Cost')
    user_approved_proposal_id = fields.Many2one('proposal.version', string='User Approved Proposal', copy=False)
    customer_accepted_proposal_id = fields.Many2one('proposal.version', string='Customer Accepted Proposal', copy=False)
    project_close_date = fields.Date(string='Project Close Date')
    weekday_bill = fields.Boolean(string="Bill on Weekday", default=False)
    bill_mode = fields.Selection([
        ('first_day', 'First Day'),
        ('last_day', 'Last Day'),
        ('specific_date', 'Specific Date'),
    ], string="Bill Mode")
    billing_frequency = fields.Selection([
        ('month', 'Month'),
        ('week', 'Week'),
        ('bi_week', 'Bi-Week'),
        ('yearly', 'Yearly'),
    ])
    last_billed_date = fields.Date(string='Last Bill Date')
    next_billing_date = fields.Date(string='Next Billing Date')
    invoiced_amount = fields.Float(string='Invoiced Amount', compute='_compute_invoiced_amount')
    project_sequence_id = fields.Many2one('ir.sequence', string='Project Sequence')
    project_code = fields.Char(string="ProjectCode", required='True', copy=False)
    wbs_line_ids = fields.One2many('wbs.project', 'project_id', string="Wbs Lines")
    wbs_version_count = fields.Integer(string="Version", default=0)
    early_invoice = fields.Boolean(string="Early Invoice", default= False)
    extra_invoice_line_ids = fields.One2many('project.extra.invoice.line', 'project_id', string="Extra Invoice Lines")
    custom_invoice_description = fields.Char('Custom Project Type')

    _sql_constraints = [
        ('project_code_uniq', 'UNIQUE(project_code)', 'You can not have two Project with the same Project Code !')
    ]

    @api.multi
    def _compute_invoiced_amount(self):
        for project in self:
            confirmed_invoices = project.invoice_ids.filtered(lambda inv: inv.state not in ['draft', 'cancel'])
            sum_amount = 0
            for inv in confirmed_invoices:
                sum_amount += inv.amount_total
            project.invoiced_amount = sum_amount

    @api.multi
    def _compute_proposal_count(self):
        for project in self:
            Proposal = self.env['proposal.version']
            project.proposal_count = Proposal.search_count([('project_id', '=', project.id)])


    @api.multi
    def _compute_milestone_count(self):
        for project in self:
            Milestone = self.env['project.milestone']
            project.milestone_count = Milestone.search_count([('project_id', '=', project.id)])

    @api.multi
    def _compute_invoice_count(self):
        for project in self:
            Invoice = self.env['account.invoice']
            project.invoice_count = Invoice.search_count(
                [('project_id', '=', project.id), ('type', '=', 'out_invoice')])

    @api.multi
    @api.onchange('bill_mode', 'billing_frequency', 'last_billed_date', 'weekday_bill')
    def _onchange_bill_mode(self):
        for project in self:
            # billing on week day doesn't make sense if billing is on specific date
            if project.bill_mode == 'specific_date':
                project.weekday_bill = False
            project.calculate_next_billing_date()

    @api.multi
    def action_waiting_proposal(self):
        for project in self:
            project.update({'state': 'waiting_proposal', 'user_1_approved': False, 'user_2_approved': False})

    @api.multi
    def action_waiting_approval(self):
        for project in self:
            project.update({'state': 'waiting_approval', })

    @api.multi
    def action_close_project(self):
        for project in self:
            project.update({'state': 'closed', 'project_close_date': fields.Date.today()})

    @api.multi
    def action_approved(self):
        for project in self:
            project.update({'state': 'proposal_approved', })

    @api.multi
    def action_set_to_cancel(self):
        for project in self:
            project.update({'state': 'cancel'})
            # Create project button visibility after cancel
            if project.lead_id.project_id:
                project.lead_id.project_id = False

    @api.multi
    def action_send_proposal_to_customer(self):
        self.ensure_one()
        ir_model_data = self.env['ir.model.data']
        try:
            template_id = \
                ir_model_data.get_object_reference('project_extension', 'email_template_proj_proposal_customer')[1]
        except ValueError:
            template_id = False
        try:
            compose_form_id = ir_model_data.get_object_reference('mail', 'email_compose_message_wizard_form')[1]
        except ValueError:
            compose_form_id = False
        ctx = {
            'default_model': 'project.project',
            'default_res_id': self.ids[0],
            'default_use_template': bool(template_id),
            'default_template_id': template_id,
            'default_composition_mode': 'comment',
            'default_attachment_ids': [(4, attachment.id) for attachment in
                                       self.user_approved_proposal_id.attachment_ids],
            #            'custom_layout': "mail.mail_notification_paynow",  ## Use custom_layout iff you want a link back to record in email
            'force_email': True
        }
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form_id, 'form')],
            'view_id': compose_form_id,
            'target': 'new',
            'context': ctx,
        }

    @api.multi
    def action_create_invoice(self):
        """
            create an invoice while project type is 'hourly'
        """
        for project in self:
            if project.project_type == 'hourly':
                journal = self.env['account.journal'].search([('type', '=', 'sale')], limit=1)
                product_account_id = project.product_id.property_account_income_id.id
                product_category_account_id = project.product_id.categ_id.property_account_income_categ_id.id
                journal_account_id = journal.default_credit_account_id.id
                if product_account_id:
                    account_id = product_account_id
                elif product_category_account_id:
                    account_id = product_category_account_id
                else:
                    account_id = journal_account_id
                if not account_id:
                    raise UserError(_("Account not set"))
                self.env['account.invoice'].create({
                                                    'partner_id': project.partner_id.id,
                                                    'date_invoice': fields.Date.today(),
                                                    'type': 'out_invoice',
                                                    'project_id': project.id,
                                                    'origin': project.name,
                                                    'move_name': project.get_next_project_sequence_number(),
                                                    'invoice_line_ids':project._prepare_extra_invoice_lines(project)
                                                    })
                return True
            else:
                ctx = {'default_project_id': project.id, 'default_partner_id': project.partner_id.id}
                return {
                'type': 'ir.actions.act_window',
                'res_model': 'project.invoice.wizard',
                'views': [(False, 'form')],
                'target': 'new',
                'context': ctx,
            }

    @api.multi
    def action_open_proposal(self):
        for project in self:
            proposal_action = self.env.ref('project_extension.proposal_version_action').read()[0]
            proposal_action['domain'] = [('project_id', '=', project.id)]
            return proposal_action

    @api.multi
    def action_open_milestone(self):
        for project in self:
            milestone_action = self.env.ref('project_extension.project_milestone_action').read()[0]
            milestone_action['domain'] = [('project_id', '=', project.id)]
            return milestone_action

    @api.multi
    def action_open_invoice(self):
        for project in self:
            action = self.env.ref('account.action_invoice_tree1').read()[0]
            action['domain'] = [('project_id', '=', project.id)]
            return action

    @api.model
    def get_user_project_proposal_url(self):
        """
        :return: project proposal url for user. Called from the email template.
        """
        web_root_url = self.env['ir.config_parameter'].get_param('web.base.url')
        proposal = self.env['proposal.version'].search([], order='id desc', limit=1).id
        VIEW_WEB_URL = '%s/proposal/version/%s' % (web_root_url, proposal)
        return VIEW_WEB_URL

    @api.model
    def get_customer_project_proposal_url(self):
        """
        :return: project proposal url for customer. Called from the email Template.
        """
        proposal = self.user_approved_proposal_id
        # use token provided by odoo via portal.mixin to gain access to attachments in database
        access_token = proposal.access_token if proposal.access_token else proposal._portal_ensure_token()
        web_root_url = self.env['ir.config_parameter'].get_param('web.base.url')
        customer = self.env['res.users'].search([('partner_id','=',proposal.partner_id.id)])
        if customer.has_group('base.group_portal'):
            WEB_URL =  '%s/my/proposal/%s?access_token=%s' % (web_root_url, proposal.id, access_token)
            return WEB_URL
        WEB_URL = '%s/project/proposal/%s?access_token=%s' % (web_root_url, proposal.id, access_token)
        return WEB_URL

    @api.multi
    def write(self, vals):
        res = super(ProjectProject, self).write(vals) if vals else True
        if vals.get('wbs_line_ids'):
            self.message_post_with_view('project_extension.wbs_post',
                                        values={'body': self.wbs_line_ids, 'version': self.wbs_version_count},
                                        subtype_id=self.env.ref('mail.mt_note').id)
            self.wbs_version_count += 1
        if vals.get('state') == 'proposal_accepted':
            for project in self:
                if not project.project_sequence_id:
                    project.create_new_project_invoice_sequence()
        return res

    def find_next_weekday(self, date):
        date += timedelta(days=1)
        while date.weekday() > 4:  # Mon-Fri are 0-4
            date += timedelta(days=1)
        return date

    def find_previous_weekday(self, date):
        date -= timedelta(days=1)
        while date.weekday() > 4:  # Mon-Fri are 0-4
            date -= timedelta(days=1)
        return date

    @api.multi
    def calculate_next_billing_date(self):
        """
            Calculates the next billing date of the project.
        """
        for project in self:
            last_billed_date = fields.Date.today() if project.last_billed_date == False else project.last_billed_date
            next_date_early = project.next_billing_date if project.early_invoice else False
            # for Monthly billing
            if project.billing_frequency == 'month':
                month_1 = relativedelta(months=1)
                next_month_first_day = next_date_early.replace(day=1) + month_1 if project.early_invoice else last_billed_date.replace(day=1) + month_1
                if project.bill_mode == 'first_day':
                    if project.weekday_bill and next_month_first_day.weekday() not in range(5):
                        project.next_billing_date = project.find_next_weekday(next_month_first_day)
                    else:
                        project.next_billing_date = next_month_first_day
                    project.early_invoice = False
                elif project.bill_mode == 'last_day':
                    # if billing is first time, we choose current month end, other wise next month end
                    if project.last_billed_date == False:
                        this_month_last_day = next_month_first_day - relativedelta(days=1)
                        if project.weekday_bill and this_month_last_day.weekday() not in range(5):
                            project.next_billing_date = project.find_previous_weekday(this_month_last_day)
                        else:
                            project.next_billing_date = this_month_last_day
                        project.early_invoice = False
                    else:
                        next_next_month_first_day = next_month_first_day + month_1
                        next_month_last_day = next_next_month_first_day - relativedelta(days=1)
                        if project.weekday_bill and next_month_last_day.weekday() not in range(5):
                            project.next_billing_date = project.find_previous_weekday(next_month_last_day)
                        else:
                            project.next_billing_date = next_month_last_day
                        project.early_invoice = False
                elif project.bill_mode == 'specific_date':
                    project.next_billing_date = next_date_early + month_1 if project.early_invoice else last_billed_date + month_1
                    project.early_invoice = False
            # For weekly billing
            elif project.billing_frequency == 'week':
                week_1 = relativedelta(weeks=1)
                sat = next_date_early + relativedelta(weekday=dateutil.relativedelta.SA(1)) if project.early_invoice else last_billed_date + relativedelta(weekday=dateutil.relativedelta.SA(1))  # find next saturday
                sun = sat + relativedelta(days=1)
                fri = project.find_previous_weekday(sat)
                mon = project.find_next_weekday(sat)
                if project.bill_mode == 'first_day':
                    if project.weekday_bill:
                        project.next_billing_date = mon
                    else:
                        project.next_billing_date = sun
                    project.early_invoice = False
                elif project.bill_mode == 'last_day':
                    if project.weekday_bill:
                        # if billing is first time, we choose current week end, other wise next week end
                        project.next_billing_date = fri if project.last_billed_date == False else fri + week_1
                    else:
                        # if billing is first time, we choose current week end, other wise next week end
                        project.next_billing_date = sat if project.last_billed_date == False else sat + week_1
                    project.early_invoice = False
                elif project.bill_mode == 'specific_date':
                    project.next_billing_date = next_date_early + week_1 if project.early_invoice else last_billed_date + week_1
                    project.early_invoice = False
            # For bi-week billing
            elif project.billing_frequency == 'bi_week':
                week_1 = relativedelta(weeks=1)
                week_2 = relativedelta(weeks=2)
                sat = next_date_early + relativedelta(weekday=dateutil.relativedelta.SA(2)) if project.early_invoice else last_billed_date + relativedelta(weekday=dateutil.relativedelta.SA(2))  # find next next Saturday
                sun = sat + relativedelta(days=1)
                fri = project.find_previous_weekday(sat)
                mon = project.find_next_weekday(sat)
                if project.bill_mode == 'first_day':
                    if project.weekday_bill:
                        project.next_billing_date = mon
                    else:
                        project.next_billing_date = sun
                    project.early_invoice = False
                elif project.bill_mode == 'last_day':
                    if project.weekday_bill:
                        # if billing is first time, we choose next week end, other wise next next week end
                        project.next_billing_date = fri if project.last_billed_date == False else fri + week_1
                    else:
                        # if billing is first time, we choose next week end, other wise next next week end
                        project.next_billing_date = sat if project.last_billed_date == False else sat + week_1
                    project.early_invoice = False
                elif project.bill_mode == 'specific_date':
                    project.next_billing_date = next_date_early + week_2 if project.early_invoice else last_billed_date + week_2
                    project.early_invoice = False
            elif project.billing_frequency == 'yearly':
                year_1 = relativedelta(years=1)
                next_year_first_day = next_date_early.replace(day=1,month=1) + year_1 if project.early_invoice else last_billed_date.replace(day=1,month=1) + year_1
                if project.bill_mode == 'first_day':
                    if project.weekday_bill and next_year_first_day.weekday() not in range(5):
                        project.next_billing_date = project.find_next_weekday(next_year_first_day)
                    else:
                        project.next_billing_date = next_year_first_day
                    project.early_invoice = False
                elif project.bill_mode == 'last_day':
                    # if billing is first time, we choose current month end, other wise next month end
                    if project.last_billed_date == False:
                        next_year_last_day = next_year_first_day - relativedelta(days=1)
                        if project.weekday_bill and next_year_last_day.weekday() not in range(5):
                            project.next_billing_date = project.find_previous_weekday(next_year_last_day)
                        else:
                            project.next_billing_date = next_year_last_day
                        project.early_invoice = False
                    else:
                        next_next_year_first_day = next_year_first_day + year_1
                        next_year_last_day = next_next_year_first_day - relativedelta(days=1)
                        if project.weekday_bill and next_year_last_day.weekday() not in range(5):
                            project.next_billing_date = project.find_previous_weekday(next_year_last_day)
                        else:
                            project.next_billing_date = next_year_last_day
                        project.early_invoice = False
                elif project.bill_mode == 'specific_date':
                    project.next_billing_date = next_date_early + year_1 if project.early_invoice else last_billed_date + year_1
                    project.early_invoice = False

    def get_default_sale_jrnl_acc(self):
        """
            return: Default sales Journal Credit Account
        """
        sale_journal = self.env['account.journal'].search([('type', '=', 'sale')], limit=1)
        journal_account_id = sale_journal.default_credit_account_id
        return journal_account_id

    @api.multi
    def send_alerts_and_calc_bill_date(self, invoice_id=False):
        """
            Sends invoice alerts for the partners and Calculates the next bill date for the project
            @param invoice_id: The invoice for which alerts are send.
        """
        for project in self:
            if invoice_id and len(invoice_id) == 1:
                project.send_invoice_alerts(invoice_id=invoice_id, invoice_alert_ids=project.invoice_alert_ids)
                project.last_billed_date = fields.Date.today()
                project.calculate_next_billing_date()

    @api.model
    def create_timesheet_invoice(self):
        """
            Create invoice for projects of type timesheet. Called by the cron.
        """
        projects = self.search([('project_type', '=', 'time_sheet'), ('active', '=', True),
                                ('next_billing_date', '=', fields.Date.today()), ('state', '=', 'proposal_accepted')])
        customer_ids = projects.mapped(lambda partner: partner.partner_id)
        for customer in customer_ids:
            for project in projects.filtered(lambda project: project.partner_id == customer):
                not_invoiced_timesheets = project.analytic_account_id.line_ids.filtered(lambda line: line.project_id.id == project.id and line.timesheet_invoice_id.id == False and line.billable == True)
                if len(not_invoiced_timesheets) != 0:
                    journal_account_id = project.get_default_sale_jrnl_acc().id
                    invoice_id = self.env['account.invoice'].create({
                        'partner_id': customer.id,
                        'project_id': project.id,
                        'user_id': project.user_id.id,
                        'type': 'out_invoice',
                        'date_invoice': fields.Date.today(),
                        'origin': project.name,
                        'move_name': project.get_next_project_sequence_number(),
                        'invoice_line_ids': project._prepare_extra_invoice_lines(project)
                        })
                    project.send_alerts_and_calc_bill_date(invoice_id=invoice_id)
                    for timesheet in not_invoiced_timesheets:
                        timesheet.write({'timesheet_invoice_id': invoice_id.id})
        return True

    @api.model
    def create_fte_invoice(self):
        """
            Create invoice for projects of type fte. Called by the cron.
        """
        projects = self.search(
            [('project_type', '=', 'fte'), ('active', '=', True), ('next_billing_date', '=', fields.Date.today()),
             ('state', '=', 'proposal_accepted')])
        customer_ids = projects.mapped(lambda partner: partner.partner_id)
        for customer in customer_ids:
            for project in projects.filtered(lambda project: project.partner_id == customer):
                journal_account_id = project.get_default_sale_jrnl_acc().id
                invoice_id = self.env['account.invoice'].create({
                    'partner_id': customer.id,
                    'project_id': project.id,
                    'user_id':project.user_id.id,
                    'type': 'out_invoice',
                    'date_invoice': fields.Date.today(),
                    'origin': project.name,
                    'move_name': project.get_next_project_sequence_number(),
                    'invoice_line_ids': project._prepare_extra_invoice_lines(project)
                    })
                project.send_alerts_and_calc_bill_date(invoice_id=invoice_id)
        return True

    @api.multi
    def compute_description(self, res_id=None):
        """
            Computes the description for the invoice lines, depending on the type and invoicing policy of project.
            Called by the invoicing methods of the correspoding project types.
                @param res_id: the invoice line for which the description is to be calculated.
                return: the description of invoice line.
        """
        for project in self:
            product_desc = project.product_id.description_sale if (
                    project.product_id and project.product_id.description_sale) else (project.product_id.description or project.product_id.name)
            year = fields.Date.today().year
            week = fields.Date.today().strftime("%W")
            month = fields.Date.today().strftime("%B")
            billing_frequency = project.billing_frequency
            if project.project_type == 'milestone':
                if res_id:
                    milestone_desc = str(res_id.project_id.name) + ' - ' + str(res_id.name)
                    res = '(' + str(month) + ' - ' + str(year) + ') ' + str(milestone_desc)
                else:
                    res = '(' + str(month) + ' - ' + str(year) + ') ' + str(product_desc)
                return res
            elif project.project_type == 'fte':
                if billing_frequency in ['week', 'bi_week']:
                    res = '(Week ' + str(week) + ' - ' + str(year) + ') ' + str(product_desc)
                else:
                    res = '(' + str(month) + ' - ' + str(year) + ') ' + str(product_desc)
                return res
            elif project.project_type == 'time_sheet':
                if res_id:
                    timesheet_desc = str(res_id.project_id.name) + ' - ' + str(res_id.name)
                    week = res_id.date.strftime("%W")
                    month = res_id.date.strftime("%B")
                    year = res_id.date.year
                    if billing_frequency in ['week', 'bi_week']:
                        res = '(Week ' + str(week) + ' - ' + str(year) + ') ' + str(timesheet_desc)
                    else:
                        res = '(' + str(month) + ' - ' + str(year) + ') ' + str(timesheet_desc)
                else:
                    if billing_frequency in ['week', 'bi_week']:
                        res = '(Week ' + str(week) + ' - ' + str(year) + ') ' + str(product_desc)
                    else:
                        res = '(' + str(month) + ' - ' + str(year) + ') ' + str(product_desc)
                return res

    def _prepare_extra_invoice_lines(self, project=None, milestone=None):
        extra_lines = []
        journal_account_id = project.get_default_sale_jrnl_acc().id
        journal = self.env['account.journal'].search([('type', '=', 'sale')], limit=1)
        product_account_id = milestone.project_id.product_id.property_account_income_id.id if milestone else project.product_id.property_account_income_id.id
        product_category_account_id = milestone.project_id.product_id.categ_id.property_account_income_categ_id.id if milestone else project.product_id.categ_id.property_account_income_categ_id.id
        journal_account_id = journal.default_credit_account_id.id
        if product_account_id:
            account_id = product_account_id
        elif product_category_account_id:
            account_id = product_category_account_id
        else:
            account_id = journal_account_id
        if not account_id:
            raise UserError(_("Account not set"))
        if project and project.project_type in ['fte', 'hourly']:
            extra_lines.append((0, 0, {
                        'product_id': project.product_id.id,
                        'name': project.compute_description() if project.project_type == 'fte' else project.product_id.description_sale or project.product_id.name,
                        'account_id': journal_account_id if project.project_type == 'fte' else account_id,
                        'quantity': 1,
                        'price_unit': project.project_cost,
                    }))
            if project.extra_invoice_line_ids:
                for line in project.extra_invoice_line_ids:
                    extra_lines.append((0, 0, {
                        'product_id': line.product_id.id,
                        'name': line.description,
                        'account_id': line.account_id.id,
                        'quantity': line.quantity,
                        'price_unit': line.amount,
                    }))
            return extra_lines
        elif project and project.project_type == 'time_sheet':
            not_invoiced_timesheets = project.analytic_account_id.line_ids.filtered(lambda line: line.project_id.id == project.id and line.timesheet_invoice_id.id == False and line.billable == True)
            for timesheet in not_invoiced_timesheets:
                extra_lines.append((0, 0, {
                            'name': project.compute_description(res_id=timesheet),
                            'account_id': journal_account_id,
                            'quantity': timesheet.unit_amount,
                            'price_unit': timesheet.employee_id.employee_rate * timesheet.unit_amount,
                        }))
            if project.extra_invoice_line_ids:
                for line in project.extra_invoice_line_ids:
                    extra_lines.append((0, 0, {
                        'product_id': line.product_id.id,
                        'name': line.description,
                        'account_id': line.account_id.id,
                        'quantity': line.quantity,
                        'price_unit': line.amount,
                    }))
            return extra_lines
        elif project.project_type == 'milestone' and milestone:
            extra_lines.append((0, 0, {
                        'product_id': project.product_id.id,
                        'name': project.compute_description(res_id=milestone),
                        'account_id': account_id,
                        'quantity': 1,
                        'price_unit': milestone.amount,
                    }))
            if project.extra_invoice_line_ids:
                for line in project.extra_invoice_line_ids:
                    extra_lines.append((0, 0, {
                        'product_id': line.product_id.id,
                        'name': line.description,
                        'account_id': line.account_id.id,
                        'quantity': line.quantity,
                        'price_unit': line.amount,
                    }))
            return extra_lines
        else:
            return extra_lines


    @api.model
    def send_invoice_alerts(self, invoice_id=False, invoice_alert_ids=False):
        """
            Send invoices to correspoding Users for validation.
                @param invoice_id: the invoice to be send to the user.
                @param invoice_alert_ids: invoice_alert_ids of project.
                return: True
        """
        template = self.env.ref('project_extension.email_template_edi_invoice_alerts')
        # ctx = dict(self._context)
        # ctx.update({
        # 	'active_ids': [invoice_id.id],
        # 	'default_model': 'account.invoice',
        # 	'default_res_id': invoice_id.id,
        # 	'default_use_template': bool(template),
        # 	'default_template_id': template and template.id or False,
        # 	'default_composition_mode': 'comment',
        # 	'mark_invoice_as_sent': True,
        # 	'custom_layout': "mail.mail_notification_paynow",
        # 	# used to decorate mail template, and create back link to record
        # 	'force_email': True,
        # })
        # # self.env['mail.compose.message'].with_context(ctx).create({'composition_mode': 'comment'}).send_mail()
        # #                    compose_form = self.env.ref('account.account_invoice_send_wizard_form', False)
        # #                    return {
        # #                        'name': _('Send Invoice'),
        # #                        'type': 'ir.actions.act_window',
        # #                        'view_type': 'form',
        # #                        'view_mode': 'form',
        # #                        'res_model': 'account.invoice.send',
        # #                        'views': [(compose_form.id, 'form')],
        # #                        'view_id': compose_form.id,
        # #                        'target': 'new',
        # #                        'context': ctx,
        # #                    }
        # #                    mail_notification_paynow = self.env.ref('mail.mail_notification_paynow')
        # #                    body_html = mail_notification_paynow.render(values=mail_notification_paynow.read()[0], engine='ir.qweb')
        # #                    template.with_context(ctx).send_mail(invoice_id.id, force_send=True)
        # generated_email = template.with_context(ctx).generate_email(invoice_id.id)
        # invoice_pdf = self.env['ir.attachment'].create(
        # 	{'name': generated_email.get('attachments')[0][0],
        # 	 'datas_fname': generated_email.get('attachments')[0][0],
        # 	 'res_model': 'mail.composition.message',
        # 	 'datas': generated_email.get('attachments')[0][1], })
        # # we create a wizard record, instead of template.send_mail()
        # # to create a back link to the record for which the mail is send
        # wizard_send = self.env['account.invoice.send'].with_context(ctx).create({
        # 	'template_id': template.id,
        # 	'composition_mode': 'comment',
        # 	'is_email': True,
        # 	'partner_ids': [(4, partner.partner_id.id) for partner in invoice_alert_ids],
        # 	'body': generated_email.get('body_html'),
        # 	'invoice_ids': [(4, invoice_id.id)],
        # 	'composer_id': self.env['mail.compose.message'].with_context(ctx).create(
        # 		{'composition_mode': 'comment'}).id,
        # 	'attachment_ids': [(4, invoice_pdf.id)],
        # })
        # wizard_send._send_email()

        # template.create_action()
        invoice_id.message_post_with_template(template.id,notif_layout="mail.mail_notification_paynow")
        return True

    @api.model
    def get_approve_users_ids(self):
        if self.approval_1_user_id.id == self.approval_2_user_id.id:
            return self.approval_1_user_id.partner_id.id
        else:
            ids = str([self.approval_1_user_id.partner_id.id,self.approval_2_user_id.partner_id.id]).replace('[', '').replace(']', '')
            return ids

    @api.model
    def invoice_projects_cron(self):
        """
            Directly called by the cron to invoice projects with billing date as of today.
        """
        self.env['project.milestone'].invoice_project_milestones()
        self.create_fte_invoice()
        # self.create_timesheet_invoice()
        self.env['mail.mail'].process_email_queue()
        return True

    @api.multi
    def action_view_timesheet_overview(self):
        for project in self:
            action = self.env.ref('project_extension.project_timesheet_action_client_timesheet_plan').read()[0]
            action['params'] = {
                'project_ids': project.ids,
            }
            action['context'] = {
                'active_id': project.id,
                'active_ids': project.ids,
                'search_default_display_name': project.name,
            }
            return action

    @api.multi
    def create_new_project_invoice_sequence(self):
        """
            Create a new invoice sequence for the project.
            Called when the customer accepts the proposal.
                return: newly created project invoice sequence
        """
        for project in self:
            project_sequence_id = self.env['ir.sequence'].create({
                'name': str(project.name) + " Invoice Sequence",
                #                                    'code': 'project.project',
                'prefix': project.project_code + str("/%(range_year)s/"),
                'number_next': 1,
                'number_increment': 1,
                'use_date_range': 1,
                'company_id': False,
                'padding': 3,
            })
            project.write({'project_sequence_id': project_sequence_id.id, })

    # @api.multi
    # def compute_project_seq_prefix(self):
    #     """
    #         Calculates a prefix for the newly created project invoice sequence
    #             return: newly created sequence prefix
    #     """
    #     for project in self:
    #         proj_name_list = project.name.split()
    #         if len(proj_name_list) > 1: # Projects name with more than 1 word
    #             if len(proj_name_list[0]) >= 2 and len(proj_name_list[1]) >= 2:
    #                 prefix = proj_name_list[0][0:2].upper() + proj_name_list[1][0:2].upper()
    #             elif len(proj_name_list[0]) >= 2 and len(proj_name_list[1]) == 1:
    #                 prefix = proj_name_list[0][0:2].upper() + proj_name_list[1].upper()
    #             elif len(proj_name_list[0]) == 1 and len(proj_name_list[1]) >= 2:
    #                 prefix = proj_name_list[0].upper() + proj_name_list[1][0:2].upper()
    #             else:
    #                 prefix = proj_name_list[0].upper()
    #         elif len(proj_name_list) == 1: # Project name with 1 word
    #             if len(proj_name_list[0]) >=3:
    #                 prefix = proj_name_list[0][0:3].upper()
    #             elif len(proj_name_list[0]) >= 2:
    #                 prefix = proj_name_list[0][0:2].upper()
    #             else:
    #                 prefix = proj_name_list[0].upper()
    #         else:
    #             prefix = "PROJ" #default to assert prefix, this might not be called!
    #         prefix += str("/%(range_year)s/")
    #         return prefix

    @api.multi
    def get_next_project_sequence_number(self):
        for project in self:
            return project.project_sequence_id._next()

    @api.multi
    def action_direct_user_proposal_accept(self):
        for record in self:
            for user in [record.approval_1_user_id, record.approval_2_user_id]:
                proposal = record.proposal_version_ids[-1]
                if not proposal.check_if_already_done_by_user(user):
                    proposal.check_for_user_approval(user)
                    message = "<b>%s</b> Accepted By <b>%s</b>" % (proposal.name, user.name)
                    record.message_post(body=message)

    @api.multi
    def action_direct_customer_proposal_accept(self):
        for record in self:
            proposal = record.proposal_version_ids[-1]
            proposal.update({'customer_done': True})
            record.write({'state': 'proposal_accepted', 'customer_accepted_proposal_id': proposal.id})
            message = "<b>%s</b> Accepted By Customer <b>%s</b>" % (proposal.name, record.partner_id.name)
            record.message_post(body=message)

