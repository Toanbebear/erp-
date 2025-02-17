# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import logging

import werkzeug
from odoo import fields
from odoo import http
from odoo.addons.survey.controllers.main import Survey
from odoo.exceptions import UserError
from odoo.http import request

_logger = logging.getLogger(__name__)


class SurveyBrandPhoneCall(Survey):

    @http.route('/survey_brand/phone_call/<int:phone_call_id>', type='http', auth='public', website=True)
    def survey_brand_phone_call_init(self, phone_call_id, **post):
        """ Khởi tạo khảo sát, dựa vào tiêu chí của phiếu và chọn lựa của người dùng
            Tìm ra phiếu khảo sát tương ứng
            Nếu không tìm thấy thì thông báo
            Nếu có hơn 1 phiếu thì cho người dùng chọn phiếu sẽ khảo sát
        """
        phone_call = request.env['crm.phone.call'].sudo().browse(phone_call_id)
        walkin = phone_call.medical_id
        partner = phone_call.partner_id
        customer_phone = partner.phone if partner.phone else partner.mobile
        timing = request.env['survey.survey.type'].sudo().search([('is_pc', '=', True)])
        booking = phone_call.crm_id
        data = {
            'user_id': request.env.user.id,  # Người làm khảo sát
            'customer_name': partner.name,
            'customer_phone': customer_phone,
            'customer_phone_x': customer_phone[0:3] + 'xxxx' + customer_phone[7:],
            'branch': phone_call.company_id.name,
            'group_services': phone_call.crm_line_id.service_id.service_category,
            'phone_call': phone_call_id,
            'branch_id': booking.company_id.id,
            'brand': booking.brand_id.id,
            'booking': booking.id,
            'timing': timing,
            'data_submit': '/survey_brand/phone_call/%s/survey' % phone_call_id,
        }

        if post:
            response = request.render('survey_brand.survey_brand_select_survey', data)
            response.headers['X-Frame-Options'] = 'DENY'
            return response
        else:
            return request.render('survey_brand.survey_brand_init_survey', data)

    @http.route('/survey_brand/phone_call/<int:phone_call_id>/survey', type='http', auth='public', website=True)
    def get_phone_call_surveys(self, phone_call_id, **post):
        phone_call = request.env['crm.phone.call'].sudo().browse(phone_call_id)
        partner = phone_call.partner_id
        customer_phone = partner.phone if partner.phone else partner.mobile

        timing = request.env['survey.survey.type'].sudo().search([('is_pc', '=', True)])
        booking = phone_call.crm_id
        walk_in = phone_call.medical_id
        group_services = walk_in.list_advisory_services.service_advisory.service_category

        data = {
            'user_id': request.env.user.id,  # Người làm khảo sát
            'customer_name': partner.name,
            'customer_phone': customer_phone,
            'customer_phone_x': customer_phone[0:3] + 'xxxx' + customer_phone[7:],
            'branch': phone_call.company_id.name,
            'group_services': group_services,
            'phone_call': phone_call_id,
            'booking': booking,
            'timing': timing,
        }

        if post and 'survey_survey' in post and 'group_service' in post and 'time' in post:
            ret = {'redirect': '/survey_brand/phone_call/%s/%s?group_service=%s&time=%s' % (phone_call_id, post['survey_survey'],post['group_service'], post['time'])}
            return json.dumps(ret)
        else:
            return request.render('survey_brand.survey_brand_init_survey', data)

    @http.route('/survey_brand/phone_call/<string:phone_call_id>/<string:survey_token>', type='http', auth='public',
                website=True)
    def survey_brand_phone_call_start(self, phone_call_id, survey_token, **post):
        """
        """
        answer_token = None
        access_data = self._get_access_data(survey_token, answer_token, ensure_token=False)
        if access_data['validity_code'] is not True:
            return self._redirect_with_error_survey_brand(access_data, access_data['validity_code'])

        survey_sudo, answer_sudo = access_data['survey_sudo'], access_data['answer_sudo']
        if not answer_sudo:
            try:
                group_service = None
                survey_time_id = None
                if 'group_service' in post:
                    group_service = int(post['group_service'])
                if 'time' in post:
                    survey_time_id = int(post['time'])
                answer_sudo = survey_sudo._create_answer_phone_call(user=request.env.user, phone_call_id=phone_call_id, group_service_id=group_service, survey_time_id=survey_time_id )
            except UserError:
                answer_sudo = False
        if not answer_sudo:
            try:
                survey_sudo.with_user(request.env.user).check_access_rights('read')
                survey_sudo.with_user(request.env.user).check_access_rule('read')
            except:
                return werkzeug.utils.redirect("/")
            else:
                return request.render("survey.403", {'survey': survey_sudo})

        return request.redirect(
            '/survey_brand/fill/phone_call/%s/%s/%s' % (phone_call_id, survey_sudo.access_token, answer_sudo.token))
        # phone_call = request.env['crm.phone.call'].sudo().browse(int(phone_call_id))
        # time_id = None
        # group_service_id = None
        # if 'time' in post:
        #     time_id = int(post['time'])
        # if 'group_service' in post:
        #     group_service_id = int(post['group_service'])
        # request.env['survey.user_input'].sudo().create({
        #     'survey_id': survey_sudo.id,
        #     'partner_id': phone_call.partner_id.id,
        #     'state': 'new',
        #     'crm_id': phone_call.crm_id.id,
        #     'phone_call_id': phone_call.id,
        #     'group_service_id': group_service_id if group_service_id else None,
        #     'survey_time_id': time_id if time_id else None
        # })
        # return request.redirect('https://www.google.com.vn/?hl=vi')

    @http.route('/survey_brand/phone_call/<string:phone_call_id>/<string:survey_token>', type='http', auth='public',
                website=True)
    def survey_brand_start_phone_call(self, phone_call_id, survey_token, answer_token=None, email=False, **post):
        """ Start a survey by providing
         * a token linked to a survey;
         * a token linked to an answer or generate a new token if access is allowed;
        """
        access_data = self._get_access_data(survey_token, answer_token, ensure_token=False)
        if access_data['validity_code'] is not True:
            return self._redirect_with_error_survey_brand(access_data, access_data['validity_code'])
        survey_sudo, answer_sudo = access_data['survey_sudo'], access_data['answer_sudo']
        if not answer_sudo:
            try:
                group_service = None
                survey_time_id = None
                if 'group_service' in post:
                    group_service = int(post['group_service'])
                if 'time' in post:
                    survey_time_id = int(post['time'])
                answer_sudo = survey_sudo._create_answer_phone_call(
                    user=request.env.user,
                    phone_call_id=phone_call_id,
                    email=email,
                    group_service_id=group_service, survey_time_id=survey_time_id)

            except UserError:
                answer_sudo = False

        if not answer_sudo:
            try:
                survey_sudo.with_user(request.env.user).check_access_rights('read')
                survey_sudo.with_user(request.env.user).check_access_rule('read')
            except:
                return werkzeug.utils.redirect("/")
            else:
                return request.render("survey.403", {'survey': survey_sudo})

        if answer_sudo.state == 'new':  # Intro page
            customer_phone = answer_sudo.crm_lead.phone if answer_sudo.crm_lead.phone else answer_sudo.crm_lead.mobile
            data = {
                'survey': survey_sudo,
                'answer': answer_sudo,
                'page': 0,
                'user_id': request.env.user.id,  # Người làm khảo sát
                'user_ids': survey_sudo.company_id.user_ids,
                'customer_name': answer_sudo.crm_lead.contact_name,
                'customer_phone': customer_phone,
                'branch': answer_sudo.crm_lead.company_id.name,
                'group_services': answer_sudo.group_service_ids,
                'booking': answer_sudo.crm_lead.id,
            }
            return request.render('survey_brand.survey_brand_init', data)

        return request.redirect('/survey_brand/fill/%s/%s' % (survey_sudo.access_token, answer_sudo.token))

    @http.route(['/survey_brand/submit-creator/<string:survey_token>/<string:answer_token>'], type='http',
                methods=['POST'], csrf=False, auth='public', website=True)
    def survey_brand_submit_creator(self, survey_token, answer_token, **post):
        ret = {}
        user_input = request.env['survey.user_input'].sudo().search([('token', '=', answer_token)], limit=1)

        if post['user']:
            user_id = request.env['res.users'].sudo().search([('id', '=', int(post['user']))], limit=1)
            user_input['survey_creator'] = user_id
        if 'customer_phone' in post:
            customer_name = post['customer_name'].upper()
            exit_partner = request.env['res.partner'].sudo().search([('phone', '=', post['customer_phone'])], limit=1)
            if exit_partner:
                exit_partner.name = post['customer_name']
                user_input.write({
                    'partner_id': exit_partner.id
                })
            else:
                partner = request.env['res.partner'].sudo().create({
                    'name': customer_name,
                    'phone': post['customer_phone']
                })
                user_input['partner_id'] = partner.id
        access_data = self._get_access_data(survey_token, answer_token, ensure_token=False)
        if access_data['validity_code'] is not True:
            return self._redirect_with_error_survey_brand(access_data, access_data['validity_code'])
        survey_sudo, answer_sudo = access_data['survey_sudo'], access_data['answer_sudo']
        ret['redirect'] = '/survey_brand/fill/%s/%s' % (survey_sudo.access_token, answer_sudo.token)
        return json.dumps(ret)

    @http.route('/survey_brand/fill/phone_call/<int:phone_call_id>/<string:survey_token>/<string:answer_token>',
                type='http',
                auth='public',
                website=True)
    def survey_brand_phone_call_display_page_base(self, phone_call_id, survey_token, answer_token, prev=None, **post):
        access_data = self._get_access_data(survey_token, answer_token, ensure_token=True)
        if access_data['validity_code'] is not True:
            return self._redirect_with_error_survey_brand(access_data, access_data['validity_code'])
        phone_call = request.env['crm.phone.call'].sudo().browse(int(phone_call_id))
        walkin = request.env['sh.medical.appointment.register.walkin'].sudo().browse(int(phone_call.medical_id.id))
        booking = request.env['crm.lead'].sudo().browse(int(phone_call.crm_id.id))
        survey_sudo, answer_sudo = access_data['survey_sudo'], access_data['answer_sudo']
        answer_sudo.partner_id = booking.partner_id.id if booking.partner_id.id else None
        if survey_sudo.is_time_limited and not answer_sudo.start_datetime:
            # init start date when user starts filling in the survey
            answer_sudo.write({
                'start_datetime': fields.Datetime.now()
            })

        page_or_question_key = 'question' if survey_sudo.questions_layout == 'page_per_question' else 'page'

        triggering_answer_by_question, triggered_questions_by_answer, triggering_question = answer_sudo._get_conditional_values()

        data_trigger = {
            'triggering_answer_by_question': {
                question.id: triggering_answer_by_question[question].id for question in
                triggering_answer_by_question.keys()
                if triggering_answer_by_question[question]
            },
            'triggered_questions_by_answer': {
                answer.id: triggered_questions_by_answer[answer].ids
                for answer in triggered_questions_by_answer.keys()
            },
            'triggering_question': triggering_question,
        }

        # Select the right page
        if answer_sudo.state == 'new':  # First page
            page_or_question_id, last = survey_sudo.next_question(answer_sudo, 0, data_trigger, go_back=False)
            data = {
                'survey': survey_sudo,
                page_or_question_key: page_or_question_id,
                'answer': answer_sudo,
                'booking': booking.id,
                'phone_call': phone_call_id
            }
            if last:
                data.update({'last': True})

            return request.render('survey_brand.survey_brand', data)
        elif answer_sudo.state == 'done':  # Display success message
            return request.render('survey_brand.survey_finished',
                                  self._prepare_survey_finished_values(survey_sudo, answer_sudo))
        elif answer_sudo.state == 'skip':
            flag = (True if prev and prev == 'prev' else False)
            page_or_question_id, last = survey_sudo.next_question(answer_sudo,
                                                                  answer_sudo.last_displayed_page_id.id,
                                                                  data_trigger,
                                                                  go_back=flag)

            # special case if you click "previous" from the last page, then leave the survey, then reopen it from the URL, avoid crash
            if not page_or_question_id:
                page_or_question_id, last = survey_sudo.next_question(answer_sudo,
                                                                      answer_sudo.last_displayed_page_id.id,
                                                                      data_trigger,
                                                                      go_back=True)

            data = {
                'survey': survey_sudo,
                page_or_question_key: page_or_question_id,
                'answer': answer_sudo,
                'booking': booking.id,
                'phone_call': phone_call_id
            }
            if last:
                data.update({'last': True})
            return request.render('survey_brand.survey_brand', data)
        else:
            return request.render("survey.403", {'survey': survey_sudo})


