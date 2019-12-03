# -*- coding:utf-8 -*-

from odoo import models, fields, api
#from inscriptis import get_text
import re


class MailThread(models.AbstractModel):
    _inherit = 'mail.thread'

    @api.multi
    @api.returns('mail.message', lambda value: value.id)
    def message_post(self, **kwargs):
        message = super(MailThread, self).message_post(**kwargs)
        if message.model == 'proposal.version' and message.res_id:
            proposal = self.env['proposal.version'].browse(message.res_id)
            if proposal.project_id.state =='send_to_customer':
                message.write({'read_by_customer': True})
            if proposal.project_id:
                context = dict(self._context)
                project = proposal.project_id
                context.update({'default_res_id': project.id})
                project.with_context(context).message_post(**kwargs)
        return message

class Message(models.Model):

    _inherit = 'mail.message'

    read_by_customer = fields.Boolean(string="Read Permission", default=False)

#    @api.model
#    def message_new(self, msg_dict, custom_values=None):
#        if self._name == "crm.lead":
#            dict_cust_val = self.create_dict_from_html_msg_body(msg_dict.get('body', False))
#            custom_values.update(dict_cust_val)
#        return super(MailThread, self).message_new(msg_dict=msg_dict, custom_values=custom_values)
#        
#    @api.model
#    def create_dict_from_html_msg_body(self, html_message):
#        """
#            Creates a python dictionary from an html body.
#                @param html_message: The html message body containing message to be filtered
#                return: python dictionary with field names as keys, and message filtered from html body as values.
#        """
#        text = get_text(html_message)   # from python library inscriptis
#        dict_val = {}
#        contact_name = ""
#        for items in text.split("\n"):
#            if ":" in items:
#                item = items.split(":")
#                if re.search("^first[ ]*name$", item[0], re.IGNORECASE):
#                    dict_val.update({"firstname": item[1]})
#                    contact_name += item[1]
#                elif re.search("^last[ ]*name$", item[0], re.IGNORECASE):
#                    dict_val.update({"lastname": item[1]})
#                    contact_name += " " + item[1]
#                elif re.search("^phone[ ]*number|phone$", item[0], re.IGNORECASE):
#                    dict_val.update({"phone": item[1]})
#                elif re.search("^mobile[ ]*number *|mobile$", item[0], re.IGNORECASE):
#                    dict_val.update({"mobile": item[1]})
#                elif re.search("^email[ ]*[address]*$", item[0], re.IGNORECASE):
#                    dict_val.update({"email_from": item[1]})
#                elif re.search("^company$", item[0], re.IGNORECASE):
#                    dict_val.update({"partner_name": item[1]})
#                elif re.search("^website$", item[0], re.IGNORECASE):
#                    dict_val.update({"website": item[1]})
#                elif re.search("^comments|message$", item[0], re.IGNORECASE):
#                    dict_val.update({"description": item[1]})
#                dict_val.update({"contact_name": contact_name})
#        return dict_val
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
