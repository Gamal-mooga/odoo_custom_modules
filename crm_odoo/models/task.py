from email.policy import default

from odoo import models, fields, api
from odoo.exceptions import ValidationError


class Task(models.Model):
    _name='task'
    _inherit = ['mail.thread','mail.activity.mixin']

    sequence = fields.Char(default='New',readonly=True)
    task_name=fields.Text(translate=True)
    assign_to=fields.Many2one('res.partner')
    description=fields.Text(translate=True)
    due_date=fields.Date()
    status=fields.Selection([
        ('new','New'),
        ('in_progress','In Progress'),
        ('completed','Completed'),
        ('closed', 'Closed'),
    ])
    estimated_time = fields.Float(string="Estimated Time (hours)", required=True)
    timesheet_ids = fields.One2many('task.timesheet', 'task_id', string="Timesheets")
    total_time = fields.Float(string="Total Recorded Time (hours)", compute="_compute_total_time", store=True)
    active=fields.Boolean(default=True)
    is_late=fields.Boolean()

    @api.depends('timesheet_ids.time_spent')
    def _compute_total_time(self):
        for record in self:
            record.total_time = sum(record.timesheet_ids.mapped('time_spent'))

    @api.constrains('total_time', 'estimated_time')
    def _check_total_time(self):
        for record in self:
            if record.total_time > record.estimated_time:
                raise ValidationError("Total recorded time cannot exceed the estimated time.")


    def action_close(self):
        for rec in self:
            rec.status = 'close'


    def check_late(self):
        task_id=self.search([])
        for rec in task_id:
            if rec.status in['new','in_progress'] and rec.due_date < fields.date.today():
                rec.is_late=True

    @api.model
    def create(self, vals):
        res = super(Task, self).create(vals)
        if res.sequence == 'New':
            res.sequence = self.env['ir.sequence'].next_by_code('task_seq')
            return res

    def action_open_wizard_window(self):
        action=self.env['ir.actions.actions']._for_xml_id('task_one.change_wizard_window_action')
        action['context']={'default_task_id': self.id},
        return action

class TaskTimesheet(models.Model):
    _name = 'task.timesheet'

    task_id = fields.Many2one('task', string="Task", required=True, ondelete='cascade')
    description = fields.Text(string="Description")
    time_spent = fields.Float(string="Time Spent (hours)", required=True)
    date = fields.Date(string="Date", default=fields.Date.today)