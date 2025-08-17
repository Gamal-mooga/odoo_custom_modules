from odoo import http, fields
from odoo.http import request
from odoo.exceptions import AccessError
from odoo.exceptions import ValidationError
from odoo import _, http
from odoo.addons.portal.controllers.portal import CustomerPortal
from urllib.parse import quote_plus




class EmployeePortal(http.Controller):

    def _get_employee(self):
        return request.env['hr.employee'].sudo().search([('user_id', '=', request.env.user.id)], limit=1)

    @http.route(['/my/employees'], type='http', auth='user', website=True)
    def portal_employee_home(self, **kwargs):
        employee = self._get_employee()
        print(employee)
        return request.render("custom_portal_pages.portal_employee_home", {
            'employee': employee,
        })

    @http.route(['/my/leaves/info'], type='http', auth='user', website=True)
    def portal_leaves(self, **kwargs):
        employee = self._get_employee()
        leaves = request.env['hr.leave'].sudo().search([
            ('employee_id', '=', employee.id),
        ]) if employee else []
        return request.render("custom_portal_pages.portal_leave_list_template", {
            'employee': employee,
            'leaves': leaves,
        })

    @http.route(['/my/permissions'], type='http', auth='user', website=True)
    def portal_permissions(self, **kwargs):
        employee = self._get_employee()
        permissions = request.env['hr.leave'].sudo().search([
            ('employee_id', '=', employee.id),
            ('holiday_status_id.name', 'ilike', 'Permission')
        ]) if employee else []
        return request.render("custom_portal_pages.portal_permission_list_template", {
            'employee': employee,
            'permissions': permissions,
        })

    @http.route(['/my/salary'], type='http', auth='user', website=True)
    def portal_salary(self, **kwargs):
        employee = self._get_employee()
        payslips = request.env['hr.payslip'].sudo().search([
            ('employee_id', '=', employee.id),
        ]) if employee else []
        return request.render("custom_portal_pages.portal_salary_template", {
            'employee': employee,
            'payslips': payslips,
        })

    @http.route(['/my/leave/request'], type='http', auth='user', website=True, methods=['POST'])
    def create_leave_request(self, **post):
        employee = self._get_employee()
        if not employee:
            return request.redirect('/my/leaves/info')

        start_date = post.get('start_date')
        end_date = post.get('end_date')

        # تحقق من وجود إجازة متداخلة
        overlapping = request.env['hr.leave'].sudo().search([
            ('employee_id', '=', employee.id),
            ('state', 'in', ['confirm', 'validate']),
            ('request_date_from', '<=', end_date),
            ('request_date_to', '>=', start_date),
        ], limit=1)

        if overlapping:
            raise ValidationError(
                _("⚠️ يوجد لديك طلب إجازة آخر في هذه المدة: من %s إلى %s") %
                (overlapping.request_date_from, overlapping.request_date_to)
            )

        # إنشاء الإجازة
        request.env['hr.leave'].sudo().create({
            'employee_id': employee.id,
            'request_date_from': start_date,
            'request_date_to': end_date,
            'name': post.get('reason'),
            'holiday_status_id': request.env.ref('hr_holidays.portal_leave_request_template').id,  # إجازة سنوية
        })

        return request.redirect('/my/leaves/info')
    @http.route(['/my/permission/request'], type='http', auth='user', website=True, methods=['POST','GET'])
    def create_permission_request(self, **post):
        employee = self._get_employee()
        if employee:
            request.env['hr.leave'].sudo().create({
                'employee_id': employee.id,
                'request_date_from': post.get('date'),
                'request_date_to': post.get('date'),
                'name': post.get('reason'),
                'holiday_status_id': request.env.ref('hr_holidays.holiday_status_permission').id,  # نوع الإذن
            })
        return request.redirect('/my/permissions')


    @http.route(['/my/sales'], type='http', auth="user", website=True)
    def portal_sales_card(self, **kw):
        # تحقق من أن المستخدم عنده الجروب
        if not request.env.user.has_group('custom_portal_pages.group_portal_sales'):
            return request.not_found()
        orders = request.env['sale.order'].sudo().search([
            ('partner_id', '=', request.env.user.partner_id.id)
        ])

        # عرض صفحة المبيعات
        return request.render('custom_portal_pages.portal_my_sales_template', {
            'orders': orders

        })

    @http.route(['/my/attendances'], type='http', auth='user', website=True)
    def portal_attendance(self, **kwargs):
        employee = self._get_employee()
        attendances = request.env['hr.attendance'].sudo().search([
            ('employee_id', '=', employee.id)
        ], order='check_in desc', limit=30) if employee else []

        return request.render("custom_portal_pages.portal_attendance_templatess", {
            'employee': employee,
            'attendances': attendances,
        })

    @http.route(['/my/attendances/<int:attendance_id>'], type='http', auth='user', website=True)
    def portal_attendance_detail(self, attendance_id, **kwargs):
        employee = self._get_employee()
        attendance = request.env['hr.attendance'].sudo().browse(attendance_id)

        if not attendance.exists() or attendance.employee_id.id != employee.id:
            return request.redirect('/my/attendance')

        return request.render("custom_portal_pages.portal_attendance_detail", {
            'attendance': attendance,
            'employee': employee,
        })

    @http.route(['/my/attendances/checkin'], type='http', auth='user', methods=['POST'], website=True, csrf=False)
    def portal_check_in(self, **kwargs):
        employee = self._get_employee()

        if not employee:
            request.session['portal_alert'] = {'message': 'Employee not found.', 'type': 'danger'}
            return request.redirect('/my/attendance')

        open_attendance = request.env['hr.attendance'].sudo().search([
            ('employee_id', '=', employee.id),
            ('check_out', '=', False)
        ], limit=1)

        if open_attendance:
            request.session['portal_alert'] = {
                'message': f'You are already checked in since {open_attendance.check_in}.',
                'type': 'warning'
            }
            return request.redirect('/my/attendance')

        request.env['hr.attendance'].sudo().create({
            'employee_id': employee.id,
            'check_in': fields.Datetime.now(),
        })

        request.session['portal_alert'] = {'message': 'Checked in successfully.', 'type': 'success'}
        return request.redirect('/my/attendance')

    @http.route(['/my/attendances/checkout'], type='http', auth='user', methods=['POST'], website=True, csrf=False)
    def portal_check_out(self, **kwargs):
        employee = self._get_employee()

        if not employee:
            request.session['portal_alert'] = {'message': 'Employee not found.', 'type': 'danger'}
            return request.redirect('/my/attendance')

        open_attendance = request.env['hr.attendance'].sudo().search([
            ('employee_id', '=', employee.id),
            ('check_out', '=', False)
        ], order="check_in desc", limit=1)

        if not open_attendance:
            request.session['portal_alert'] = {'message': 'No active Check In found to Check Out.', 'type': 'warning'}
            return request.redirect('/my/attendance')

        open_attendance.write({'check_out': fields.Datetime.now()})

        request.session['portal_alert'] = {'message': 'Checked out successfully.', 'type': 'success'}
        return request.redirect('/my/attendance')