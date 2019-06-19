# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ErrorBox(models.Model):
    _name = "error.box"
    _description = 'Error Message'

    error_message = fields.Text('Error Message')
    order = fields.Char('Invoice')
