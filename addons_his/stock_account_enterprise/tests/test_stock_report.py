# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import common


class TestStockReport(common.TransactionCase):
    def setUp(self):
        super(TestStockReport, self).setUp()

        products = self.env['product.product'].search([('product_tmpl_id.type', '=', 'product')])
        moves = self.env['stock.move'].search([('company_id', '=', self.env.companies.ids[0])])
        for move in moves:
            if move._is_in():
                move._create_in_svl()
            elif move._is_out():
                move._create_out_svl()

        self.inventory_valuation = sum(product.value_svl for product in products)
        self.total_move_valuation = sum(moves.mapped('stock_valuation_layer_ids.value'))
        incoming_moves = self.env['stock.move'].search([('picking_id.picking_type_id.code', '=', 'incoming')])
        self.incoming_move_valuation = sum(incoming_moves.mapped('stock_valuation_layer_ids.value'))

    def test_valuation(self):
        # without domain
        value = self.env['stock.report'].with_context(debug=True).read_group([], ['valuation:sum(valuation)'], '')

        self.assertEqual(value[0]['valuation'], self.total_move_valuation,
                         "Calling read group with valuation and without domain should give the total move valuation of the inventory")

        # with domain
        value = self.env['stock.report'].read_group([('picking_type_code', '=', 'incoming')], ['valuation:sum(valuation)'], '')

        self.assertEqual(value[0]['valuation'], self.incoming_move_valuation,
                         "Calling read group with valuation and with domain should give the move valuation for this domain")

        # Doesn't support group by
        with self.assertRaises(UserError):
            value = self.env['stock.report'].read_group([('picking_type_code', '=', 'incoming')], ['valuation:sum(valuation)'], 'state')

        # Only support sum operator
        with self.assertRaises(UserError):
            value = self.env['stock.report'].read_group([('picking_type_code', '=', 'incoming')], ['valuation:avg(valuation)'], '')

    def test_stock_value(self):
        def get_test_date():
            return fields.Datetime.to_string(fields.Datetime.from_string(fields.Datetime.now()) - timedelta(days=5))

        # without domain
        value = self.env['stock.report'].read_group([], ['stock_value:sum(stock_value)'], '')

        self.assertEqual(value[0]['stock_value'], self.inventory_valuation,
                         "Calling read group with stock_value should give the total inventory value to this date")

        # Takes date_done into account when in domain but doesn't care about the operator
        value = self.env['stock.report'].read_group([('date_done', '=', get_test_date())], ['stock_value:sum(stock_value)'], '')

        self.assertEqual(value[0]['stock_value'], self.inventory_valuation,
                         "Read group on stock_value should not take date_done into account in domain")

        value = self.env['stock.report'].read_group([('date_done', '<', get_test_date())], ['stock_value:sum(stock_value)'], '')

        self.assertEqual(value[0]['stock_value'], self.inventory_valuation,
                         "Read group on stock_value should note take date_done into account in domain")

        # with domain should be the same value
        value = self.env['stock.report'].read_group([('picking_type_code', '=', 'incoming')], ['stock_value:sum(stock_value)'], '')

        self.assertEqual(value[0]['stock_value'], self.inventory_valuation,
                         "Read group on stock_value should ignore domain")

        # Doesn't support group by
        with self.assertRaises(UserError):
            value = self.env['stock.report'].read_group([], ['stock_value:sum(stock_value)'], 'state')

        # Only support sum operator
        with self.assertRaises(UserError):
            value = self.env['stock.report'].read_group([], ['stock_value:avg(stock_value)'], '')
