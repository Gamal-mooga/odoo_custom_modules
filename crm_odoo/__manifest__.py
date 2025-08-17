

{
    'name': 'CRM API',
    'author': 'Moaz',
    'depends': ['base','mail','crm','portal'],
    'data': [
        # 'security/group_crm.xml',
        'security/ir.model.access.csv',
        'data/sequence.xml',
        # 'data/groups.xml',
        # 'views/crm_portal_leads.xml',
        'views/base_menu.xml',
        'views/task_view.xml',
        'wizard/change_state_wizard_view.xml',
        'report/task_report.xml',
    ],
    'application': True,
    'sequence': '-200',
    'installable': True,

}
