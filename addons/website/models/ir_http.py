# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
from lxml import etree
import os
import unittest

import pytz
import werkzeug
import werkzeug.routing
import werkzeug.utils

from functools import partial

import odoo
from odoo import api, models
from odoo import SUPERUSER_ID
from odoo.http import request
from odoo.tools.safe_eval import safe_eval
from odoo.osv.expression import FALSE_DOMAIN, OR

from odoo.addons.http_routing.models.ir_http import ModelConverter, _guess_mimetype
from odoo.addons.portal.controllers.portal import _build_url_w_params

logger = logging.getLogger(__name__)


def sitemap_qs2dom(qs, route, field='name'):
    """ Convert a query_string (can contains a path) to a domain"""
    dom = []
    if qs and qs.lower() not in route:
        needles = qs.strip('/').split('/')
        # needles will be altered and keep only element which one is not in route
        # diff(from=['shop', 'product'], to=['shop', 'product', 'product']) => to=['product']
        unittest.util.unorderable_list_difference(route.strip('/').split('/'), needles)
        if len(needles) == 1:
            dom = [(field, 'ilike', needles[0])]
        else:
            dom = FALSE_DOMAIN
    return dom


def get_request_website():
    """ Return the website set on `request` if called in a frontend context
    (website=True on route).
    This method can typically be used to check if we are in the frontend.

    This method is easy to mock during python tests to simulate frontend
    context, rather than mocking every method accessing request.website.

    Don't import directly the method or it won't be mocked during tests, do:
    ```
    from odoo.addons.website.models import ir_http
    my_var = ir_http.get_request_website()
    ```
    """
    return request and getattr(request, 'website', False) or False


