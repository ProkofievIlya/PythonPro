from decimal import Decimal

from django import forms
from django.utils.translation import gettext_lazy as _

from .models import Book


class BookForm(forms.ModelForm):
    class Meta:
        model = Book
        fields = (
            "title",
            "author",
            "price",
            "description",
            "stock",
            "category",
            "title_en",
            "author_en",
            "description_en",
            "cover",
        )
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "author": forms.TextInput(attrs={"class": "form-control"}),
            "price": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01", "min": "0"}
            ),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "stock": forms.NumberInput(attrs={"class": "form-control", "min": "0"}),
            "category": forms.Select(attrs={"class": "form-select"}),
            "title_en": forms.TextInput(attrs={"class": "form-control"}),
            "author_en": forms.TextInput(attrs={"class": "form-control"}),
            "description_en": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "cover": forms.ClearableFileInput(attrs={"class": "form-control", "accept": "image/*"}),
        }

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.fields["category"].label_from_instance = lambda obj: obj.localized_name

    def clean_price(self) -> Decimal:
        price = self.cleaned_data["price"]
        if price <= 0:
            raise forms.ValidationError(
                _("Ціна має бути більшою за нуль."), code="invalid_price"
            )
        return price


class CheckoutForm(forms.Form):
    email = forms.EmailField(
        label=_("Email для листа"),
        error_messages={
            "required": _("Вкажіть email для замовлення."),
            "invalid": _("Вкажіть коректний email."),
        },
    )
