from odoo import _, api, fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        context = self.env.context
        args = args or []
        if context.get('is_discount_sale') and context.get('warehouse_id'):
            warehouse = self.env['stock.warehouse'].browse(context['warehouse_id'])
            if warehouse and warehouse.discount_location_id:
                discount_location = warehouse.discount_location_id
                quants = self.env['stock.quant'].search([
                    ('location_id', 'child_of', discount_location.id),
                    ('quantity', '>', 0),
                ])
                product_ids = list(set(quants.mapped('product_id.product_tmpl_id').ids))
                if product_ids:
                    args += [('id', 'in', product_ids)]
                else:
                    args += [('id', '=', 0)]

        return super(ProductTemplate, self).name_search(name, args=args, operator=operator, limit=limit)


    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        context = self.env.context
        domain = domain or []
        if context.get('is_discount_sale') and context.get('warehouse_id'):
            warehouse = self.env['stock.warehouse'].browse(context['warehouse_id'])
            if warehouse and warehouse.discount_location_id:
                discount_location = warehouse.discount_location_id

                quants = self.env['stock.quant'].search([
                    ('location_id', 'child_of', discount_location.id),
                    ('quantity', '>', 0),
                ])

                product_ids = list(set(quants.mapped('product_id.product_tmpl_id').ids))

                if product_ids:
                    domain += [('id', 'in', product_ids)]
                else:
                    domain += [('id', '=', 0)]

        return super(ProductTemplate, self).search_read(domain=domain, fields=fields,
                                                        offset=offset, limit=limit, order=order)

