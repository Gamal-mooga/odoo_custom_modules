from odoo import http
from odoo.http import request

class CustomEventController(http.Controller):

    @http.route(['/custom/events', '/custom/events/<int:event_id>'], type='http', auth="public", website=True)
    def custom_events(self, event_id=None, **kwargs):
        values = {}
        if event_id:
            event = request.env['event.event'].sudo().browse(event_id)
            registrations = request.env['event.registration'].sudo().search([('event_id', '=', event.id)])
            booths = []
            has_booths = False
            if 'event.booth' in request.env:
                booths = request.env['event.booth'].sudo().search([('event_id', '=', event.id)])
                has_booths = True
            values = {
                'event': event,
                'registrations': registrations,
                'booths': booths,
                'has_booths': has_booths,
            }
            return request.render('website_event_crm.custom_event_detail_template', values)
        else:
            events = request.env['event.event'].sudo().search([])
            values['events'] = events
            return request.render('website_event_crm.custom_event_list_template', values)
