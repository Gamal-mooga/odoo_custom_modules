{
    'name': 'Custom Portal Pages',
    'version': '1.0',
    'category': 'Website',
    'summary': 'Portal pages for different employee types',
    'author': 'Kassem',
    'depends': ['portal','base', 'website','hr', 'hr_holidays', 'hr_attendance', 'hr_payroll','event_sale','website_event_sale', 'website_event_booth','website_event'],
    'data': [
        'security/portal_groups.xml',
        'views/portal_templates.xml',
        'views/employee_actions_templates.xml',
        'views/portal_sales.xml',
        'views/portal_attendance_templates.xml',
        'views/website_update.xml',
        'views/category.xml',
    ],
    'website': 'https://yourcompany.com',

    'installable': True,
    'application': False,
}
