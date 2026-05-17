from django import template


register = template.Library()


@register.filter
def has_group(user, group_name: str) -> bool:
    if not getattr(user, "is_authenticated", False):
        return False
    return user.groups.filter(name=group_name).exists()


@register.filter
def can_edit_booking(booking, user) -> bool:
    return booking.can_edit(user)


@register.filter
def can_cancel_booking(booking, user) -> bool:
    return booking.can_cancel(user)
