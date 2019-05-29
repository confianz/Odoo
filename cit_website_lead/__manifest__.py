# -*- encoding: utf-8 -*-
##############################################################################
#
#    Confianz IT
#    Copyright (C) 2019   (https://www.confianzit.com)
#
##############################################################################


{
    'name': 'Confianz Website Lead',
    'version': '12.0.1.0',
    'category': 'CRM',
    'sequence': '10',
    'description': """
        This module will add the ability create opportunities from website.
    """,
    'author': 'Confianz IT',
    'website': 'https://www.confianzit.com',
    'depends': ['crm'],
    'data': [
        'views/crm_views.xml',
    ],
    'demo': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
