from odoo import http
from odoo.http import request
import base64

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
        files = request.httprequest.files

        image_1_file = files.get('image_1')
        image_2_file = files.get('image_2')
        print(image_1_file,'______________________')

        image_1 = False
        image_2 = False

        if image_1_file:
            image_1 = base64.b64encode(image_1_file.read())

        if image_2_file:
            image_2 = base64.b64encode(image_2_file.read())

        partner = request.env['res.partner'].sudo().create({
            'name': post.get('customer_name'),
            'email': post.get('customer_email'),
            'phone': post.get('customer_phone')
        })

        complaint = request.env['complaint.management'].sudo().create({
            'customer_id': partner.id,
            'purchased_shop_id': int(post.get('shop_id')),
            'description': post.get('description'),
            'image_1': image_1,
            'image_2': image_2,
            'product_line_ids': [(0, 0, {
                'product_id': int(post.get('product_id')),
                'quantity': 1.0
            })],
        })

        return request.render('capstone_complaint_management.template_complaint_thankyou', {'complaint': complaint})
