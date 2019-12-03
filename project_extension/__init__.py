from . import models
from . import controllers
from . import wizards

from odoo import api, SUPERUSER_ID

def _update_base_values(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    report_1 = env.ref('account.account_invoices', False)
    report_2 = env.ref('account.account_invoices_without_payment', False)
    report_1.report_name = 'project_extension.report_invoice_document_with_payments_inherits'
    report_1.report_file = 'project_extension.report_invoice_document_with_payments_inherits'
    report_2.report_name = 'project_extension.report_invoice_document_project_extension'
    report_2.report_file = 'project_extension.report_invoice_document_project_extension'

def uninstall_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    report_1 = env.ref('account.account_invoices', False)
    report_2 = env.ref('account.account_invoices_without_payment', False)
    company = env.ref("base.main_company")
    company.external_report_layout_id = env.ref('web.external_layout_clean')
    report_1.report_name = 'account.report_invoice_with_payments'
    report_1.report_file = 'account.report_invoice_with_payments'
    report_1.paperformate_id = None
    report_2.report_name = 'account.report_invoice'
    report_2.report_file = 'account.report_invoice'
    report_2.paperformat_id = None
