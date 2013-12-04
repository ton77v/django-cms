# -*- coding: utf-8 -*-
from classytags.arguments import Argument
from classytags.core import Tag, Options
from django import template
from django.template.defaultfilters import safe
from django.utils.http import urlencode
from django.utils.translation import ugettext_lazy as _
from classytags.helpers import InclusionTag
from django.core.urlresolvers import reverse
from cms.utils import get_language_from_request

register = template.Library()


class RenderPlaceholder(Tag):
    name = 'render_placeholder'
    options = Options(
        Argument('placeholder'),
        Argument('width', default=None, required=False),
        'language',
        Argument('language', default=None, required=False),
    )

    def render_tag(self, context, placeholder, width, language=None):
        request = context.get('request', None)
        if not request:
            return ''
        if not placeholder:
            return ''
        return safe(placeholder.render(context, width, lang=language))
register.tag(RenderPlaceholder)


class CMSEditableObject(InclusionTag):
    template = 'cms/toolbar/content.html'
    edit_template = 'cms/toolbar/plugin.html'
    name = 'show_editable_model'
    options = Options(
        Argument('instance'),
        Argument('attribute'),
        Argument('edit_fields', default=None, required=False),
        Argument('language', default=None, required=False),
        Argument('view_url', default=None, required=False),
        Argument('view_method', default=None, required=False),
    )

    def _is_editable(self, request):
        return (request and hasattr(request, 'toolbar') and
                request.toolbar.edit_mode)

    def get_template(self, context, **kwargs):
        if self._is_editable(context.get('request', None)):
            return self.edit_template
        return self.template

    def get_context(self, context, instance, attribute, edit_fields, language,
                    view_url, view_method):
        if not language:
            language = get_language_from_request(context['request'])
        # This allow the requested item to be a method, a property or an
        # attribute
        if not instance:
            return context
        if not attribute:
            return context
        attribute = attribute.strip()
        context['attribute_name'] = attribute
        querystring = {'language': language}
        if edit_fields:
            context['edit_fields'] = edit_fields.strip().split(",")
        context['content'] = getattr(instance, attribute, '')
        if callable(context['content']):
            context['content'] = context['content'](context['request'])
        context['rendered_content'] = context['content']
        # If the toolbar is not enabled the following part is just skipped: it
        # would cause a perfomance hit for no reason
        if self._is_editable(context.get('request', None)):
            instance.get_plugin_name = u"%s %s" % (unicode(_('Edit')), unicode(instance._meta.verbose_name))
            context['instance'] = instance
            context['generic'] = instance._meta
            # view_method has the precedence and we retrieve the corresponding
            # attribute in the instance class.
            # If view_method refers to a method it will be called passing the
            # request; if it's an attribute, it's stored for later use
            if view_method:
                method = getattr(instance, view_method)
                if callable(method):
                    url_base = method(context['request'])
                else:
                    url_base = method
            else:
                # The default view_url is the default admin changeform for the
                # current instance
                if not edit_fields:
                    view_url = 'admin:%s_%s_change' % (
                        instance._meta.app_label, instance._meta.module_name)
                    url_base = reverse(view_url, args=(instance.pk,))
                else:
                    if not view_url:
                        view_url = 'admin:%s_%s_edit_field' % (
                            instance._meta.app_label, instance._meta.module_name)
                    url_base = reverse(view_url, args=(instance.pk, language))
                    querystring['edit_fields'] = ",".join(context['edit_fields'])
            context['edit_url'] = "%s?%s" % (url_base, urlencode(querystring))
        return context


register.tag(CMSEditableObject)
