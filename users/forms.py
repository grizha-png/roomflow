from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User

from core.forms import BootstrapFormMixin


class SignUpForm(BootstrapFormMixin, UserCreationForm):
    first_name = forms.CharField(label="Имя", max_length=150)
    last_name = forms.CharField(label="Фамилия", max_length=150)
    email = forms.EmailField(label="Email")

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("first_name", "last_name", "username", "email", "password1", "password2")
        labels = {
            "username": "Логин",
            "password1": "Пароль",
            "password2": "Подтверждение пароля",
        }

    def save(self, commit=True):
        user = super().save(commit=False)
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
        return user


class StyledAuthenticationForm(BootstrapFormMixin, AuthenticationForm):
    username = forms.CharField(label="Логин", max_length=150)
    password = forms.CharField(label="Пароль", strip=False, widget=forms.PasswordInput)
