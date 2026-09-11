from odoo import Command
from odoo.exceptions import AccessError, ValidationError
from odoo.tests import TransactionCase, tagged, new_test_user
from datetime import datetime, timedelta


@tagged('post_install', '-at_install')
class TestCapstoneManufacture(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.warehouse = cls.env['stock.warehouse'].search(
            [('company_id', '=', cls.env.company.id)], limit=1)
        cls.destination = cls.env['stock.location'].create({
            'name': 'Finished Taps', 'usage': 'internal',
            'location_id': cls.warehouse.lot_stock_id.id,
            'company_id': cls.env.company.id,
        })
        cls.product = cls.env['product.product'].create({
            'name': 'Test Tap', 'type': 'product',
        })
        cls.component = cls.env['product.product'].create({
            'name': 'Test Body', 'type': 'product',
        })
        cls.operator = new_test_user(cls.env, login='capstone_operator',
                                     groups='mrp.group_mrp_user')
        cls.other = new_test_user(cls.env, login='capstone_other',
                                  groups='mrp.group_mrp_user')
        cls.manager = new_test_user(cls.env, login='capstone_manager',
                                    groups='mrp.group_mrp_manager')
        cls.employee = cls.env['hr.employee'].create({
            'name': 'Assigned Operator', 'user_id': cls.operator.id,
            'company_id': cls.env.company.id,
        })
        cls.center = cls.env['mrp.workcenter'].create({
            'name': 'Grinding', 'company_id': cls.env.company.id,
            'capstone_allowed_employee_ids': [Command.set(cls.employee.ids)],
        })
        cls.closed_center = cls.env['mrp.workcenter'].create({
            'name': 'Unassigned Polishing', 'company_id': cls.env.company.id,
        })
        cls.bom = cls.env['mrp.bom'].create({
            'product_tmpl_id': cls.product.product_tmpl_id.id,
            'company_id': cls.env.company.id,
            'picking_type_id': cls.warehouse.manu_type_id.id,
            'bom_line_ids': [Command.create({
                'product_id': cls.component.id, 'product_qty': 1,
            })],
            'operation_ids': [Command.create({
                'name': 'Grinding', 'workcenter_id': cls.center.id,
                'time_cycle_manual': 4,
            })],
        })

    def _mo(self, **values):
        return self.env['mrp.production'].create({
            'product_id': self.product.id, 'product_qty': 1,
            'bom_id': self.bom.id,
            'picking_type_id': self.warehouse.manu_type_id.id,
            **values,
        })

    def _enable_destination(self):
        self.bom.write({
            'capstone_produce_to_location': True,
            'capstone_finished_location_id': self.destination.id,
        })

    def test_default_destination(self):
        mo = self._mo()
        self.assertEqual(mo.location_dest_id, self.warehouse.manu_type_id.default_location_dest_id)
        self.assertEqual(mo.location_src_id, self.warehouse.manu_type_id.default_location_src_id)

    def test_destination_moves_and_completed_inventory(self):
        self._enable_destination()
        self.env['stock.quant']._update_available_quantity(
            self.component, self.warehouse.lot_stock_id, 1)
        mo = self._mo()
        mo.action_confirm()
        self.assertEqual(mo.location_dest_id, self.destination)
        self.assertEqual(mo.move_finished_ids.location_dest_id, self.destination)
        self.assertEqual(mo.move_raw_ids.location_id, self.warehouse.lot_stock_id)
        mo.qty_producing = 1
        mo._set_qty_producing()
        mo.move_raw_ids.quantity = 1
        mo.move_raw_ids.picked = True
        mo.workorder_ids.button_finish()
        mo.button_mark_done()
        self.assertEqual(mo.state, 'done')
        self.assertEqual(self.env['stock.quant']._get_available_quantity(
            self.product, self.destination), 1)

    def test_bom_edit_and_reselection(self):
        mo = self._mo()
        self._enable_destination()
        # Existing MOs retain their destination after a recipe edit.
        self.assertEqual(mo.location_dest_id, self.warehouse.manu_type_id.default_location_dest_id)
        mo.bom_id = False
        mo.bom_id = self.bom
        self.assertEqual(mo.location_dest_id, self.destination)
        self.assertEqual(mo.location_src_id, self.warehouse.manu_type_id.default_location_src_id)

    def test_explicit_component_location_is_respected_on_creation(self):
        self._enable_destination()
        mo = self._mo(location_src_id=self.destination.id)
        self.assertEqual(mo.location_src_id, self.destination)
        self.assertEqual(mo.location_dest_id, self.destination)

    def test_explicit_mo_destination_is_respected(self):
        self._enable_destination()
        mo = self._mo(location_dest_id=self.warehouse.lot_stock_id.id)
        self.assertEqual(mo.location_dest_id, self.warehouse.lot_stock_id)

    def test_missing_destination_rejected(self):
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self.bom.capstone_produce_to_location = True

    def test_other_warehouse_rejected(self):
        warehouse = self.env['stock.warehouse'].create({
            'name': 'Other Warehouse', 'code': 'COTH',
            'company_id': self.env.company.id,
        })
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self.bom.write({
                'capstone_produce_to_location': True,
                'capstone_finished_location_id': warehouse.lot_stock_id.id,
            })

    def test_non_internal_destination_rejected(self):
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self.bom.write({
                'capstone_produce_to_location': True,
                'capstone_finished_location_id': self.warehouse.view_location_id.id,
            })

    def test_assigned_workcenter_visibility(self):
        centers = self.env['mrp.workcenter'].with_user(self.operator).search([])
        self.assertIn(self.center, centers)
        self.assertNotIn(self.closed_center, centers)
        self.assertNotIn(self.center, self.env['mrp.workcenter'].with_user(self.other).search([]))
        self.assertIn(self.closed_center, self.env['mrp.workcenter'].with_user(self.manager).search([]))

    def test_workorder_access_and_reassignment(self):
        mo = self._mo()
        mo.action_confirm()
        wo = mo.workorder_ids
        wo.with_user(self.operator).read(['name'])
        with self.assertRaises(AccessError):
            wo.with_user(self.other).read(['name'])
        with self.assertRaises(AccessError), self.cr.savepoint():
            wo.with_user(self.other).write({'name': 'Forbidden'})
        with self.assertRaises(AccessError), self.cr.savepoint():
            wo.with_user(self.operator).write({'workcenter_id': self.closed_center.id})
        wo.with_user(self.operator).button_start()
        self.assertEqual(wo.state, 'progress')
        wo.with_user(self.operator).button_finish()
        self.assertEqual(wo.state, 'done')

    def test_operator_cannot_assign_employees(self):
        with self.assertRaises(AccessError), self.cr.savepoint():
            self.center.with_user(self.operator).write({
                'capstone_allowed_employee_ids': [Command.clear()],
            })

    def test_employee_archive_revokes_access(self):
        self.employee.active = False
        self.assertNotIn(self.center, self.env['mrp.workcenter'].with_user(self.operator).search([]))

    def test_employee_user_change_updates_access(self):
        self.employee.user_id = self.other
        self.assertNotIn(self.center, self.env['mrp.workcenter'].with_user(self.operator).search([]))
        self.assertIn(self.center, self.env['mrp.workcenter'].with_user(self.other).search([]))

    def _cost_mo(self, method='piece', basis='processed', rate=12, quantity=10):
        self.bom.operation_ids.write({
            'capstone_cost_method': method, 'capstone_cost_rate': rate,
            'capstone_quantity_basis': basis,
        })
        self.center.costs_hour = 180
        self.component.standard_price = 335
        category = self.env['product.category'].create({
            'name': 'AVCO Taps', 'property_cost_method': 'average',
        })
        self.product.categ_id = category
        mo = self._mo(product_qty=quantity)
        mo.action_confirm()
        return mo

    def _complete_cost_mo(self, mo, good=8, consumed=10):
        self.env['stock.quant']._update_available_quantity(self.component, mo.location_src_id, consumed)
        mo.qty_producing = good
        mo._set_qty_producing()
        mo.move_raw_ids.quantity = consumed
        mo.move_raw_ids.picked = True
        mo.workorder_ids.button_finish()
        mo.with_context(skip_consumption=True, skip_backorder=True).button_mark_done()
        self.assertEqual(mo.state, 'done')

    def test_piece_processed_inventory_cost_and_report(self):
        mo = self._cost_mo()
        wo = mo.workorder_ids
        wo.write({'capstone_charge_quantity': 10, 'capstone_charge_confirmed': True})
        self._complete_cost_mo(mo)
        self.assertAlmostEqual(wo._cal_cost(), 120)
        self.assertAlmostEqual(self.product.standard_price, 433.75)
        value = sum(mo.move_finished_ids.stock_valuation_layer_ids.mapped('value'))
        self.assertAlmostEqual(value, 3470)
        report = self.env['report.mrp.report_mo_overview']._get_operations_data(mo)
        self.assertAlmostEqual(report['summary']['real_cost'], 120)
        self.assertAlmostEqual(report['details'][0]['quantity'], 10)

    def test_piece_good_output_inventory_cost(self):
        mo = self._cost_mo(basis='good')
        self._complete_cost_mo(mo)
        self.assertAlmostEqual(mo.workorder_ids._cal_cost(), 96)
        self.assertAlmostEqual(self.product.standard_price, 430.75)

    def test_batch_inventory_cost(self):
        mo = self._cost_mo(method='batch', rate=150)
        mo.workorder_ids.capstone_charge_confirmed = True
        self._complete_cost_mo(mo)
        self.assertAlmostEqual(mo.workorder_ids._cal_cost(), 150)
        self.assertAlmostEqual(self.product.standard_price, 437.50)

    def test_charge_confirmation_required(self):
        mo = self._cost_mo()
        with self.assertRaises(ValidationError), self.cr.savepoint():
            mo.workorder_ids.button_finish()
        mo.workorder_ids.write({'capstone_charge_quantity': 10, 'capstone_charge_confirmed': True})
        mo.workorder_ids.capstone_charge_quantity = 9
        self.assertFalse(mo.workorder_ids.capstone_charge_confirmed)

    def test_cost_snapshot_and_operator_rate_security(self):
        mo = self._cost_mo()
        self.bom.operation_ids.capstone_cost_rate = 99
        self.assertEqual(mo.workorder_ids.capstone_cost_rate, 12)
        with self.assertRaises(AccessError), self.cr.savepoint():
            mo.workorder_ids.with_user(self.operator).capstone_cost_rate = 1
        mo.workorder_ids.with_user(self.operator).write({
            'capstone_charge_quantity': 10, 'capstone_charge_confirmed': True})

    def test_closed_cost_cannot_be_edited(self):
        mo = self._cost_mo(basis='good')
        self._complete_cost_mo(mo)
        with self.assertRaises(ValidationError), self.cr.savepoint():
            mo.workorder_ids.capstone_cost_rate = 1

    def test_negative_rates_and_quantities_rejected(self):
        mo = self._cost_mo()
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self.bom.operation_ids.capstone_cost_rate = -1
        with self.assertRaises(ValidationError), self.cr.savepoint():
            mo.workorder_ids.capstone_charge_quantity = -1

    def test_bom_price_and_overview_piece(self):
        self._cost_mo()
        self.assertAlmostEqual(self.product._compute_bom_price(self.bom), 347)
        lines = self.env['report.mrp.report_bom_structure']._get_operation_line(self.product, self.bom, 10, 0, '')
        self.assertAlmostEqual(lines[0]['bom_cost'], 120)

    def test_bom_price_and_overview_batch(self):
        self._cost_mo(method='batch', rate=150)
        self.bom.product_qty = 10
        self.bom.bom_line_ids.product_qty = 10
        self.assertAlmostEqual(self.product._compute_bom_price(self.bom), 350)
        lines = self.env['report.mrp.report_bom_structure']._get_operation_line(self.product, self.bom, 25, 0, '')
        self.assertAlmostEqual(lines[0]['bom_cost'], 150)

    def test_split_does_not_duplicate_batch_fee(self):
        mo = self._cost_mo(method='batch', rate=150)
        mo.workorder_ids.capstone_charge_confirmed = True
        orders = mo._split_productions({mo: [8, 2]})
        backorder = orders - mo
        self.assertTrue(mo.workorder_ids.capstone_charge_batch)
        self.assertFalse(backorder.workorder_ids.capstone_charge_batch)
        self.assertFalse(backorder.workorder_ids.capstone_charge_confirmed)
        self.assertEqual(backorder.workorder_ids.capstone_cost_rate, 150)
        with self.assertRaises(ValidationError), self.cr.savepoint():
            backorder.workorder_ids.button_finish()

    def test_hourly_cost_remains_time_based(self):
        mo = self._cost_mo(method='hourly')
        wo = mo.workorder_ids
        loss = self.env['mrp.workcenter.productivity.loss'].search([('loss_type', '=', 'productive')], limit=1)
        start = datetime(2026, 1, 1, 9)
        self.env['mrp.workcenter.productivity'].create({
            'workorder_id': wo.id, 'workcenter_id': self.center.id,
            'loss_id': loss.id, 'date_start': start, 'date_end': start + timedelta(minutes=40),
        })
        self.assertAlmostEqual(wo._cal_cost(), 120)

    def test_custom_cost_analytic_amount(self):
        mo = self._cost_mo()
        plan = self.env['account.analytic.plan'].create({'name': 'Manufacturing Test'})
        account = self.env['account.analytic.account'].create({'name': 'Grinding Cost', 'plan_id': plan.id})
        mo.analytic_distribution = {str(account.id): 100}
        mo.workorder_ids.write({'capstone_charge_quantity': 10, 'capstone_charge_confirmed': True})
        self.assertAlmostEqual(sum(mo.workorder_ids.mo_analytic_account_line_ids.mapped('amount')), -120)

    def test_byproduct_share_in_estimate_and_valuation(self):
        mo = self._cost_mo()
        recovered = self.env['product.product'].create({
            'name': 'Recovered Alloy', 'type': 'product', 'categ_id': self.product.categ_id.id,
        })
        self.bom.byproduct_ids = [Command.create({
            'product_id': recovered.id, 'product_qty': 1, 'cost_share': 10,
            'product_uom_id': recovered.uom_id.id,
        })]
        self.assertAlmostEqual(self.product._compute_bom_price(self.bom), 312.3)
        self.assertAlmostEqual(recovered._compute_bom_price(self.bom, byproduct_bom=True), 34.7)
        # Create a fresh MO so its by-product moves reflect the updated recipe.
        mo = self._mo(product_qty=10)
        mo.action_confirm()
        mo.workorder_ids.write({'capstone_charge_quantity': 10, 'capstone_charge_confirmed': True})
        self.env['stock.quant']._update_available_quantity(self.component, mo.location_src_id, 10)
        mo.qty_producing = 8
        mo._set_qty_producing()
        mo.move_raw_ids.quantity = 10
        mo.move_raw_ids.picked = True
        mo.move_byproduct_ids.quantity = 1
        mo.move_byproduct_ids.picked = True
        mo.workorder_ids.button_finish()
        mo.with_context(skip_consumption=True, skip_backorder=True).button_mark_done()
        main_move = mo.move_finished_ids.filtered(lambda move: move.product_id == self.product)
        self.assertAlmostEqual(sum(main_move.stock_valuation_layer_ids.mapped('value')), 3123)
        self.assertAlmostEqual(sum(mo.move_byproduct_ids.stock_valuation_layer_ids.mapped('value')), 347)
