# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import datetime
import io
import re
import requests
import PyPDF2

from PIL import Image
from werkzeug import urls

from odoo import api, fields, models, _
from odoo.addons.http_routing.models.ir_http import slug
from odoo.exceptions import Warning, UserError, AccessError, ValidationError
from odoo.http import request
from odoo.addons.http_routing.models.ir_http import url_for


class SlidePartnerRelation(models.Model):
    _name = 'slide.slide.partner'
    _description = 'Slide / Partner decorated m2m'
    _table = 'slide_slide_partner'

    slide_id = fields.Many2one('slide.slide', ondelete="cascade", index=True, required=True)
    channel_id = fields.Many2one(
        'slide.channel', string="Channel",
        related="slide_id.channel_id", store=True, index=True, ondelete='cascade')
    partner_id = fields.Many2one('res.partner', index=True, required=True, ondelete='cascade')
    vote = fields.Integer('Vote', default=0)
    completed = fields.Boolean('Completed')
    quiz_attempts_count = fields.Integer('Quiz attempts count', default=0)

    def create(self, values):
        res = super(SlidePartnerRelation, self).create(values)
        completed = res.filtered('completed')
        if completed:
            completed._set_completed_callback()
        return res

    def write(self, values):
        res = super(SlidePartnerRelation, self).write(values)
        if values.get('completed'):
            self._set_completed_callback()
        return res

    def _set_completed_callback(self):
        self.env['slide.channel.partner'].search([
            ('channel_id', 'in', self.channel_id.ids),
            ('partner_id', 'in', self.partner_id.ids),
        ])._recompute_completion()


class SlideLink(models.Model):
    _name = 'slide.slide.link'
    _description = "External URL for a particular slide"

    slide_id = fields.Many2one('slide.slide', required=True, ondelete='cascade')
    name = fields.Char('Title', required=True)
    link = fields.Char('Link', required=True)


class EmbeddedSlide(models.Model):
    """ Embedding in third party websites. Track view count, generate statistics. """
    _name = 'slide.embed'
    _description = 'Embedded Slides View Counter'
    _rec_name = 'slide_id'

    slide_id = fields.Many2one('slide.slide', string="Presentation", required=True, index=True)
    url = fields.Char('Third Party Website URL', required=True)
    count_views = fields.Integer('# Views', default=1)

    def _add_embed_url(self, slide_id, url):
        baseurl = urls.url_parse(url).netloc
        if not baseurl:
            return 0
        embeds = self.search([('url', '=', baseurl), ('slide_id', '=', int(slide_id))], limit=1)
        if embeds:
            embeds.count_views += 1
        else:
            embeds = self.create({
                'slide_id': slide_id,
                'url': baseurl,
            })
        return embeds.count_views


class SlideTag(models.Model):
    """ Tag to search slides accross channels. """
    _name = 'slide.tag'
    _description = 'Slide Tag'

    name = fields.Char('Name', required=True, translate=True)

    _sql_constraints = [
        ('slide_tag_unique', 'UNIQUE(name)', 'A tag must be unique!'),
    ]


