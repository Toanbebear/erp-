{
    'name': 'CRM Sale Payment',
    'version': '1.0',
    'category': 'Sales/CRM',
    'author': 'Hoang NV',
    'sequence': '11',
    'summary': 'Sale Payment',
    'depends': [
        'crm',
        'crm_base',
        'crm_booking_order',
        'tas_payment',
        # 'sci_payment_list',
        # 'sale_management',
        'sale_crm',
        'account',
        'stock',
        # 'sh_message',
        # 'sci_brand'
        'crm_voucher'
    ],
    'data': [
        # 'security/payment_security.xml',
        'views/account_payment.xml',
        'views/account_payment_detail.xml',
        'views/crm_sale_payment_view.xml',
        'views/crm_sale_payment_local_view.xml',
        'views/crm_sale_payment_plan_view.xml',
        'views/crm_transfer_payment_view.xml',
        'views/payment_list_detail.xml',
        'views/view_booking.xml',
        'views/product.xml',
        'views/assets.xml',
        'wizard/bao_cao_chi_tiet_doanh_so/crm_sale_payment_detail_report_wizard.xml',
        'wizard/bao_cao_chi_tiet_doanh_so_dich_vu/crm_sale_payment_service_report_wizard.xml',
        'wizard/bao_cao_chi_tiet_doanh_so_ngay/crm_sale_payment_day_report_wizard.xml',
        'wizard/bao_cao_chi_tiet_doanh_so_thang/crm_sale_payment_report_wizard.xml',
        'wizard/ta_bao_cao_doanh_so_theo_nguon_online_offline/online_offline_sales_report_wizard.xml',
        'wizard/ta_bao_cao_doanh_so_vuot_tran/over_discount_sales_report_wizard.xml',
        'wizard/ta_bao_cao_doanh_so_theo_nguon/source_sales_report_wizard.xml',
        'wizard/ta_bao_cao_doanh_so_theo_nguon_sp_dv/source_service_product_sales_report_wizard.xml',
        'data/crm_transfer_payment_sequence.xml',
        'data/crm_sale_payment_sequence.xml',
        'data/crm_sale_payment_local_sequence.xml',
        'security/ir.model.access.csv',
        'security/crm_sale_payment_security.xml',
        'views/crm_lead.xml',
        'views/menu.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'qweb': [],
}
