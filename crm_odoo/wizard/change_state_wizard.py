from odoo import fields,models

class Wizard(models.TransientModel):
    _name='wizard'

    task_id=fields.Many2one('task')
    status=fields.Selection([
        ('new', 'New'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('close', 'Close'),
    ])

    def action_confirm(self):
        self.task_id.status=self.status