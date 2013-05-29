from django.template import Library
import django.template.defaulttags
import tenant_schemas.utils

register = Library()


class SchemaURLNode(django.template.defaulttags.URLNode):

    def __init__(self, url_node):
        super(SchemaURLNode, self).__init__(url_node.view_name, url_node.args, url_node.kwargs, url_node.asvar)

    def render(self, context):
        url = super(SchemaURLNode, self).render(context)
        return tenant_schemas.utils.clean_tenant_url(url)


@register.tag
def url(parser, token):
    return SchemaURLNode(django.template.defaulttags.url(parser, token))


@register.assignment_tag(takes_context=True)
def get_tenant(context):
    if hasattr(context['request'], 'tenant'):
        return context['request'].tenant
