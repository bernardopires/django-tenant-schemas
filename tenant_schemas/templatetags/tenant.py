from django.template import Library
from django.template.defaulttags import url as default_url, URLNode
from tenant_schemas.utils import clean_tenant_url

register = Library()

class SchemaURLNode(URLNode):

    def __init__(self, url_node):
        super(SchemaURLNode, self).__init__(url_node.view_name, url_node.args, url_node.kwargs, url_node.asvar, url_node.legacy_view_name)

def render(self, context):
    url = super(SchemaURLNode, self).render(context)
    return clean_tenant_url(url)

@register.tag
def url(parser, token):
    return SchemaURLNode(default_url(parser,token))

@register.assignment_tag(takes_context=True)
def get_tenant(context):
    if hasattr(context['request'],'tenant'):
        return context['request'].tenant
