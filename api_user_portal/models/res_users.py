from odoo import models, fields, api

class ResUsers(models.Model):
    _inherit = 'res.users'

    portal_extra_groups = fields.Many2many(
        'res.groups',
        string='Portal Extra Permissions',
        domain="[('category_id.name', '=', 'Portal')]",
        help="Select extra permissions for this portal user."
    )

    @api.model
    def create(self, vals):
        user = super().create(vals)
        if user.portal_extra_groups:
            user.groups_id = [(4, g.id) for g in user.portal_extra_groups]
        return user

    def write(self, vals):
        res = super().write(vals)
        if 'portal_extra_groups' in vals:
            for user in self:
                user.groups_id = [(4, g.id) for g in user.portal_extra_groups]
        return res