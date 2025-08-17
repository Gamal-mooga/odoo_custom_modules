from odoo import http, fields
from odoo.http import request 
from odoo.exceptions import ValidationError
from odoo import _, http
from odoo.addons.portal.controllers.portal import CustomerPortal
from urllib.parse import quote_plus
from datetime import datetime
from dateutil.relativedelta import relativedelta


def _month_bounds(dt):
    first = dt.replace(day=1)
    # inclusive end-of-month at 23:59:59
    last = (first + relativedelta(months=1)) - relativedelta(seconds=1)
    return first, last

def _find_active_contract(employee, on_date):
    Contract = request.env['hr.contract'].sudo()
    # current or most recent valid contract
    return Contract.search([
        ('employee_id', '=', employee.id),
        ('date_start', '<=', on_date.date()),
        '|', ('date_end', '=', False), ('date_end', '>=', on_date.date()),
        ('state', 'in', ['open','close','draft'])  # keep flexible
    ], order="state desc, date_start desc", limit=1)

class EmployeePortal(http.Controller):
    def _get_employee(self):
        return request.env['hr.employee'].sudo().search([('user_id', '=', request.env.user.id)], limit=1)
    @http.route(['/test'], type='http', auth='user' , methods=['POST','GET'])
    def test(self, **kwargs):
        print("test from api")
         
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
    def portal_my_salary(self, **kw):
        # 1) احصل على الموظف المرتبط بالمستخدم
        employee = request.env['hr.employee'].sudo().search(
            [('user_id', '=', request.uid)], limit=1
        )
        if not employee:
            return request.render("portal.my_home", {
                'error': "لا يوجد موظف مربوط بهذا المستخدم."
            })

        today = fields.Datetime.context_timestamp(request.env.user, fields.Datetime.now())
        contract = _find_active_contract(employee, today)
        if not contract:
            return request.render("portal.my_home", {
                'error': "لا يوجد عقد نشط/صالح لهذا الموظف."
            })

        # 2) إعداد التقويم لحساب ساعات الشهر المتوقعة
        calendar = contract.resource_calendar_id or employee.resource_calendar_id or employee.company_id.resource_calendar_id
        tz = employee.tz or request.env.user.tz or "UTC"

        months_count = int(kw.get('months', 6))  # آخر 6 شهور افتراضياً
        rows = []

        Attendance = request.env['hr.attendance'].sudo()
        currency = employee.company_id.currency_id

        for i in range(months_count):
            ref_dt = (today.replace(day=15) - relativedelta(months=i))  # منتصف الشهر لسلامة الحساب
            m_first, m_last = _month_bounds(ref_dt)

            # فترات زمنية بتوقيت المستخدم
            start = m_first.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=None)
            end   = m_last.replace(hour=23, minute=59, second=59, microsecond=0, tzinfo=None)

            # ساعات الشهر المتوقعة من التقويم
            expected_hours = 0.0
            if calendar:
                # get_work_hours_count expects UTC-naive datetimes in server TZ; نستعمل helpers الآمنة:
                start = m_first.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=None)
                end   = m_last.replace(hour=23, minute=59, second=59, microsecond=0, tzinfo=None)
                expected_hours = calendar.get_work_hours_count(
                    start,
                    end,
                    compute_leaves=True
                )or 0.0 
            expected_hours = calendar.get_work_hours_count(
                start,
                end,
                compute_leaves=True
            )


            # ساعات العمل الفعلية من الحضور
            att_domain = [
                ('employee_id', '=', employee.id),
                ('check_in', '>=', m_first.replace(tzinfo=None)),
                ('check_in', '<=', m_last.replace(tzinfo=None)),
            ]
            worked_hours = sum(Attendance.search(att_domain).mapped('worked_hours')) or 0.0

            wage = float(contract.wage or 0.0)
            hourly_rate = (wage / expected_hours) if expected_hours > 0 else 0.0
            payable = worked_hours * hourly_rate

            rows.append({
                'month_label': ref_dt.strftime('%B %Y'),
                'wage': wage,
                'expected_hours': round(expected_hours, 2),
                'worked_hours': round(worked_hours, 2),
                'hourly_rate': round(hourly_rate, 2),
                'payable': round(payable, 2),
                'is_current': i == 0,
            })

        values = {
            'employee': employee,
            'contract': contract,
            'currency': currency,
            'rows': list(reversed(rows)),  # الأقدم أولاً
        }
        return request.render("custom_portal_pages.portal_my_salary_template", values)

    @http.route(['/my/leave/request'], type='http', auth='user', website=True, methods=['POST','GET'])
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
    @http.route(['/my/leaves/request'], type='http', auth='user', website=True, methods=['POST','GET'])
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
            return request.redirect('/my/attendances')

        request.env['hr.attendance'].sudo().create({
            'employee_id': employee.id,
            'check_in': fields.Datetime.now(),
        })

        request.session['portal_alert'] = {'message': 'Checked in successfully.', 'type': 'success'}
        return request.redirect('/my/attendances')

    @http.route(['/my/attendances/checkout'], type='http', auth='user', methods=['POST'], website=True, csrf=False)
    def portal_check_out(self, **kwargs):
        employee = self._get_employee()

        if not employee:
            request.session['portal_alert'] = {'message': 'Employee not found.', 'type': 'danger'}
            return request.redirect('/my/attendances')

        open_attendance = request.env['hr.attendance'].sudo().search([
            ('employee_id', '=', employee.id),
            ('check_out', '=', False)
        ], order="check_in desc", limit=1)

        if not open_attendance:
            request.session['portal_alert'] = {'message': 'No active Check In found to Check Out.', 'type': 'warning'}
            return request.redirect('/my/attendances')

        open_attendance.write({'check_out': fields.Datetime.now()})

        request.session['portal_alert'] = {'message': 'Checked out successfully.', 'type': 'success'}
        return request.redirect('/my/attendances')