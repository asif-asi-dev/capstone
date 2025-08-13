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

class StockWarehouse(models.Model):
    _inherit = "stock.warehouse"

    @api.model
    def create(self, vals):
        warehouse = super(StockWarehouse, self).create(vals)
        warehouse._create_special_locations()
        return warehouse

    def _create_special_locations(self):
        """Create special locations for scrap, scrap dump, recyclable, and manufacturing defect."""
        Location = self.env['stock.location']

        for warehouse in self:
            # 1. Scrap Location
            Location.create({
                'name': _('Scrap Location'),
                'usage': 'inventory',
                'location_id': warehouse.view_location_id.id,
                'company_id': warehouse.company_id.id,
                'is_scrap_location': True,
            })

            # 2. Scrap Dump Location
            Location.create({
                'name': _('Scrap Dump Location'),
                'usage': 'inventory',
                'location_id': warehouse.view_location_id.id,
                'company_id': warehouse.company_id.id,
                'is_scrap_dump_location': True,
            })

            # 3. Recyclable Location
            Location.create({
                'name': _('Recyclable Location'),
                'usage': 'production',
                'location_id': warehouse.view_location_id.id,
                'company_id': warehouse.company_id.id,
                'is_recyclable_location': True,
            })

            # 4. Manufacturing Defect Location
            Location.create({
                'name': _('Manufacturing Defect Location'),
                'usage': 'production',
                'location_id': warehouse.view_location_id.id,
                'company_id': warehouse.company_id.id,
                'is_manufacturing_defect_location': True,
            })