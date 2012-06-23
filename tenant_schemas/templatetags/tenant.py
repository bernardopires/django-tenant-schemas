from django.conf import settings
from django.template import Library
from django.template.base import TemplateSyntaxError, kwarg_re
from django.template.defaulttags import url as default_url, URLNode
from tenant_schemas.utils import clean_tenant_url

register = Library()

class SchemaURLNode(URLNode):
    def render(self, context):
        url = super(SchemaURLNode, self).render(context)
        return clean_tenant_url(url)


@register.tag
def url(parser, token):
    """
    (todo) find an eleganter solution
    Copied from django's url tag and changed which kind of Node it
    returns
    """
    bits = token.split_contents()
    if len(bits) < 2:
        raise TemplateSyntaxError("'%s' takes at least one argument"
                                  " (path to a view)" % bits[0])
    viewname = parser.compile_filter(bits[1])
    args = []
    kwargs = {}
    asvar = None
    bits = bits[2:]
    if len(bits) >= 2 and bits[-2] == 'as':
        asvar = bits[-1]
        bits = bits[:-2]

    if len(bits):
        for bit in bits:
            match = kwarg_re.match(bit)
            if not match:
                raise TemplateSyntaxError("Malformed arguments to url tag")
            name, value = match.groups()
            if name:
                kwargs[name] = parser.compile_filter(value)
            else:
                args.append(parser.compile_filter(value))

    return SchemaURLNode(viewname, args, kwargs, asvar)