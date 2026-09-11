from odoo import _, api, models
from odoo.exceptions import ValidationError


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    # Do not depend on editable BoM destination fields: changing the recipe's
    # default must not silently redirect existing production orders.
    @api.depends('picking_type_id', 'bom_id', 'company_id')
    def _compute_locations(self):
        super()._compute_locations()
        for mo in self:
            if mo.bom_id.capstone_produce_to_location:
                mo.bom_id._check_capstone_finished_location()
                if mo.bom_id.picking_type_id.warehouse_id != mo.picking_type_id.warehouse_id:
                    raise ValidationError(_('The BoM output location belongs to a different manufacturing warehouse.'))
                mo.location_dest_id = mo.bom_id.capstone_finished_location_id