class Slide(models.Model):
    _name = 'slide.slide'
    _inherit = [
        'mail.thread',
        'image.mixin',
        'website.seo.metadata', 'website.published.mixin']
    _description = 'Slides'
    _mail_post_access = 'read'
    _order_by_strategy = {
        'sequence': 'sequence asc',
        'most_viewed': 'total_views desc',
        'most_voted': 'likes desc',
        'latest': 'date_published desc',
    }
    _order = 'sequence asc, is_category asc'

    # description
    name = fields.Char('Title', required=True, translate=True)
    active = fields.Boolean(default=True)
    sequence = fields.Integer('Sequence', default=0)
    user_id = fields.Many2one('res.users', string='Uploaded by', default=lambda self: self.env.uid)
    description = fields.Text('Description', translate=True)
    channel_id = fields.Many2one('slide.channel', string="Course", required=True)
    tag_ids = fields.Many2many('slide.tag', 'rel_slide_tag', 'slide_id', 'tag_id', string='Tags')
    is_preview = fields.Boolean('Allow Preview', default=False, help="The course is accessible by anyone : the users don't need to join the channel to access the content of the course.")
    completion_time = fields.Float('Duration', digits=(10, 4), help="The estimated completion time for this slide")
    # Categories
    is_category = fields.Boolean('Is a category', default=False)
    category_id = fields.Many2one('slide.slide', string="Section", compute="_compute_category_id", store=True)
    slide_ids = fields.One2many('slide.slide', "category_id", string="Slides")
    # subscribers
    partner_ids = fields.Many2many('res.partner', 'slide_slide_partner', 'slide_id', 'partner_id',
                                   string='Subscribers', groups='website.group_website_publisher', copy=False)
    slide_partner_ids = fields.One2many('slide.slide.partner', 'slide_id', string='Subscribers information', groups='website.group_website_publisher', copy=False)
    user_membership_id = fields.Many2one(
        'slide.slide.partner', string="Subscriber information", compute='_compute_user_membership_id', compute_sudo=False,
        help="Subscriber information for the current logged in user")
    # Quiz related fields
    question_ids = fields.One2many("slide.question", "slide_id", string="Questions")
    questions_count = fields.Integer(string="Numbers of Questions", compute='_compute_questions_count')
    quiz_first_attempt_reward = fields.Integer("First attempt reward", default=10)
    quiz_second_attempt_reward = fields.Integer("Second attempt reward", default=7)
    quiz_third_attempt_reward = fields.Integer("Third attempt reward", default=5,)
    quiz_fourth_attempt_reward = fields.Integer("Reward for every attempt after the third try", default=2)
    # content
    slide_type = fields.Selection([
        ('infographic', 'Infographic'),
        ('webpage', 'Web Page'),
        ('presentation', 'Presentation'),
        ('document', 'Document'),
        ('video', 'Video'),
        ('quiz', "Quiz")],
        string='Type', required=True,
        default='document',
        help="The document type will be set automatically based on the document URL and properties (e.g. height and width for presentation and document).")
    datas = fields.Binary('Content', attachment=True)
    url = fields.Char('Document URL', help="Youtube or Google Document URL")
    document_id = fields.Char('Document ID', help="Youtube or Google Document ID")
    link_ids = fields.One2many('slide.slide.link', 'slide_id', string="External URL for this slide")
    mime_type = fields.Char('Mime-type')
    html_content = fields.Html("HTML Content", help="Custom HTML content for slides of type 'Web Page'.", translate=True)
    # website
    website_id = fields.Many2one(related='channel_id.website_id', readonly=True)
    date_published = fields.Datetime('Publish Date', readonly=True, tracking=True)
    likes = fields.Integer('Likes', compute='_compute_user_info', store=True, compute_sudo=False)
    dislikes = fields.Integer('Dislikes', compute='_compute_user_info', store=True, compute_sudo=False)
    user_vote = fields.Integer('User vote', compute='_compute_user_info', compute_sudo=False)
    embed_code = fields.Text('Embed Code', readonly=True, compute='_compute_embed_code')
    # views
    embedcount_ids = fields.One2many('slide.embed', 'slide_id', string="Embed Count")
    slide_views = fields.Integer('# of Website Views', store=True, compute="_compute_slide_views")
    public_views = fields.Integer('# of Public Views')
    total_views = fields.Integer("Views", default="0", compute='_compute_total', store=True)
    # comments
    comments_count = fields.Integer('Number of comments', compute="_compute_comments_count")
    # channel
    channel_type = fields.Selection(related="channel_id.channel_type", string="Channel type")
    channel_allow_comment = fields.Boolean(related="channel_id.allow_comment", string="Allows comment")
    # Statistics in case the slide is a category
    nbr_presentation = fields.Integer("Number of Presentations", compute='_compute_slides_statistics', store=True)
    nbr_document = fields.Integer("Number of Documents", compute='_compute_slides_statistics', store=True)
    nbr_video = fields.Integer("Number of Videos", compute='_compute_slides_statistics', store=True)
    nbr_infographic = fields.Integer("Number of Infographics", compute='_compute_slides_statistics', store=True)
    nbr_webpage = fields.Integer("Number of Webpages", compute='_compute_slides_statistics', store=True)
    nbr_quiz = fields.Integer("Number of Quizs", compute="_compute_slides_statistics", store=True)
    total_slides = fields.Integer(compute='_compute_slides_statistics', store=True)

    # Thêm phần trộn câu hỏi
    random_questions = fields.Boolean('Trộn câu hỏi')
    num_questions = fields.Integer('Số lượng câu hỏi', help='Số lượng câu hỏi sẽ dùng trong quiz lấy từ các câu hỏi bên cạnh.')

    _sql_constraints = [
        ('exclusion_html_content_and_url', "CHECK(html_content IS NULL OR url IS NULL)", "A slide is either filled with a document url or HTML content. Not both.")
    ]

    # Todo: chuyển sang tiếng Anh & dịch
    @api.constrains('num_questions', 'question_ids')
    def constrain_max_questions(self):
        for record in self:
            if record.random_questions and record.num_questions <= 0:
                raise ValidationError(_("Trường 'Số lượng câu hỏi' phải lớn hơn 0."))
            if record.num_questions > len(record.question_ids):
                raise ValidationError(_("Trường 'Số lượng câu hỏi' không được vượt quá số câu hỏi được tạo."))
            
    @api.onchange('random_questions')
    def onchange_random_questions(self):
        if self.random_questions:
            self.num_questions = len(self.question_ids)
        
    @api.depends('channel_id.slide_ids.is_category', 'channel_id.slide_ids.sequence')
    def _compute_category_id(self):
        """ Will take all the slides of the channel for which the index is higher
        than the index of this category and lower than the index of the next category.

        Lists are manually sorted because when adding a new browse record order
        will not be correct as the added slide would actually end up at the
        first place no matter its sequence."""
        self.category_id = False  # initialize whatever the state

        channel_slides = {}
        for slide in self:
            if slide.channel_id.id not in channel_slides:
                channel_slides[slide.channel_id.id] = slide.channel_id.slide_ids

        for cid, slides in channel_slides.items():
            current_category = self.env['slide.slide']
            slide_list = list(slides)
            slide_list.sort(key=lambda s: (s.sequence, not s.is_category))
            for slide in slide_list:
                if slide.is_category:
                    current_category = slide
                elif slide.category_id != current_category:
                    slide.category_id = current_category.id

    @api.depends('question_ids')
    def _compute_questions_count(self):
        for slide in self:
            slide.questions_count = len(slide.question_ids)

    @api.depends('website_message_ids.res_id', 'website_message_ids.model', 'website_message_ids.message_type')
    def _compute_comments_count(self):
        for slide in self:
            slide.comments_count = len(slide.website_message_ids)

    @api.depends('slide_views', 'public_views')
    def _compute_total(self):
        for record in self:
            record.total_views = record.slide_views + record.public_views

    @api.depends('slide_partner_ids.vote')
    @api.depends_context('uid')
    def _compute_user_info(self):
        slide_data = dict.fromkeys(self.ids, dict({'likes': 0, 'dislikes': 0, 'user_vote': False}))
        slide_partners = self.env['slide.slide.partner'].sudo().search([
            ('slide_id', 'in', self.ids)
        ])
        for slide_partner in slide_partners:
            if slide_partner.vote == 1:
                slide_data[slide_partner.slide_id.id]['likes'] += 1
                if slide_partner.partner_id == self.env.user.partner_id:
                    slide_data[slide_partner.slide_id.id]['user_vote'] = 1
            elif slide_partner.vote == -1:
                slide_data[slide_partner.slide_id.id]['dislikes'] += 1
                if slide_partner.partner_id == self.env.user.partner_id:
                    slide_data[slide_partner.slide_id.id]['user_vote'] = -1
        for slide in self:
            slide.update(slide_data[slide.id])

    @api.depends('slide_partner_ids.slide_id')
    def _compute_slide_views(self):
        # TODO awa: tried compute_sudo, for some reason it doesn't work in here...
        read_group_res = self.env['slide.slide.partner'].sudo().read_group(
            [('slide_id', 'in', self.ids)],
            ['slide_id'],
            groupby=['slide_id']
        )
        mapped_data = dict((res['slide_id'][0], res['slide_id_count']) for res in read_group_res)
        for slide in self:
            slide.slide_views = mapped_data.get(slide.id, 0)

    @api.depends('slide_ids.slide_type', 'slide_ids.is_published', 'slide_ids.is_category')
    def _compute_slides_statistics(self):
        # Do not use dict.fromkeys(self.ids, dict()) otherwise it will use the same dictionnary for all keys.
        # Therefore, when updating the dict of one key, it updates the dict of all keys.
        keys = ['nbr_%s' % slide_type for slide_type in self.env['slide.slide']._fields['slide_type'].get_values(self.env)]
        default_vals = dict((key, 0) for key in keys)

        res = self.env['slide.slide'].read_group(
            [('is_published', '=', True), ('category_id', 'in', self.ids), ('is_category', '=', False)],
            ['category_id', 'slide_type'], ['category_id', 'slide_type'],
            lazy=False)

        type_stats = self._compute_slides_statistics_type(res)

        for record in self:
            record.update(type_stats.get(record._origin.id, default_vals))

    def _compute_slides_statistics_type(self, read_group_res):
        """ Compute statistics based on all existing slide types """
        slide_types = self.env['slide.slide']._fields['slide_type'].get_values(self.env)
        keys = ['nbr_%s' % slide_type for slide_type in slide_types]
        result = dict((cid, dict((key, 0) for key in keys)) for cid in self.ids)
        for res_group in read_group_res:
            cid = res_group['category_id'][0]
            result[cid]['total_slides'] = 0
            for slide_type in slide_types:
                result[cid]['nbr_%s' % slide_type] += res_group.get('slide_type', '') == slide_type and res_group['__count'] or 0
                result[cid]['total_slides'] += result[cid]['nbr_%s' % slide_type]
        return result

    @api.depends('slide_partner_ids.partner_id')
    @api.depends('uid')
    def _compute_user_membership_id(self):
        slide_partners = self.env['slide.slide.partner'].sudo().search([
            ('slide_id', 'in', self.ids),
            ('partner_id', '=', self.env.user.partner_id.id),
        ])

        for record in self:
            record.user_membership_id = next(
                (slide_partner for slide_partner in slide_partners if slide_partner.slide_id == record),
                self.env['slide.slide.partner']
            )

    @api.depends('document_id', 'slide_type', 'mime_type')
    def _compute_embed_code(self):
        base_url = request and request.httprequest.url_root or self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        if base_url[-1] == '/':
            base_url = base_url[:-1]
        for record in self:
            if record.datas and (not record.document_id or record.slide_type in ['document', 'presentation']):
                slide_url = base_url + url_for('/slides/embed/%s?page=1' % record.id)
                record.embed_code = '<iframe src="%s" class="o_wslides_iframe_viewer" allowFullScreen="true" height="%s" width="%s" frameborder="0"></iframe>' % (slide_url, 315, 420)
            elif record.slide_type == 'video' and record.document_id:
                if not record.mime_type:
                    # embed youtube video
                    record.embed_code = '<iframe src="//www.youtube.com/embed/%s?theme=light" allowFullScreen="true" frameborder="0"></iframe>' % (record.document_id)
                else:
                    # embed google doc video
                    record.embed_code = '<iframe src="//drive.google.com/file/d/%s/preview" allowFullScreen="true" frameborder="0"></iframe>' % (record.document_id)
            else:
                record.embed_code = False

    @api.onchange('url')
    def _on_change_url(self):
        self.ensure_one()
        if self.url:
            res = self._parse_document_url(self.url)
            if res.get('error'):
                raise Warning(_('Could not fetch data from url. Document or access right not available:\n%s') % res['error'])
            values = res['values']
            if not values.get('document_id'):
                raise Warning(_('Please enter valid Youtube or Google Doc URL'))
            for key, value in values.items():
                self[key] = value

    @api.onchange('datas')
    def _on_change_datas(self):
        """ For PDFs, we assume that it takes 5 minutes to read a page. """
        if self.datas:
            data = base64.b64decode(self.datas)
            if data.startswith(b'%PDF-'):
                pdf = PyPDF2.PdfFileReader(io.BytesIO(data), overwriteWarnings=False)
                self.completion_time = (5 * len(pdf.pages)) / 60

    @api.depends('name', 'channel_id.website_id.domain')
    def _compute_website_url(self):
        # TDE FIXME: clena this link.tracker strange stuff
        super(Slide, self)._compute_website_url()
        for slide in self:
            if slide.id:  # avoid to perform a slug on a not yet saved record in case of an onchange.
                base_url = slide.channel_id.get_base_url()
                # link_tracker is not in dependencies, so use it to shorten url only if installed.
                if self.env.registry.get('link.tracker'):
                    url = self.env['link.tracker'].sudo().create({
                        'url': '%s/slides/slide/%s' % (base_url, slug(slide)),
                        'title': slide.name,
                    }).short_url
                else:
                    url = '%s/slides/slide/%s' % (base_url, slug(slide))
                slide.website_url = url

    def get_backend_menu_id(self):
        return self.env.ref('website_slides.website_slides_menu_root').id

    @api.depends('channel_id.can_publish')
    def _compute_can_publish(self):
        for record in self:
            record.can_publish = record.channel_id.can_publish

    @api.model
    def _get_can_publish_error_message(self):
        return _("Publishing is restricted to the responsible of training courses or members of the publisher group for documentation courses")

    # ---------------------------------------------------------
    # ORM Overrides
    # ---------------------------------------------------------

    @api.model
    def create(self, values):
        # Do not publish slide if user has not publisher rights
        channel = self.env['slide.channel'].browse(values['channel_id'])
        if not channel.can_publish:
            # 'website_published' is handled by mixin
            values['date_published'] = False

        if values.get('slide_type') == 'infographic' and not values.get('image_1920'):
            values['image_1920'] = values['datas']
        if values.get('is_category'):
            values['is_preview'] = True
            values['is_published'] = True
        if values.get('is_published') and not values.get('date_published'):
            values['date_published'] = datetime.datetime.now()
        if values.get('url') and not values.get('document_id'):
            doc_data = self._parse_document_url(values['url']).get('values', dict())
            for key, value in doc_data.items():
                values.setdefault(key, value)

        slide = super(Slide, self).create(values)

        if slide.is_published and not slide.is_category:
            slide._post_publication()
        return slide

    def write(self, values):
        if values.get('url') and values['url'] != self.url:
            doc_data = self._parse_document_url(values['url']).get('values', dict())
            for key, value in doc_data.items():
                values.setdefault(key, value)
        if values.get('is_category'):
            values['is_preview'] = True
            values['is_published'] = True

        res = super(Slide, self).write(values)
        if values.get('is_published'):
            self.date_published = datetime.datetime.now()
            self._post_publication()

        if 'is_published' in values or 'active' in values:
            # if the slide is published/unpublished, recompute the completion for the partners
            self.slide_partner_ids._set_completed_callback()

        return res

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        """Sets the sequence to zero so that it always lands at the beginning
        of the newly selected course as an uncategorized slide"""
        rec = super(Slide, self).copy(default)
        rec.sequence = 0
        return rec

    # ---------------------------------------------------------
    # Mail/Rating
    # ---------------------------------------------------------

    @api.returns('mail.message', lambda value: value.id)
    def message_post(self, *, message_type='notification', **kwargs):
        self.ensure_one()
        if message_type == 'comment' and not self.channel_id.can_comment:  # user comments have a restriction on karma
            raise AccessError(_('Not enough karma to comment'))
        return super(Slide, self).message_post(message_type=message_type, **kwargs)

    def get_access_action(self, access_uid=None):
        """ Instead of the classic form view, redirect to website if it is published. """
        self.ensure_one()
        if self.website_published:
            return {
                'type': 'ir.actions.act_url',
                'url': '%s' % self.website_url,
                'target': 'self',
                'target_type': 'public',
                'res_id': self.id,
            }
        return super(Slide, self).get_access_action(access_uid)

    def _notify_get_groups(self):
        """ Add access button to everyone if the document is active. """
        groups = super(Slide, self)._notify_get_groups()

        if self.website_published:
            for group_name, group_method, group_data in groups:
                group_data['has_button_access'] = True

        return groups

    # ---------------------------------------------------------
    # Business Methods
    # ---------------------------------------------------------

    def _post_publication(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        for slide in self.filtered(lambda slide: slide.website_published and slide.channel_id.publish_template_id):
            publish_template = slide.channel_id.publish_template_id
            html_body = publish_template.with_context(base_url=base_url)._render_template(publish_template.body_html, 'slide.slide', slide.id)
            subject = publish_template._render_template(publish_template.subject, 'slide.slide', slide.id)
            slide.channel_id.with_context(mail_create_nosubscribe=True).message_post(
                subject=subject,
                body=html_body,
                subtype='website_slides.mt_channel_slide_published',
                email_layout_xmlid='mail.mail_notification_light',
            )
        return True

    def _generate_signed_token(self, partner_id):
        """ Lazy generate the acces_token and return it signed by the given partner_id
            :rtype tuple (string, int)
            :return (signed_token, partner_id)
        """
        if not self.access_token:
            self.write({'access_token': self._default_access_token()})
        return self._sign_token(partner_id)

    def _send_share_email(self, email, fullscreen):
        # TDE FIXME: template to check
        mail_ids = []
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        for record in self:
            if self.env.user.has_group('base.group_portal'):
                mail_ids.append(self.channel_id.share_template_id.with_context(user=self.env.user, email=email, base_url=base_url, fullscreen=fullscreen).sudo().send_mail(record.id, notif_layout='mail.mail_notification_light', email_values={'email_from': self.env['res.company'].catchall or self.env['res.company'].email, 'email_to': email}))
            else:
                mail_ids.append(self.channel_id.share_template_id.with_context(user=self.env.user, email=email, base_url=base_url, fullscreen=fullscreen).send_mail(record.id, notif_layout='mail.mail_notification_light', email_values={'email_to': email}))
        return mail_ids

    def action_like(self):
        self.check_access_rights('read')
        self.check_access_rule('read')
        return self._action_vote(upvote=True)

    def action_dislike(self):
        self.check_access_rights('read')
        self.check_access_rule('read')
        return self._action_vote(upvote=False)

    def _action_vote(self, upvote=True):
        """ Private implementation of voting. It does not check for any real access
        rights; public methods should grant access before calling this method.

          :param upvote: if True, is a like; if False, is a dislike
        """
        self_sudo = self.sudo()
        SlidePartnerSudo = self.env['slide.slide.partner'].sudo()
        slide_partners = SlidePartnerSudo.search([
            ('slide_id', 'in', self.ids),
            ('partner_id', '=', self.env.user.partner_id.id)
        ])
        slide_id = slide_partners.mapped('slide_id')
        new_slides = self_sudo - slide_id
        channel = slide_id.channel_id
        karma_to_add = 0

        for slide_partner in slide_partners:
            if upvote:
                new_vote = 0 if slide_partner.vote == -1 else 1
                if slide_partner.vote != 1:
                    karma_to_add += channel.karma_gen_slide_vote
            else:
                new_vote = 0 if slide_partner.vote == 1 else -1
                if slide_partner.vote != -1:
                    karma_to_add -= channel.karma_gen_slide_vote
            slide_partner.vote = new_vote

        for new_slide in new_slides:
            new_vote = 1 if upvote else -1
            new_slide.write({
                'slide_partner_ids': [(0, 0, {'vote': new_vote, 'partner_id': self.env.user.partner_id.id})]
            })
            karma_to_add += new_slide.channel_id.karma_gen_slide_vote * (1 if upvote else -1)

        if karma_to_add:
            self.env.user.add_karma(karma_to_add)

    def action_set_viewed(self, quiz_attempts_inc=False):
        if not all(slide.channel_id.is_member for slide in self):
            raise UserError(_('You cannot mark a slide as viewed if you are not among its members.'))

        return bool(self._action_set_viewed(self.env.user.partner_id, quiz_attempts_inc=quiz_attempts_inc))

    def _action_set_viewed(self, target_partner, quiz_attempts_inc=False):
        self_sudo = self.sudo()
        SlidePartnerSudo = self.env['slide.slide.partner'].sudo()
        existing_sudo = SlidePartnerSudo.search([
            ('slide_id', 'in', self.ids),
            ('partner_id', '=', target_partner.id)
        ])
        if quiz_attempts_inc:
            for exsting_slide in existing_sudo:
                exsting_slide.write({
                    'quiz_attempts_count': exsting_slide.quiz_attempts_count + 1
                })

        new_slides = self_sudo - existing_sudo.mapped('slide_id')
        return SlidePartnerSudo.create([{
            'slide_id': new_slide.id,
            'channel_id': new_slide.channel_id.id,
            'partner_id': target_partner.id,
            'quiz_attempts_count': 1 if quiz_attempts_inc else 0,
            'vote': 0} for new_slide in new_slides])

    def action_set_completed(self):
        if not all(slide.channel_id.is_member for slide in self):
            raise UserError(_('You cannot mark a slide as completed if you are not among its members.'))

        return self._action_set_completed(self.env.user.partner_id)

    def _action_set_completed(self, target_partner):
        self_sudo = self.sudo()
        SlidePartnerSudo = self.env['slide.slide.partner'].sudo()
        existing_sudo = SlidePartnerSudo.search([
            ('slide_id', 'in', self.ids),
            ('partner_id', '=', target_partner.id)
        ])
        existing_sudo.write({'completed': True})

        new_slides = self_sudo - existing_sudo.mapped('slide_id')
        SlidePartnerSudo.create([{
            'slide_id': new_slide.id,
            'channel_id': new_slide.channel_id.id,
            'partner_id': target_partner.id,
            'vote': 0,
            'completed': True} for new_slide in new_slides])

        return True

    def _action_set_quiz_done(self):
        if not all(slide.channel_id.is_member for slide in self):
            raise UserError(_('You cannot mark a slide quiz as completed if you are not among its members.'))

        points = 0
        for slide in self:
            user_membership_sudo = slide.user_membership_id.sudo()
            if not user_membership_sudo or user_membership_sudo.completed or not user_membership_sudo.quiz_attempts_count:
                continue

            gains = [slide.quiz_first_attempt_reward,
                     slide.quiz_second_attempt_reward,
                     slide.quiz_third_attempt_reward,
                     slide.quiz_fourth_attempt_reward]
            points += gains[user_membership_sudo.quiz_attempts_count - 1] if user_membership_sudo.quiz_attempts_count <= len(gains) else gains[-1]

        return self.env.user.sudo().add_karma(points)

    def _compute_quiz_info(self, target_partner, quiz_done=False):
        result = dict.fromkeys(self.ids, False)
        slide_partners = self.env['slide.slide.partner'].sudo().search([
            ('slide_id', 'in', self.ids),
            ('partner_id', '=', target_partner.id)
        ])
        slide_partners_map = dict((sp.slide_id.id, sp) for sp in slide_partners)
        for slide in self:
            if not slide.question_ids:
                gains = [0]
            else:
                gains = [slide.quiz_first_attempt_reward,
                         slide.quiz_second_attempt_reward,
                         slide.quiz_third_attempt_reward,
                         slide.quiz_fourth_attempt_reward]
            result[slide.id] = {
                'quiz_karma_max': gains[0],  # what could be gained if succeed at first try
                'quiz_karma_gain': gains[0],  # what would be gained at next test
                'quiz_karma_won': 0,  # what has been gained
                'quiz_attempts_count': 0,  # number of attempts
            }
            slide_partner = slide_partners_map.get(slide.id)
            if slide.question_ids and slide_partner:
                if slide_partner.quiz_attempts_count:
                    result[slide.id]['quiz_karma_gain'] = gains[slide_partner.quiz_attempts_count] if slide_partner.quiz_attempts_count < len(gains) else gains[-1]
                    result[slide.id]['quiz_attempts_count'] = slide_partner.quiz_attempts_count
                if quiz_done or slide_partner.completed:
                    result[slide.id]['quiz_karma_won'] = gains[slide_partner.quiz_attempts_count-1] if slide_partner.quiz_attempts_count < len(gains) else gains[-1]
        return result

    # --------------------------------------------------
    # Parsing methods
    # --------------------------------------------------

    @api.model
    def _fetch_data(self, base_url, params, content_type=False):
        result = {'values': dict()}
        try:
            response = requests.get(base_url, timeout=3, params=params)
            response.raise_for_status()
            if content_type == 'json':
                result['values'] = response.json()
            elif content_type in ('image', 'pdf'):
                result['values'] = base64.b64encode(response.content)
            else:
                result['values'] = response.content
        except requests.exceptions.HTTPError as e:
            result['error'] = e.response.content
        except requests.exceptions.ConnectionError as e:
            result['error'] = str(e)
        return result

    def _find_document_data_from_url(self, url):
        url_obj = urls.url_parse(url)
        if url_obj.ascii_host == 'youtu.be':
            return ('youtube', url_obj.path[1:] if url_obj.path else False)
        elif url_obj.ascii_host in ('youtube.com', 'www.youtube.com', 'm.youtube.com'):
            v_query_value = url_obj.decode_query().get('v')
            if v_query_value:
                return ('youtube', v_query_value)
            split_path = url_obj.path.split('/')
            if len(split_path) >= 3 and split_path[1] in ('v', 'embed'):
                return ('youtube', split_path[2])

        expr = re.compile(r'(^https:\/\/docs.google.com|^https:\/\/drive.google.com).*\/d\/([^\/]*)')
        arg = expr.match(url)
        document_id = arg and arg.group(2) or False
        if document_id:
            return ('google', document_id)

        return (None, False)

    def _parse_document_url(self, url, only_preview_fields=False):
        document_source, document_id = self._find_document_data_from_url(url)
        if document_source and hasattr(self, '_parse_%s_document' % document_source):
            return getattr(self, '_parse_%s_document' % document_source)(document_id, only_preview_fields)
        return {'error': _('Unknown document')}

    def _parse_youtube_document(self, document_id, only_preview_fields):
        """ If we receive a duration (YT video), we use it to determine the slide duration.
        The received duration is under a special format (e.g: PT1M21S15, meaning 1h 21m 15s). """

        key = self.env['website'].get_current_website().website_slide_google_app_key
        fetch_res = self._fetch_data('https://www.googleapis.com/youtube/v3/videos', {'id': document_id, 'key': key, 'part': 'snippet,contentDetails', 'fields': 'items(id,snippet,contentDetails)'}, 'json')
        if fetch_res.get('error'):
            return fetch_res

        values = {'slide_type': 'video', 'document_id': document_id}
        items = fetch_res['values'].get('items')
        if not items:
            return {'error': _('Please enter valid Youtube or Google Doc URL')}
        youtube_values = items[0]

        youtube_duration = youtube_values.get('contentDetails', {}).get('duration')
        if youtube_duration:
            parsed_duration = re.search(r'^PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?$', youtube_duration)
            values['completion_time'] = (int(parsed_duration.group(1) or 0)) + \
                                        (int(parsed_duration.group(2) or 0) / 60) + \
                                        (int(parsed_duration.group(3) or 0) / 3600)

        if youtube_values.get('snippet'):
            snippet = youtube_values['snippet']
            if only_preview_fields:
                values.update({
                    'url_src': snippet['thumbnails']['high']['url'],
                    'title': snippet['title'],
                    'description': snippet['description']
                })

                return values

            values.update({
                'name': snippet['title'],
                'image_1920': self._fetch_data(snippet['thumbnails']['high']['url'], {}, 'image')['values'],
                'description': snippet['description'],
                'mime_type': False,
            })
        return {'values': values}

    @api.model
    def _parse_google_document(self, document_id, only_preview_fields):
        def get_slide_type(vals):
            # TDE FIXME: WTF ??
            slide_type = 'presentation'
            if vals.get('image_1920'):
                image = Image.open(io.BytesIO(base64.b64decode(vals['image_1920'])))
                width, height = image.size
                if height > width:
                    return 'document'
            return slide_type

        # Google drive doesn't use a simple API key to access the data, but requires an access
        # token. However, this token is generated in module google_drive, which is not in the
        # dependencies of website_slides. We still keep the 'key' parameter just in case, but that
        # is probably useless.
        params = {}
        params['projection'] = 'BASIC'
        if 'google.drive.config' in self.env:
            access_token = self.env['google.drive.config'].get_access_token()
            if access_token:
                params['access_token'] = access_token
        if not params.get('access_token'):
            params['key'] = self.env['website'].get_current_website().website_slide_google_app_key

        fetch_res = self._fetch_data('https://www.googleapis.com/drive/v2/files/%s' % document_id, params, "json")
        if fetch_res.get('error'):
            return fetch_res

        google_values = fetch_res['values']
        if only_preview_fields:
            return {
                'url_src': google_values['thumbnailLink'],
                'title': google_values['title'],
            }

        values = {
            'name': google_values['title'],
            'image_1920': self._fetch_data(google_values['thumbnailLink'].replace('=s220', ''), {}, 'image')['values'],
            'mime_type': google_values['mimeType'],
            'document_id': document_id,
        }
        if google_values['mimeType'].startswith('video/'):
            values['slide_type'] = 'video'
        elif google_values['mimeType'].startswith('image/'):
            values['datas'] = values['image_1920']
            values['slide_type'] = 'infographic'
        elif google_values['mimeType'].startswith('application/vnd.google-apps'):
            values['slide_type'] = get_slide_type(values)
            if 'exportLinks' in google_values:
                values['datas'] = self._fetch_data(google_values['exportLinks']['application/pdf'], params, 'pdf')['values']
        elif google_values['mimeType'] == 'application/pdf':
            # TODO: Google Drive PDF document doesn't provide plain text transcript
            values['datas'] = self._fetch_data(google_values['webContentLink'], {}, 'pdf')['values']
            values['slide_type'] = get_slide_type(values)

        return {'values': values}

    def _default_website_meta(self):
        res = super(Slide, self)._default_website_meta()
        res['default_opengraph']['og:title'] = res['default_twitter']['twitter:title'] = self.name
        res['default_opengraph']['og:description'] = res['default_twitter']['twitter:description'] = self.description
        res['default_opengraph']['og:image'] = res['default_twitter']['twitter:image'] = self.env['website'].image_url(self, 'image_1024')
        res['default_meta_description'] = self.description
        return res
