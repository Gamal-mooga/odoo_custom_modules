import secrets
from datetime import timedelta

from odoo import models, fields, api
from odoo.exceptions import UserError

class ApiAccessToken(models.Model):
    _name = 'api.access_token'
    _description = 'API Access Token'
    _rec_name = 'token'

    token = fields.Char(string='Token', required=True, index=True, readonly=True)
    user_id = fields.Many2one('res.users', string='User', required=True, ondelete='cascade')
    create_date = fields.Datetime(string='Created on', readonly=True)
    expires_at = fields.Datetime(string='Expires At', required=True, readonly=True)

    _sql_constraints = [
        ('token_unique', 'unique(token)', 'Token must be unique.')
    ]

    @api.model
    def _generate_token(self):
        return secrets.token_urlsafe(40)

    @api.model
    def find_or_create_token(self, user_id, create=False):
        now = fields.Datetime.now()
        token = self.sudo().search([
            ('user_id', '=', user_id),
            ('expires_at', '>', now)
        ], limit=1)

        if token:
            return token.token

        if not create:
            return None

        expires = now + timedelta(days=1)
        new_token = self.create({
            'user_id': user_id,
            'token': self._generate_token(),
            'expires_at': expires,
        })
        return new_token.token