class Http(models.AbstractModel):
    _inherit = 'ir.http'

    @classmethod
    def routing_map(cls, key=None):
        key = key or (request and request.website_routing)
        return super(Http, cls).routing_map(key=key)

    @classmethod
    def clear_caches(cls):
        super(Http, cls)._clear_routing_map()
        return super(Http, cls).clear_caches()

    @classmethod
    def _slug_matching(cls, adapter, endpoint, **kw):
        for arg in kw:
            if isinstance(kw[arg], models.BaseModel):
                kw[arg] = kw[arg].with_user(request.uid)
        qs = request.httprequest.query_string.decode('utf-8')
        return adapter.build(endpoint, kw) + (qs and '?%s' % qs or '')

    @classmethod
    def _match(cls, path_info, key=None):
        key = key or (request and request.website_routing)
        return super(Http, cls)._match(path_info, key=key)

    @classmethod
    def _generate_routing_rules(cls, modules, converters):
        website_id = request.website_routing
        logger.debug("_generate_routing_rules for website: %s", website_id)
        domain = [('redirect_type', 'in', ('308', '404')), '|', ('website_id', '=', False), ('website_id', '=', website_id)]

        rewrites = dict([(x.url_from, x) for x in request.env['website.rewrite'].sudo().search(domain)])
        cls._rewrite_len[website_id] = len(rewrites)

        for url, endpoint, routing in super(Http, cls)._generate_routing_rules(modules, converters):
            routing = dict(routing)
            if url in rewrites:
                rewrite = rewrites[url]
                url_to = rewrite.url_to
                if rewrite.redirect_type == '308':
                    logger.debug('Add rule %s for %s' % (url_to, website_id))
                    yield url_to, endpoint, routing  # yield new url

                    if url != url_to:
                        logger.debug('Redirect from %s to %s for website %s' % (url, url_to, website_id))
                        _slug_matching = partial(cls._slug_matching, endpoint=endpoint)
                        routing['redirect_to'] = _slug_matching
                        yield url, endpoint, routing  # yield original redirected to new url
                elif rewrite.redirect_type == '404':
                    logger.debug('Return 404 for %s for website %s' % (url, website_id))
                    continue
            else:
                yield url, endpoint, routing

    @classmethod
    def _get_converters(cls):
        """ Get the converters list for custom url pattern werkzeug need to
            match Rule. This override adds the website ones.
        """
        return dict(
            super(Http, cls)._get_converters(),
            model=ModelConverter,
        )

    @classmethod
    def _auth_method_public(cls):
        """ If no user logged, set the public user of current website, or default
            public user as request uid.
            After this method `request.env` can be called, since the `request.uid` is
            set. The `env` lazy property of `request` will be correct.
        """
        if not request.session.uid:
            env = api.Environment(request.cr, SUPERUSER_ID, request.context)
            website = env['website'].get_current_website()
            if website and website.user_id:
                request.uid = website.user_id.id
        if not request.uid:
            super(Http, cls)._auth_method_public()

    @classmethod
    def _register_website_track(cls, response):
        if getattr(response, 'status_code', 0) != 200 or not hasattr(response, 'qcontext'):
            return False
        main_object = response.qcontext.get('main_object')
        website_page = getattr(main_object, '_name', False) == 'website.page' and main_object
        template = response.qcontext.get('response_template')
        view = template and request.env['website'].get_template(template)
        if view and view.track:
            request.env['website.visitor']._handle_webpage_dispatch(response, website_page)

    @classmethod
    def _dispatch(cls):
        """
        In case of rerouting for translate (e.g. when visiting odoo.com/fr_BE/),
        _dispatch calls reroute() that returns _dispatch with altered request properties.
        The second _dispatch will continue until end of process. When second _dispatch is finished, the first _dispatch
        call receive the new altered request and continue.
        At the end, 2 calls of _dispatch (and this override) are made with exact same request properties, instead of one.
        As the response has not been sent back to the client, the visitor cookie does not exist yet when second _dispatch call
        is treated in _handle_webpage_dispatch, leading to create 2 visitors with exact same properties.
        To avoid this, we check if, !!! before calling super !!!, we are in a rerouting request. If not, it means that we are
        handling the original request, in which we should create the visitor. We ignore every other rerouting requests.
        """
        is_rerouting = hasattr(request, 'routing_iteration')

        request.website_routing = request.env['website'].get_current_website().id

        response = super(Http, cls)._dispatch()

        if not is_rerouting:
            cls._register_website_track(response)
        return response

    @classmethod
    def _add_dispatch_parameters(cls, func):

        # Force website with query string paramater, typically set from website selector in frontend navbar
        force_website_id = request.httprequest.args.get('fw')
        if (force_website_id and request.session.get('force_website_id') != force_website_id and
                request.env.user.has_group('website.group_multi_website') and
                request.env.user.has_group('website.group_website_publisher')):
            request.env['website']._force_website(request.httprequest.args.get('fw'))

        context = {}
        if not request.context.get('tz'):
            context['tz'] = request.session.get('geoip', {}).get('time_zone')
            try:
                pytz.timezone(context['tz'] or '')
            except pytz.UnknownTimeZoneError:
                context.pop('tz')

        request.website = request.env['website'].get_current_website()  # can use `request.env` since auth methods are called
        context['website_id'] = request.website.id
        # This is mainly to avoid access errors in website controllers where there is no
        # context (eg: /shop), and it's not going to propagate to the global context of the tab
        # context['allowed_company_ids'] = [request.website.company_id.id]
        context['allowed_company_ids'] = request.env.user.company_ids.ids
        # modify bound context
        request.context = dict(request.context, **context)

        super(Http, cls)._add_dispatch_parameters(func)

        if request.routing_iteration == 1:
            request.website = request.website.with_context(request.context)

    @classmethod
    def _get_default_lang(cls):
        if getattr(request, 'website', False):
            return request.website.default_lang_id
        return super(Http, cls)._get_default_lang()

    @classmethod
    def _get_translation_frontend_modules_domain(cls):
        domain = super(Http, cls)._get_translation_frontend_modules_domain()
        return OR([domain, [('name', 'ilike', 'website')]])

    @classmethod
    def _serve_page(cls):
        req_page = request.httprequest.path
        page_domain = [('url', '=', req_page)] + request.website.website_domain()

        published_domain = page_domain
        # need to bypass website_published, to apply is_most_specific
        # filter later if not publisher
        pages = request.env['website.page'].sudo().search(published_domain, order='website_id')
        pages = pages.filtered(pages._is_most_specific_page)

        if not request.website.is_publisher():
            pages = pages.filtered('is_visible')

        mypage = pages[0] if pages else False
        _, ext = os.path.splitext(req_page)
        if mypage:
            return request.render(mypage.get_view_identifier(), {
                # 'path': req_page[1:],
                'deletable': True,
                'main_object': mypage,
            }, mimetype=_guess_mimetype(ext))

    @classmethod
    def _serve_redirect(cls):
        req_page = request.httprequest.path
        domain = [
            ('redirect_type', 'in', ('301', '302')),
            ('url_from', '=', req_page)
        ]
        domain += request.website.website_domain()
        return request.env['website.rewrite'].sudo().search(domain, limit=1)

    @classmethod
    def _serve_fallback(cls, exception):
        # serve attachment before
        parent = super(Http, cls)._serve_fallback(exception)
        if parent:  # attachment
            return parent
        if not request.is_frontend:
            return False
        website_page = cls._serve_page()
        if website_page:
            return website_page

        redirect = cls._serve_redirect()
        if redirect:
            return request.redirect(_build_url_w_params(redirect.url_to, request.params), code=redirect.redirect_type)

        return False

    @classmethod
    def _get_exception_code_values(cls, exception):
        code, values = super(Http, cls)._get_exception_code_values(exception)
        if request.website.is_publisher() and isinstance(exception, werkzeug.exceptions.NotFound):
            code = 'page_404'
            values['path'] = request.httprequest.path[1:]
        return (code, values)

    @classmethod
    def _get_values_500_error(cls, env, values, exception):
        View = env["ir.ui.view"]
        values = super(Http, cls)._get_values_500_error(env, values, exception)
        if 'qweb_exception' in values:
            try:
                # exception.name might be int, string
                exception_template = int(exception.name)
            except:
                exception_template = exception.name
            view = View._view_obj(exception_template)
            if exception.html and exception.html in view.arch:
                values['view'] = view
            else:
                # There might be 2 cases where the exception code can't be found
                # in the view, either the error is in a child view or the code
                # contains branding (<div t-att-data="request.browse('ok')"/>).
                et = etree.fromstring(view.with_context(inherit_branding=False).read_combined(['arch'])['arch'])
                node = et.xpath(exception.path)
                line = node is not None and etree.tostring(node[0], encoding='unicode')
                if line:
                    values['view'] = View._views_get(exception_template).filtered(
                        lambda v: line in v.arch
                    )
                    values['view'] = values['view'] and values['view'][0]
        # Needed to show reset template on translated pages (`_prepare_qcontext` will set it for main lang)
        values['editable'] = request.uid and request.website.is_publisher()
        return values

    @classmethod
    def _get_error_html(cls, env, code, values):
        if code == 'page_404':
            return env['ir.ui.view'].render_template('website.%s' % code, values)
        return super(Http, cls)._get_error_html(env, code, values)

    def binary_content(self, xmlid=None, model='ir.attachment', id=None, field='datas',
                       unique=False, filename=None, filename_field='name', download=False,
                       mimetype=None, default_mimetype='application/octet-stream',
                       access_token=None):
        obj = None
        if xmlid:
            obj = self._xmlid_to_obj(self.env, xmlid)
        elif id and model in self.env:
            obj = self.env[model].browse(int(id))
        if obj and 'website_published' in obj._fields:
            if self.env[obj._name].sudo().search([('id', '=', obj.id), ('website_published', '=', True)]):
                self = self.sudo()
        return super(Http, self).binary_content(
            xmlid=xmlid, model=model, id=id, field=field, unique=unique, filename=filename,
            filename_field=filename_field, download=download, mimetype=mimetype,
            default_mimetype=default_mimetype, access_token=access_token)

    @classmethod
    def _xmlid_to_obj(cls, env, xmlid):
        website_id = env['website'].get_current_website()
        if website_id and website_id.theme_id:
            domain = [('key', '=', xmlid), ('website_id', '=', website_id.id)]
            Attachment = env['ir.attachment']
            if request.env.user.share:
                domain.append(('public', '=', True))
                Attachment = Attachment.sudo()
            obj = Attachment.search(domain)
            if obj:
                return obj[0]

        return super(Http, cls)._xmlid_to_obj(env, xmlid)

    @api.model
    def get_frontend_session_info(self):
        session_info = super(Http, self).get_frontend_session_info()
        session_info.update({
            'is_website_user': request.env.user.id == request.website.user_id.id,
        })
        if request.env.user.has_group('website.group_website_publisher'):
            session_info.update({
                'website_id': request.website.id,
                'website_company_id': request.website.company_id.id,
            })
        return session_info


class ModelConverter(ModelConverter):

    def generate(self, uid, dom=None, args=None):
        Model = request.env[self.model].with_user(uid)
        # Allow to current_website_id directly in route domain
        args.update(current_website_id=request.env['website'].get_current_website().id)
        domain = safe_eval(self.domain, (args or {}).copy())
        if dom:
            domain += dom
        for record in Model.search_read(domain=domain, fields=['write_date', Model._rec_name]):
            if record.get(Model._rec_name, False):
                yield {'loc': (record['id'], record[Model._rec_name])}
