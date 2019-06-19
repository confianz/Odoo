# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
# 
#
#
#                               Modified DashBoard with all dependancy of sale order removed.
#
#
from ast import literal_eval
import babel
from dateutil.relativedelta import relativedelta
import itertools
import json

from odoo import http, fields, _
from odoo.http import request
from odoo.tools import float_round

from odoo.addons.web.controllers.main import clean_action

DEFAULT_MONTH_RANGE = 3


class SaleTimesheetController(http.Controller):

    @http.route('/project/dashboard', type='json', auth="user")
    def plan(self, domain):
        """ Get the HTML of the project plan for projects matching the given domain
            :param domain: a domain for project.project
        """
        projects = request.env['project.project'].search(domain)
        values = self._plan_prepare_values(projects)
        view = request.env.ref('project_extension.timesheet_plan')
        return {
            'html_content': view.render(values),
            'project_ids': projects.ids,
            'actions':[],# self._plan_prepare_actions(projects, values),
        }

    def _plan_prepare_values(self, projects):

        currency = request.env.user.company_id.currency_id
        uom_hour = request.env.ref('uom.product_uom_hour')
        hour_rounding = uom_hour.rounding
        billable_types = ['non_billable', 'non_billable_project', 'billable_time', 'billable_fixed']

        values = {
            'projects': projects,
            'currency': currency,
            'timesheet_domain': [('project_id', 'in', projects.ids)],
            'stat_buttons': self._plan_get_stat_button(projects),
        }

        #
        # Hours, Rates and Profitability
        #
        dashboard_values = {
            'hours': dict.fromkeys(billable_types + ['total'], 0.0),
            'rates': dict.fromkeys(billable_types + ['total'], 0.0),
            'profit': {
                'invoiced': 0.0,
                'to_invoice': 0.0,
                'cost': 0.0,
                'total': 0.0,
            }
        }

        # hours (from timesheet) and rates (by billable type)
        dashboard_domain = [('project_id', 'in', projects.ids), ('timesheet_invoice_type', '!=', False)]  # force billable type
        dashboard_data = request.env['account.analytic.line'].read_group(dashboard_domain, ['unit_amount', 'timesheet_invoice_type'], ['timesheet_invoice_type'])
        dashboard_total_hours = sum([data['unit_amount'] for data in dashboard_data])
        for data in dashboard_data:
            billable_type = data['timesheet_invoice_type']
            dashboard_values['hours'][billable_type] = float_round(data.get('unit_amount'), precision_rounding=hour_rounding)
            dashboard_values['hours']['total'] += float_round(data.get('unit_amount'), precision_rounding=hour_rounding)
        profit = dict.fromkeys(['cost', 'expense_cost', 'total'], 0.0)
        profitability_data = self.compute_profitability_data(projects)
        profit['cost'] += profitability_data.get('cost', 0.0)
        profit['expense_cost'] += profitability_data.get('expense_cost', 0.0)
        profit['total'] = profitability_data.get('total', 0.0)
        dashboard_values['profit'] = profit

        values['dashboard'] = dashboard_values

        
        # Time Repartition (per employee per billable types)
        #
        user_ids = request.env['project.task'].sudo().search_read([('project_id', 'in', projects.ids), ('user_id', '!=', False)], ['user_id'])
        user_ids = [user_id['user_id'][0] for user_id in user_ids]
        employee_ids = request.env['res.users'].sudo().search_read([('id', 'in', user_ids)], ['employee_ids'])
        # flatten the list of list
        employee_ids = list(itertools.chain.from_iterable([employee_id['employee_ids'] for employee_id in employee_ids]))
        employees = request.env['hr.employee'].sudo().browse(employee_ids) | request.env['account.analytic.line'].search([('project_id', 'in', projects.ids)]).mapped('employee_id')
        repartition_domain = [('project_id', 'in', projects.ids), ('employee_id', '!=', False), ('timesheet_invoice_type', '!=', False)]  # force billable type
        repartition_data = request.env['account.analytic.line'].read_group(repartition_domain, ['employee_id', 'timesheet_invoice_type', 'unit_amount'], ['employee_id', 'timesheet_invoice_type'], lazy=False)

        # set repartition per type per employee
        repartition_employee = {}
        for employee in employees:
            repartition_employee[employee.id] = dict(
                employee_id=employee.id,
                employee_name=employee.name,
                non_billable_project=0.0,
                non_billable=0.0,
                billable_time=0.0,
                billable_fixed=0.0,
                total=0.0,
            )
        for data in repartition_data:
            employee_id = data['employee_id'][0]
            repartition_employee.setdefault(employee_id, dict(
                employee_id=data['employee_id'][0],
                employee_name=data['employee_id'][1],
                non_billable_project=0.0,
                non_billable=0.0,
                billable_time=0.0,
                billable_fixed=0.0,
                total=0.0,
            ))[data['timesheet_invoice_type']] = float_round(data.get('unit_amount', 0.0), precision_rounding=hour_rounding)
            repartition_employee[employee_id]['__domain_' + data['timesheet_invoice_type']] = data['__domain']

        # compute total
        for employee_id, vals in repartition_employee.items():
            repartition_employee[employee_id]['total'] = sum([vals[inv_type] for inv_type in billable_types])

        hours_per_employee = [repartition_employee[employee_id]['total'] for employee_id in repartition_employee]
        values['repartition_employee_max'] = (max(hours_per_employee) if hours_per_employee else 1) or 1
        values['repartition_employee'] = repartition_employee

        return values
    
    def compute_profitability_data(self, projects=False):
        for project in projects:
            profit = {}
            total_cost = 0.0
            total_work_cost = 0.0
            project_billable_timesheets = request.env['account.analytic.line'].search([('project_id', '=', project.id), ('billable', '=', True)])
            for employee in project_billable_timesheets.mapped('employee_id'):
                employee_cost = 0.0
                employee_work_rate = 0.0
                employee_cost_per_hour = employee.timesheet_cost
                employee_working_rate = employee.employee_rate
                employee_timesheets = project_billable_timesheets.filtered(lambda sheet: sheet.employee_id == employee)
                for sheet in employee_timesheets:
                    employee_cost += sheet.amount
                    employee_work_rate += sheet.unit_amount * employee_working_rate
                total_cost += employee_cost
                total_work_cost += employee_work_rate
                # cost <--> The rate @ the employee works for the company
                # expense_cost <--> The rate @ company charges the customer
        profit.update({'cost': total_cost, 'expense_cost': total_work_cost, 'total': total_work_cost + total_cost})
        return profit
        
        
    # --------------------------------------------------
    # Actions: Stat buttons, ...
    # --------------------------------------------------

