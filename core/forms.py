from django import forms


class BootstrapFormMixin:
    input_class = "form-control"
    select_class = "form-select"
    checkbox_class = "form-check-input"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            existing_classes = widget.attrs.get("class", "")
            if isinstance(widget, forms.CheckboxInput):
                new_class = self.checkbox_class
            elif isinstance(widget, (forms.Select, forms.SelectMultiple)):
                new_class = self.select_class
            elif isinstance(widget, forms.RadioSelect):
                new_class = ""
            else:
                new_class = self.input_class
            if new_class:
                widget.attrs["class"] = " ".join(filter(None, [existing_classes, new_class]))
            if not isinstance(widget, (forms.CheckboxInput, forms.RadioSelect)):
                widget.attrs.setdefault("placeholder", field.label)

