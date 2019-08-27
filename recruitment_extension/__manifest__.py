# -*- encoding: utf-8 -*-
##############################################################################
#
#    Confianz IT
#    Copyright (C) 2019   (https://www.confianzit.com)
#
##############################################################################


{
    'name': 'Recruitment Extension',
    'version': '12.0.1.0',
    'category': 'HR',
    'sequence': '10',
    'description': """
        Confianz Recruitment
    """,
    'author': 'Confianz IT',
    'website': 'https://www.confianzit.com',
    'depends': ['hr_recruitment'],
    'data': [
        'views/hr_recruitment_views.xml',
    ],
    'demo': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
