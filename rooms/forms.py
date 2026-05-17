from django import forms

from core.forms import BootstrapFormMixin

from .models import Equipment, MeetingRoom


class RoomFilterForm(BootstrapFormMixin, forms.Form):
    q = forms.CharField(label="Поиск", required=False)
    location = forms.CharField(label="Локация", required=False)
    min_capacity = forms.IntegerField(label="Минимальная вместимость", required=False, min_value=1)
    approval_policy = forms.ChoiceField(
        label="Режим подтверждения",
        required=False,
        choices=[("", "Любой")] + list(MeetingRoom.ApprovalPolicy.choices),
    )
    equipment = forms.ModelMultipleChoiceField(
        label="Оснащение",
        queryset=Equipment.objects.none(),
        required=False,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["equipment"].queryset = Equipment.objects.all()

