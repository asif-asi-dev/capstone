from odoo import models, fields

class ReturnReason(models.Model):
    _name = 'return.reason'
    _description = 'Return Reason'
    _order = 'name'

    name = fields.Char(
        string='Reason',
        required=True
    )

class InspectionResult(models.Model):
    _name = 'inspection.result'
    _description = 'Inspection Result'
    _order = 'name'

    name = fields.Char(
        string='Inspection Result',
        required=True
    )
    location_dest_id = fields.Many2one(
        'stock.location',
        string="Destination Location",
        help="Location to which the product is moved."
    )
