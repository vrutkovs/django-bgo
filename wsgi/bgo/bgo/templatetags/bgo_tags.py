from django import template

register = template.Library()


@register.simple_tag()
def build_link_class(has_smoketests):
    if has_smoketests:
        return ''
    else:
        return 'text-muted'


@register.simple_tag()
def build_list_item_class(build, tmp_build):
    if build and build.id == tmp_build.id:
        return 'list-group-item list-group-item-info'
    else:
        return 'list-group-item'