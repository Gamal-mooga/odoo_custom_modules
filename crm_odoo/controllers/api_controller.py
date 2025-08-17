import json
import logging
import functools
import werkzeug.wrappers

from odoo import http
from odoo import fields
from odoo.exceptions import UserError, ValidationError, AccessError, MissingError
from odoo.http import request, Response
from odoo.exceptions import UserError
from odoo.tools import json
from werkzeug.wrappers import Response

_logger = logging.getLogger(__name__)


def invalid_response(error=None, message=None, status=400):
    return request.make_json_response({
        "success": False,
        "error": error,
        "message": message
    }, status=status)


def valid_response(data=None, status=200):
    return request.make_json_response({
        "success": True,
        "data": data
    }, status=status)

def token_required(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        token = request.httprequest.headers.get('Authorization')
        if not token:
            return {
                "success": False,
                "error": "missing_token",
                "message": "Access token is required"
            }

        token = token.replace('Bearer ', '')  # لو التوكن جاي بصيغة Bearer
        access_token = request.env['api.access_token'].sudo().search([
            ('token', '=', token),
            ('expires_at', '>', fields.Datetime.now())
        ], limit=1)

        if not access_token:
            return {
                "success": False,
                "error": "invalid_token",
               " 'message'": "Access token is invalid or expired"
            }

        request._access_token_user = access_token.user_id  # ممكن تستخدمه جوه أي API
        return func(*args, **kwargs)

    return wrapper



class AccessToken(http.Controller):
    @http.route("/api/login/v1", methods=["POST"], type="json", auth="public", csrf=False)
    def api_login(self):
        # قراءة البيانات من body
        data = request.httprequest.data.decode()
        payload = json.loads(data)
        username = payload.get("login")
        password = payload.get("password")
        print("DEBUG TYPE:", type(request))

        if not username or not password:
            return invalid_response("missing_credentials", "Both login and password are required", 400)

        db = request.session.db or request.env.cr.dbname

        try:
            request.session.authenticate(db, username, password)
        except AccessError as aee:
            return invalid_response("access_error", f"Access error: {aee.name}", 403)
        except AccessDenied:
            return {
                "success": False,
                "error": "missing_fields",
                "message": "email and password are required"
            }
        except Exception as e:
            _logger.exception("Unexpected error during login")
            return invalid_response("server_error", f"Unexpected error: {e}", 500)

        uid = request.session.uid
        if not uid:
            return invalid_response("authentication_failed", "Invalid credentials", 401)
        print(uid)

        # الحصول على access token
        access_token = request.env["api.access_token"].sudo().find_or_create_token(user_id=uid, create=True)
        user = request.env["res.users"].sudo().browse(uid)


        return {
            "uid": uid,
            "access_token": access_token,
            "company_id": user.company_id.id,
            "company_ids": user.company_ids.ids,
            "partner_id": user.partner_id.id,
            "company_name": user.company_name,
            "country": user.country_id.name,
            "contact_address": user.contact_address,
        }


    @http.route('/api/signup_portal/v1', type='json', auth='public', csrf=False, methods=['POST'])
    def signup_portal_user(self):
        raw_data = request.httprequest.data.decode()
        payload = json.loads(raw_data)
        name = payload.get('name')
        email = payload.get('email')
        password = payload.get('password')

        if not all([email, name, password]):
            return {
                "success": False,
                "error": "missing_fields",
                "message": "email, name and password are required"
            }
        if request.env['res.users'].sudo().search([('login', '=', email)], limit=1):
            return {
                "success": False,
                "error": "User Exists",
                "message": "A user with this login already exists"
            }


        # sales_portal_group = request.env.ref('api_portal.group_portal_sales_only')

        MAX_ACTIVE_TOKENS = 10

        # احسب عدد التوكنات النشطة (ما انتهتش صلاحيتها)
        active_tokens = request.env['api.access_token'].sudo().search_count([
            ('expires_at', '>', fields.Datetime.now())
        ])

        if active_tokens >= MAX_ACTIVE_TOKENS:
            return {
                "success": False,
                "error": "login_limit_reached",
                "message": f"Only {MAX_ACTIVE_TOKENS} users can be logged in at the same time."
            }
        uid = request.session.uid
        user = request.env['res.users'].sudo().browse(uid)
        company = request.env.company
        company_id = company.id

        # 🟠 عدد المستخدمين الحاليين في نفس الشركة
        MAX_USERS_PER_COMPANY = 1
        company_user_count = request.env['res.users'].sudo().search_count([
            ('company_id', '=', company_id),
            ('active', '=', True)
        ])

        if company_user_count >= MAX_USERS_PER_COMPANY:
            return {
                "success": False,
                "error": "company_limit_reached",
                "message": f"Company user limit reached ({MAX_USERS_PER_COMPANY})"
            }
        portal_group = request.env.ref('base.group_portal')
        crm_group = request.env.ref('crm.group_use_crm', raise_if_not_found=False)

        group_ids = [portal_group.id]
        if crm_group:
            group_ids.append(crm_group.id)

        user = request.env['res.users'].sudo().create({
            'name': name,
            'login': email,
            'email': email,
            'password': password,
            'company_id': company.id,  # 🟢 الشركة الأساسية
            'company_ids': [(6, 0, [company.id])],
            'groups_id': [(6, 0, group_ids)],
            # 'groups_id': [(6, 0,group_ids)],
        })

        return {
            'success': True,
            'message': 'Portal CRM user created successfully.',
            'user_id': user.id
        }
        #     token_model = request.env['api.access_token'].sudo()
        #     token = token_model.find_or_create_token(user_id=user.id, create=True)
        #
        #     return {
        #         "success": True,
        #         "message": "User created successfully",
        #         "user_id": user.id,
        #         "login": login,
        #         "access_token": token
        #     }
        #
        # except Exception as e:
        #     request.env.cr.rollback()
        #     return {
        #         "success": False,
        #         "error": "internal_error",
        #         "message": str(e)
        #     }



    @http.route(['/my/leads'], type='http', auth="user", website=True)
    def portal_my_leads(self, **kw):
        user = request.env.user
        leads = request.env['crm.lead'].sudo().search([
            ('user_id', '=', user.id)
        ])
        return request.render("api_portal.portal_my_leads", {
            'leads': leads,
        })

    @http.route("/api/create/", type='json', auth='none', csrf=False, methods=['POST'])
    @token_required
    def create_task(self):
        args = request.httprequest.data.decode()
        vals = json.loads(args)
        print(vals)
        try:
            res = request.env['task'].sudo().create(vals)
            if res:
                return {
                    "success": True,
                    "message": " created successfully",
                    "user_id": res.id,
                }
        except Exception as error:
            return {
                "success": False,
                "message": " error ",
            }

    @http.route("/api/update/<int:task_id>", type='json', auth='none', csrf=False, methods=['PUT'])
    def update_task(self, task_id):
        try:
            task_id = request.env['task'].sudo().search([('id', "=", task_id)])
            if not task_id:
                return {
                    "success": False,
                    "message": " id does not exist ",
                }

            args = request.httprequest.data.decode()
            vals = json.loads(args)
            print(vals)
            task_id.write(vals)
            return {
                "success": True,
                "message": " task has been update successfully ",
            }


        except Exception as error:
            return {
                "success": False,
                "message": " error ",
            }

    @http.route("/api/delete/<int:task_id>", type='http', auth='none', csrf=False, methods=['DELETE'])
    def delete_task(self, task_id):
        try:
            task_id = request.env['task'].sudo().search([('id', "=", task_id)])
            if not task_id:
                return {
                    "success": False,
                    "message": " id does not exist ",
                }
            task_id.unlink()
            return request.make_json_response({
                "success": True,
                "message": " task has been Delete successfully ", }
            )


        except Exception as error:
            return {
                "success": False,
                "message": " error ",
            }

    @http.route("/api/read/<int:task_id>", type='http', auth='none', csrf=False, methods=['GET'])
    def read_task(self, task_id):
        try:
            task_id = request.env['task'].sudo().search([('id', "=", task_id)])
            if not task_id:
                return {
                    "success": False,
                    "message": " id does not exist ",
                }
            return request.make_json_response({
                "id": task_id.id,
                "task_name": task_id.task_name,
                "status": task_id.status,
                "estimated_time": task_id.estimated_time,
            })


        except Exception as error:
            return {
                "success": False,
                "message": " error ",
            }
