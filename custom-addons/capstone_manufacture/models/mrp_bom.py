from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class MrpBom(models.Model):
    _inherit = 'mrp.bom'

    capstone_produce_to_location = fields.Boolean(
        string='Produce to a Different Location', default=False,
    )
    capstone_finished_location_id = fields.Many2one(
        'stock.location', string='Finished Products Location', check_company=True,
        help='Default output destination for new manufacturing orders using this BoM. '
             'Component locations are unchanged.',
    )
    capstone_warehouse_root_id = fields.Many2one(
        related='picking_type_id.warehouse_id.view_location_id',
    )

    @api.constrains('capstone_produce_to_location', 'capstone_finished_location_id',
                    'picking_type_id', 'company_id', 'type')
    def _check_capstone_finished_location(self):
        for bom in self.filtered('capstone_produce_to_location'):
            warehouse = bom.picking_type_id.warehouse_id
            location = bom.capstone_finished_location_id
            if bom.type != 'normal':
                raise ValidationError(_('Output location overrides require a Manufacture this Product BoM.'))
            if not warehouse or not location:
                raise ValidationError(_('Select a manufacturing operation type with a warehouse and a finished products location.'))
            if (location.usage != 'internal' or not location.active
                    or location.company_id != warehouse.company_id
                    or not location.parent_path.startswith(warehouse.view_location_id.parent_path)):
                raise ValidationError(_('The finished products location must be an active internal location in the operation type warehouse and company.'))