#    def _plan_prepare_actions(self, projects, values):
#        actions = []
#        if len(projects) == 1:
#            if request.env.user.has_group('sales_team.group_sale_salesman_all_leads'):
#                to_invoice_amount = values['dashboard']['profit'].get('to_invoice', False)  # plan project only takes services SO line with timesheet into account
#                sale_orders = projects.tasks.mapped('sale_line_id.order_id').filtered(lambda so: so.invoice_status == 'to invoice')
#                if to_invoice_amount and sale_orders:
#                    if len(sale_orders) == 1:
#                        actions.append({
#                            'label': _("Create Invoice"),
#                            'type': 'action',
#                            'action_id': 'sale.action_view_sale_advance_payment_inv',
#                            'context': json.dumps({'active_ids': sale_orders.ids, 'active_model': 'project.project'}),
#                        })
#                    else:
#                        actions.append({
#                            'label': _("Create Invoice"),
#                            'type': 'action',
#                            'action_id': 'sale_timesheet.project_project_action_multi_create_invoice',
#                            'context': json.dumps({'active_id': projects.id, 'active_model': 'project.project'}),
#                        })
#        return actions

    def _plan_get_stat_button(self, projects):
        stat_buttons = []
        if len(projects) == 1:
            stat_buttons.append({
                'name': _('Project'),
                'res_model': 'project.project',
                'res_id': projects.id,
                'icon': 'fa fa-puzzle-piece',
            })
        stat_buttons.append({
            'name': _('Timesheets'),
            'res_model': 'account.analytic.line',
            'domain': [('project_id', 'in', projects.ids)],
            'icon': 'fa fa-calendar',
        })
        stat_buttons.append({
            'name': _('Tasks'),
            'count': sum(projects.mapped('task_count')),
            'res_model': 'project.task',
            'domain': [('project_id', 'in', projects.ids)],
            'icon': 'fa fa-tasks',
        })
        if request.env.user.has_group('sales_team.group_sale_salesman_all_leads'):
            invoices = projects.mapped('invoice_ids').filtered(lambda inv: inv.type == 'out_invoice')
            if invoices:
                stat_buttons.append({
                    'name': _('Invoices'),
                    'count': len(invoices),
                    'res_model': 'account.invoice',
                    'domain': [('id', 'in', invoices.ids), ('type', '=', 'out_invoice')],
                    'icon': 'fa fa-pencil-square-o',
                })
        return stat_buttons

    @http.route('/timesheet/plan/action', type='json', auth="user")
    def plan_stat_button(self, domain=[], res_model='account.analytic.line', res_id=False):
        action = {
            'type': 'ir.actions.act_window',
            'view_id': False,
            'view_mode': 'tree,form',
            'view_type': 'list',
            'domain': domain,
        }
        if res_model == 'project.project':
            view_form_id = request.env.ref('project.edit_project').id
            action = {
                'name': _('Project'),
                'type': 'ir.actions.act_window',
                'res_model': res_model,
                'view_mode': 'form',
                'view_type': 'form',
                'views': [[view_form_id, 'form']],
                'res_id': res_id,
            }
        elif res_model == 'account.analytic.line':
            ts_view_tree_id = request.env.ref('hr_timesheet.hr_timesheet_line_tree').id
            ts_view_form_id = request.env.ref('hr_timesheet.hr_timesheet_line_form').id
            action = {
                'name': _('Timesheets'),
                'type': 'ir.actions.act_window',
                'res_model': res_model,
                'view_mode': 'tree,form',
                'view_type': 'form',
                'views': [[ts_view_tree_id, 'list'], [ts_view_form_id, 'form']],
                'domain': domain,
            }
        elif res_model == 'project.task':
            action = request.env.ref('project.action_view_task').read()[0]
            action.update({
                'name': _('Tasks'),
                'domain': domain,
                'context': dict(request.env.context),  # erase original context to avoid default filter
            })
            # if only one project, add it in the context as default value
            tasks = request.env['project.task'].sudo().search(literal_eval(domain))
            if len(tasks.mapped('project_id')) == 1:
                action['context']['default_project_id'] = tasks.mapped('project_id')[0].id
        elif res_model == 'account.invoice':
            action = clean_action(request.env.ref('account.action_invoice_tree1').read()[0])
            action['domain'] = domain
            action['context'] = {'create': False, 'delete': False}  # only edition of invoice from overview
        return action
