from odoo import http
from odoo.http import request

class ComplaintController(http.Controller):

    @http.route('/complaint/register', type='http', auth='public', website=True, csrf=False)
    def complaint_form(self, **kwargs):
        shops = request.env['res.partner'].sudo().search([('is_company', '=', True)])
        products = request.env['product.product'].sudo().search([])
        return request.render('capstone_complaint_management.template_complaint_form', {
            'shops': shops,
            'products': products,
        })

    @http.route('/complaint/submit', type='http', auth='public', website=True, csrf=False)
    def complaint_submit(self, **post):
        partner = request.env['res.partner'].sudo().create({
            'name': post.get('customer_name'),
            'email': post.get('customer_email'),
            'phone': post.get('customer_phone')
        })

        complaint = request.env['complaint.management'].sudo().create({
            'customer_id': partner.id,
            'purchased_shop_id': int(post.get('shop_id')),
            'description': post.get('description'),
            'product_line_ids': [(0, 0, {
                'product_id': int(post.get('product_id')),
                'quantity': 1.0
            })],
        })

        return request.render('capstone_complaint_management.template_complaint_thankyou', {'complaint': complaint})
