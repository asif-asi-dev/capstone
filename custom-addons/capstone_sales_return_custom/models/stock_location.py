import logging
from odoo import api, fields, models,_
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class StockLocation(models.Model):
    _inherit = "stock.location"

    is_scrap_location = fields.Boolean(string="Is Scrap Location")
    is_scrap_dump_location = fields.Boolean(string="Is Scrap Dump Location")
    is_recyclable_location = fields.Boolean(string="Is Recyclable Location")
    is_manufacturing_defect_location = fields.Boolean(string="Is Manufacturing Defect Location")
    is_virtual_return_location = fields.Boolean(string="Is Virtual Return Location")
    is_discount_sale_location = fields.Boolean(string="Is Discount Sale Location")
    is_no_complaint_with_dump_location = fields.Boolean(string="Is No Complaint With Dump Location")

class StockWarehouse(models.Model):
    _inherit = "stock.warehouse"

    @api.model
    def create(self, vals):
        warehouse = super(StockWarehouse, self).create(vals)
        warehouse._create_special_locations()
        return warehouse

    def _create_special_locations(self):
        """Create special locations for scrap, scrap dump, recyclable, and manufacturing defect
        only if warehouse booleans are enabled and locations don't already exist.
        """
        Location = self.env['stock.location']

        for warehouse in self:

            if not Location.search([
                ('is_no_complaint_with_dump_location', '=', True),
                ('location_id', '=', warehouse.view_location_id.id),
                ('company_id', '=', warehouse.company_id.id)
            ], limit=1):
                Location.create({
                    'name': _('No Complaint With Dump Location'),
                    'usage': 'internal',
                    'location_id': warehouse.view_location_id.id,
                    'company_id': warehouse.company_id.id,
                    'is_no_complaint_with_dump_location': True,
                })

            if not Location.search([
                ('is_discount_sale_location', '=', True),
                ('location_id', '=', warehouse.view_location_id.id),
                ('company_id', '=', warehouse.company_id.id)
            ], limit=1):
                Location.create({
                    'name': _('Discount Sale Location'),
                    'usage': 'internal',
                    'location_id': warehouse.view_location_id.id,
                    'company_id': warehouse.company_id.id,
                    'is_discount_sale_location': True,
                })
            # Virtual Return Location
            if not Location.search([
                ('is_virtual_return_location', '=', True),
                ('location_id', '=', warehouse.view_location_id.id),
                ('company_id', '=', warehouse.company_id.id)
            ], limit=1):
                Location.create({
                    'name': _('Virtual Sales Return Location'),
                    'usage': 'internal',
                    'location_id': warehouse.view_location_id.id,
                    'company_id': warehouse.company_id.id,
                    'is_virtual_return_location': True,
                })
            # Scrap Location
            if not Location.search([
                ('is_scrap_location', '=', True),
                ('location_id', '=', warehouse.view_location_id.id),
                ('company_id', '=', warehouse.company_id.id)
            ], limit=1):
                Location.create({
                    'name': _('Scrap Location'),
                    'usage': 'inventory',
                    'location_id': warehouse.view_location_id.id,
                    'company_id': warehouse.company_id.id,
                    'is_scrap_location': True,
                })

            # Scrap Dump Location
            if not Location.search([
                ('is_scrap_dump_location', '=', True),
                ('location_id', '=', warehouse.view_location_id.id),
                ('company_id', '=', warehouse.company_id.id)
            ], limit=1):
                Location.create({
                    'name': _('Scrap Dump Location'),
                    'usage': 'inventory',
                    'location_id': warehouse.view_location_id.id,
                    'company_id': warehouse.company_id.id,
                    'is_scrap_dump_location': True,
                })

            # Recyclable Location
            if not Location.search([
                ('is_recyclable_location', '=', True),
                ('location_id', '=', warehouse.view_location_id.id),
                ('company_id', '=', warehouse.company_id.id)
            ], limit=1):
                Location.create({
                    'name': _('Recyclable Location'),
                    'usage': 'production',
                    'location_id': warehouse.view_location_id.id,
                    'company_id': warehouse.company_id.id,
                    'is_recyclable_location': True,
                })

            # Manufacturing Defect Location
            if not Location.search([
                ('is_manufacturing_defect_location', '=', True),
                ('location_id', '=', warehouse.view_location_id.id),
                ('company_id', '=', warehouse.company_id.id)
            ], limit=1):
                Location.create({
                    'name': _('Manufacturing Defect Location'),
                    'usage': 'production',
                    'location_id': warehouse.view_location_id.id,
                    'company_id': warehouse.company_id.id,
                    'is_manufacturing_defect_location': True,
                })
