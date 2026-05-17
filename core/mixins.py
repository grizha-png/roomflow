from django.contrib.auth.mixins import UserPassesTestMixin


class ModeratorRequiredMixin(UserPassesTestMixin):
    raise_exception = True

    def test_func(self):
        user = self.request.user
        return user.is_authenticated and (user.is_staff or user.groups.filter(name="moderator").exists())
