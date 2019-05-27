from django import template
from django.template.defaulttags import url as default_url, URLNode
from tenant_schemas.utils import clean_tenant_url, schema_context, tenant_context

register = template.Library()


class SchemaURLNode(URLNode):
    def __init__(self, url_node):
        super(SchemaURLNode, self).__init__(url_node.view_name, url_node.args, url_node.kwargs, url_node.asvar)

    def render(self, context):
        url = super(SchemaURLNode, self).render(context)
        return clean_tenant_url(url)


@register.tag
def url(parser, token):
    return SchemaURLNode(default_url(parser, token))


@register.tag
def schemacontext(parser, token):
    try:
        tag_name, schema_name_arg = token.split_contents()
    except ValueError:
        raise template.TemplateSyntaxError(
            '%r tag requires exactly one argument' % token.contents.split()[0]
        )
    nodelist = parser.parse(('endschemacontext',))
    parser.delete_first_token()
    return SchemaContextNode(schema_name_arg, nodelist)


class SchemaContextNode(template.Node):
    def __init__(self, schema_name_arg, nodelist):
        self.schema_name_arg = template.Variable(schema_name_arg)
        self.nodelist = nodelist

    def render(self, context):
        try:
            schema_name = self.schema_name_arg.resolve(context)
        except template.VariableDoesNotExist:
            raise template.TemplateSyntaxError(
                'Unable to resolve %r' % self.schema_name_arg.var
            )
        with schema_context(schema_name):
            output = self.nodelist.render(context)
        return output


@register.tag
def tenantcontext(parser, token):
    try:
        tag_name, tenant_arg = token.split_contents()
    except ValueError:
        raise template.TemplateSyntaxError(
            '%r tag requires exactly one argument' % token.contents.split()[0]
        )
    nodelist = parser.parse(('endtenantcontext',))
    parser.delete_first_token()
    return TenantContextNode(tenant_arg, nodelist)


class TenantContextNode(template.Node):
    def __init__(self, tenant_arg, nodelist):
        self.tenant_arg = template.Variable(tenant_arg)
        self.nodelist = nodelist

    def render(self, context):
        try:
            tenant = self.tenant_arg.resolve(context)
        except template.VariableDoesNotExist:
            raise template.TemplateSyntaxError(
                'Unable to resolve %r' % self.tenant_arg.var
            )
        with tenant_context(tenant):
            output = self.nodelist.render(context)
        return output
