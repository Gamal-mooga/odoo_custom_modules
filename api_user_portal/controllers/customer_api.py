from docutils.nodes import status

from odoo import http
from odoo.http import request
import json


class CustomerAPI(http.Controller):

    @http.route('/api/create_customer', type='json', auth='public', methods=['POST'], csrf=False)
    def create_customer(self, **kwargs):
        try:
            # الحصول على البيانات من JSON
            data = request.httprequest.data.decode()
            vals = json.loads(data)
            print(vals)

            # إنشاء سجل جديد
            res = request.env['library.book'].sudo().create(vals)
            print(res)

            return {'status': 'success', 'id': res.id}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    @http.route('/api/update_customer/<int:id>', type='json', auth='public', methods=['PUT'], csrf=False)
    def update_customer(self, id, **kwargs):
        try:
            # البحث عن السجل
            record = request.env['library.book'].sudo().search([('id', '=', id)])
            if not record:
                return {'status': 'error', 'message': 'Record not found'}

            # قراءة البيانات وتحديث السجل
            data = request.httprequest.data.decode()
            vals = json.loads(data)
            print(vals)

            record.write(vals)
            return {'status': 'success', 'message': 'Record updated'}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    @http.route('/api/get_customer/<int:id>', type='http', auth='public', methods=['GET'],csrf=False )
    def get_property(self,id):
        try:
            record = request.env['library.book'].sudo().search([('id', '=', id)])
            if record:
                data={
                    "name": record.name,
                    "age": record.age,
                }
                return request.make_json_response(data, status=200)

            else:
                return request.make_json_response({
                    "message":"ID does not exist!",

                },status=400)
        except Exception as error:
            return request.make_json_response({

                "message":error,
            })

    @http.route('/api/delete_customer/<int:id>', type='http', auth='public', methods=['DELETE'], csrf=False)
    def delete_customer(self, id):
        try:
            record = request.env['library.book'].sudo().search([('id', '=', id)])
            if record:
                record.unlink()
                return request.make_json_response({
                    "message": f"Record with ID {id} deleted successfully."
                }, status=200)
            else:
                return request.make_json_response({
                    "message": "ID does not exist!"
                }, status=404)
        except Exception as error:
            return request.make_json_response({
                "message": f"An error occurred: {str(error)}"
            }, status=500)