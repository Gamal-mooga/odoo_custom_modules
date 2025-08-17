{
    'name': 'Library Management',
    'version': '1.0',
    'summary': 'Simple Library App',
    'sequence': 10,
    'description': """Manage books in a library""",
    'category': 'Productivity',
    'author': 'Your Name',
    'depends': ['base','crm','sale','hr','hr_holidays'],
    'data': [#'models/views/sale_order_view.xml',




        'models/views/groups_form_inherit.xml',
        'models/views/edit_portal.xml',
        'models/views/group_new.xml',
        'models/views/emplyess_portal.xml',
       # 'models/views/menu_employee.xml',
             ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
