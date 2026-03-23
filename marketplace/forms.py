from django import forms
from django.forms import inlineformset_factory

from .models import Listing, ListingPhoto, Category


class ListingForm(forms.ModelForm):
    class Meta:
        model = Listing
        fields = [
            "title",
            "description",
            "category",
            "condition",
            "price",
            "negotiable",
            "university",
            "campus_location",
        ]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control", "placeholder": "What are you selling?"}),
            "description": forms.Textarea(
                attrs={"class": "form-control", "rows": 5, "placeholder": "Describe the item in detail..."}
            ),
            "category": forms.Select(attrs={"class": "form-select"}),
            "condition": forms.Select(attrs={"class": "form-select"}),
            "price": forms.NumberInput(attrs={"class": "form-control", "min": "0", "placeholder": "0"}),
            "negotiable": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "university": forms.TextInput(attrs={"class": "form-control", "placeholder": "Your university"}),
            "campus_location": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "e.g. Main Gate, Library Block"}
            ),
        }

    def clean_price(self):
        price = self.cleaned_data.get("price")
        if price is not None and price < 0:
            raise forms.ValidationError("Price must be zero or greater.")
        return price


class ListingPhotoForm(forms.ModelForm):
    class Meta:
        model = ListingPhoto
        fields = ["image", "is_primary", "order"]
        widgets = {
            "image": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "is_primary": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "order": forms.HiddenInput(),
        }


ListingPhotoFormSet = inlineformset_factory(
    Listing,
    ListingPhoto,
    form=ListingPhotoForm,
    extra=5,
    max_num=5,
    can_delete=True,
)


class ListingSearchForm(forms.Form):
    query = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Search listings..."}
        ),
    )
    category = forms.ModelChoiceField(
        queryset=Category.objects.all(),
        required=False,
        empty_label="All Categories",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    condition = forms.ChoiceField(
        choices=[("", "Any Condition")] + Listing.CONDITION_CHOICES,
        required=False,
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    min_price = forms.DecimalField(
        required=False,
        min_value=0,
        widget=forms.NumberInput(attrs={"class": "form-control", "placeholder": "Min price"}),
    )
    max_price = forms.DecimalField(
        required=False,
        min_value=0,
        widget=forms.NumberInput(attrs={"class": "form-control", "placeholder": "Max price"}),
    )
    university = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Filter by university"}),
    )
