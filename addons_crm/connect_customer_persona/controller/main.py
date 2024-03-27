"""Part of odoo. See LICENSE file for full copyright and licensing details."""
import logging
import json
from odoo import http
from odoo.http import request
from odoo.tools.image import image_data_uri
_logger = logging.getLogger(__name__)
stage_case = {'new': 'Chưa xử lý', 'processing': 'Đang xử trí', 'finding':'Tìm thêm thông tin', 'waiting_response': 'Chờ phản hồi',
              'need_to_track': 'Cần theo dõi', 'resolve': 'Đã có hướng xử lý', 'complete': 'Hoàn thành'}

def get_url_base():
    config = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
    if config:
        return config
    return ''


class PartnerController(http.Controller):

    @http.route("/api/connect-customer-persona/get-partner", type="http", auth="none", methods=["GET"], csrf=False, cors='*')
    def get_customer_persona(self, **payload):
        """ Lấy thông tin khách hàng, lịch sử khám qua id company và id khách hàng"""
        _logger.info('----------------------------')
        # for key in ['partner_id', 'company_id']:
        #     if key not in body.keys():
        #         return json_invalid_response(message="The parameter %s is missing! " % key)
        partner = request.env['res.partner'].sudo().browse(int(payload.get('partner_id')))
        # company = request.env['res.company'].sudo().browse(int(payload.get('company_id')))
        data = {}
        # if partner and company:
        if partner:
            data['id'] = partner.id
            data['thong_tin_chung'] = [{
                'image': image_data_uri(partner.image_256) if partner.image_256 else '',
                'name': partner.name,
                'gender': partner.gender or '',
                'pass_port': partner.pass_port or '',
                'phone': partner.phone or '',
                'mobile': partner.mobile or '',
                'birth_date': partner.birth_date.strftime('%d/%m/%Y') if partner.birth_date else '',
                'year_of_birth': partner.year_of_birth or '',
                'email_from': partner.email or '',
                'country_name': partner.country_id.name or '',
                'state_name': partner.state_id.name or '',
                'district_name': partner.district_id.name or '',
                'street': partner.street or '',
                'overseas_vietnamese': partner.overseas_vietnamese or '',
                'career': partner.career,
                'acc_facebook': partner.acc_facebook if partner.acc_facebook else 'Chưa có thông tin',
                'marital_status': dict(partner._fields['marital_status'].selection).get(partner.marital_status) if partner.marital_status else 'Chưa có thông tin',

            }]
            ####### Mong muốn
            list_mong_muon = []
            # mong_muon = partner.persona.filtered(lambda p: p.type == '1')
            mong_muon = partner.desires.filtered(lambda pp: pp.type == 'desires')
            dates_desires = sorted((set(mong_muon.mapped('create_on'))), key=lambda x: x)
            for date in dates_desires:
                mong_muon_date = mong_muon.filtered(lambda mm: mm.create_on == date)
                date = date.strftime('%d/%m/%Y')
                list_mong_muon.append({
                    'date': date,
                    'data': mong_muon_date.mapped('name')})
            data['mong_muon'] = list_mong_muon

            ############### Nỗi lo lắng
            list_noi_lo_lang = []
            # noi_lo_lang = partner.persona.filtered(lambda p: p.type == '2')
            noi_lo_lang = partner.pain_point.filtered(lambda pp: pp.type == 'pain_point')
            dates_pain_point = sorted((set(noi_lo_lang.mapped('create_on'))), key=lambda x: x)
            for date in dates_pain_point:
                noi_lo_lang_date = noi_lo_lang.filtered(lambda mm: mm.create_on == date)
                date = date.strftime('%d/%m/%Y')
                list_noi_lo_lang.append({
                    'date': date,
                    'data': noi_lo_lang_date.mapped('name')})
            data['noi_lo_lang'] = list_noi_lo_lang

            ######## Tính cách
            list_tinh_cach = []
            tinh_cach = partner.persona.filtered(lambda p: p.type == '3')
            dates_3 = sorted((set(tinh_cach.mapped('create_on'))), key=lambda x: x)
            for date in dates_3:
                tinh_cach_date = tinh_cach.filtered(lambda mm: mm.create_on == date)
                date = date.strftime('%d/%m/%Y')
                list_tinh_cach.append({
                    'date': date,
                    'data': tinh_cach_date.mapped('description')})
            data['tinh_cach'] = list_tinh_cach

            ######## Gia đình
            list_gia_dinh = []
            gia_dinh = partner.persona.filtered(lambda p: p.type == '4')
            dates_4 = sorted((set(gia_dinh.mapped('create_on'))), key=lambda x: x)
            for date in dates_4:
                gia_dinh_date = gia_dinh.filtered(lambda mm: mm.create_on == date)
                date = date.strftime('%d/%m/%Y')
                list_gia_dinh.append({
                    'date': date,
                    'data': gia_dinh_date.mapped('description')})
            data['gia_dinh'] = list_gia_dinh

            ######## Tài chính
            list_tai_chinh = []
            tai_chinh = partner.persona.filtered(lambda p: p.type == '5')
            dates_5 = sorted((set(tai_chinh.mapped('create_on'))), key=lambda x: x)
            for date in dates_5:
                tai_chinh_date = tai_chinh.filtered(lambda mm: mm.create_on == date)
                date = date.strftime('%d/%m/%Y')
                list_tai_chinh.append({
                    'date': date,
                    'data': tai_chinh_date.mapped('description')})
            data['tai_chinh'] = list_tai_chinh

            ######## Sở thích
            list_so_thich = []
            so_thich = partner.persona.filtered(lambda p: p.type == '6')
            dates_6 = sorted((set(so_thich.mapped('create_on'))), key=lambda x: x)
            for date in dates_6:
                so_thich_date = so_thich.filtered(lambda mm: mm.create_on == date)
                date = date.strftime('%d/%m/%Y')
                list_so_thich.append({
                    'date': date,
                    'data': so_thich_date.mapped('description')})
            data['so_thich'] = list_so_thich

            ######## Mục tiêu
            list_muc_tieu = []
            muc_tieu = partner.persona.filtered(lambda p: p.type == '7')
            dates_7 = sorted((set(muc_tieu.mapped('create_on'))), key=lambda x: x)
            for date in dates_7:
                muc_tieu_date = muc_tieu.filtered(lambda mm: mm.create_on == date)
                date = date.strftime('%d/%m/%Y')
                list_muc_tieu.append({
                    'date': date,
                    'data': muc_tieu_date.mapped('description')})
            data['muc_tieu'] = list_muc_tieu

            ######## Thương hiệu
            list_thuong_hieu = []
            thuong_hieu = partner.persona.filtered(lambda p: p.type == '8')
            dates_8 = sorted((set(thuong_hieu.mapped('create_on'))), key=lambda x: x)
            for date in dates_8:
                thuong_hieu_date = thuong_hieu.filtered(lambda mm: mm.create_on == date)
                date = date.strftime('%d/%m/%Y')
                list_thuong_hieu.append({
                    'date': date,
                    'data': thuong_hieu_date.mapped('description')})
            data['thuong_hieu'] = list_thuong_hieu

            ######## Ảnh hương bởi
            list_anh_huong = []
            anh_huong = partner.persona.filtered(lambda p: p.type == '9')
            dates_9 = sorted((set(anh_huong.mapped('create_on'))), key=lambda x: x)
            for date in dates_9:
                anh_huong_date = anh_huong.filtered(lambda mm: mm.create_on == date)
                date = date.strftime('%d/%m/%Y')
                list_anh_huong.append({
                    'date': date,
                    'data': anh_huong_date.mapped('description')})
            data['anh_huong'] = list_anh_huong

            ######## Hành vi trên Internet
            list_hanh_vi = []
            hanh_vi = partner.persona.filtered(lambda p: p.type == '10')
            dates_10 = sorted((set(hanh_vi.mapped('create_on'))), key=lambda x: x)
            for date in dates_10:
                hanh_vi_date = hanh_vi.filtered(lambda mm: mm.create_on == date)
                date = date.strftime('%d/%m/%Y')
                list_hanh_vi.append({
                    'date': date,
                    'data': hanh_vi_date.mapped('description')})
            data['hanh_vi'] = list_hanh_vi

            ######## Hoạt động hàng ngày
            list_hoat_dong = []
            hoat_dong = partner.persona.filtered(lambda p: p.type == '11')
            dates_11 = sorted((set(hoat_dong.mapped('create_on'))), key=lambda x: x)
            for date in dates_11:
                hoat_dong_date = hoat_dong.filtered(lambda mm: mm.create_on == date)
                date = date.strftime('%d/%m/%Y')
                list_hoat_dong.append({
                    'date': date,
                    'data': hoat_dong_date.mapped('description')})
            data['hoat_dong'] = list_hoat_dong

            ######## Thông tin khác
            list_other = []
            other = partner.persona.filtered(lambda p: p.type == '12')
            dates_12 = sorted((set(other.mapped('create_on'))), key=lambda x: x)
            for date in dates_12:
                other_date = other.filtered(lambda mm: mm.create_on == date)
                date = date.strftime('%d/%m/%Y')
                list_other.append({
                    'date': date,
                    'data': other_date.mapped('description')})
            data['other'] = list_other

            ####### LỊCH SỬ PHẢN ÁNH
            list_phan_anh = []
            cases = request.env['crm.case'].sudo().search([('partner_id', '=', partner.id)], order="create_date desc")
            if cases:
                for case in cases:
                    for content in case.crm_content_complain:
                        list_phan_anh.append({
                            'date': content.create_date.strftime('%d/%m/%Y'),
                            'service': ', '.join(content.complain_service_ids.product_id.mapped('name')),
                            'noi_dung': content.desc if content.desc else '',
                            'giai_phap': content.solution if content.solution else '',
                            'state': stage_case[content.stage]
                        })
            data['list_phan_anh'] = list_phan_anh

            ####### LỊCH SỬ TÁI KHÁM
            list_tai_kham = []
            patient = request.env['sh.medical.patient'].sudo().search([('partner_id', '=', partner.id)], order="evaluation_start_date desc")
            if patient:
                evaluations = request.env['sh.medical.evaluation'].sudo().search(
                    [('patient', '=', patient.id)])
                if evaluations:
                    for evaluation in evaluations:
                        list_tai_kham.append({
                            'date': evaluation.evaluation_start_date.strftime('%d/%m/%Y'),
                            'service': ', '.join(evaluation.services.mapped('name')),
                            'doctor': evaluation.doctor.name if evaluation.doctor else '',
                            'note': evaluation.notes_complaint if evaluation.notes_complaint else '',
                            'next_stage': evaluation.directions if evaluation.directions else ''
                        })
            data['list_tai_kham'] = list_tai_kham
        _logger.info(data)
        if data:
            return json.dumps({
                'status': 0,
                'massage': "Success",
                'data': data
            })
        else:
            return json.dumps({
                'status': 1,
                'message': 'Không tìm thấy thông tin'
            })

    @http.route("/api/connect-customer-persona/history-medical-exam", type="http", auth="none",
                methods=["GET"], csrf=False, cors='*')
    def history_medical_exam(self, **payload):
        """ Lấy thông tin thăm khám qua tên type và id phiếu"""
        # body = json.loads(request.httprequest.data.decode('utf-8'))
        body = payload
        for key in ['type', 'erp_id']:
            if key not in body.keys():
                return json.dumps({
                    'status': 1,
                    'message': "The parameter %s is missing! " % key
                })
        data = {}
        if body['type'] and body['erp_id']:
            type = body['type']
            erp_id = int(body['erp_id'])
            if type == 'walkin':
                walkin = request.env['sh.medical.appointment.register.walkin'].sudo().browse(int(erp_id))
                if walkin:
                    data.update({
                        'date': walkin.service_date_start.strftime('%d-%m-%Y') if walkin.service_date_start else '',
                        'reason_check': walkin.reason_check or 'Chưa có thông tin',
                        'doctor': walkin.doctor.name or 'Chưa có thông tin',
                        'reception_nurse': walkin.reception_nurse.name or 'Chưa có thông tin',
                        'service': ', '.join(walkin.service.mapped('name')),
                        'booking': walkin.booking_id.name,
                        'name': walkin.name,
                        'institution': walkin.institution.name,
                        'service_room': walkin.service_room.name
                    })
            elif type == 'evaluation':
                evaluation = request.env['sh.medical.evaluation'].sudo().browse(int(erp_id))
                if evaluation:
                    data.update({
                        'date': evaluation.evaluation_start_date.strftime('%d-%m-%Y') or 'Chưa có thông tin',
                        'reason_check': evaluation.info_diagnosis or evaluation.notes_complaint or 'Chưa có thông tin',
                        'doctor': evaluation.doctor.name or 'Chưa có thông tin',
                        # 'reception_nurse': walkin.reception_nurse.name,
                        'service': ', '.join(evaluation.services.mapped('name')),
                        'booking': evaluation.walkin.booking_id.name or False,
                        'name': evaluation.name,
                        'institution': evaluation.institution.name,
                        'service_room': evaluation.room.name
                    })
            else:
                return json.dumps({
                    'status': 1,
                    'message': 'Không xác định được tham số type truyền vào'
                })
        if data:
            return json.dumps({
                'status': 0,
                'massage': "Success",
                'data': data
            })
        else:
            return json.dumps({
                'status': 1,
                'message': 'Không tìm thấy thông tin'
            })
