from django import forms
from django.forms import inlineformset_factory

from .models import Review, SkillBooking, SkillCategory, SkillOffering, SkillPortfolioItem


class SkillOfferingForm(forms.ModelForm):
    class Meta:
        model = SkillOffering
        fields = [
            "title",
            "description",
            "category",
            "delivery_method",
            "status",
            "price_type",
            "price_min",
            "price_max",
            "estimated_duration",
            "availability",
            "language",
            "university",
        ]
        widgets = {
            "title": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "What skill are you offering?"}
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 5,
                    "placeholder": "Describe your skill, experience, and what clients can expect...",
                }
            ),
            "category": forms.Select(attrs={"class": "form-select"}),
            "delivery_method": forms.Select(attrs={"class": "form-select"}),
            "price_type": forms.Select(attrs={"class": "form-select"}),
            "price_min": forms.NumberInput(
                attrs={"class": "form-control", "min": "0", "placeholder": "Min price"}
            ),
            "price_max": forms.NumberInput(
                attrs={"class": "form-control", "min": "0", "placeholder": "Max price"}
            ),
            "estimated_duration": forms.TextInput(
                attrs={"class": "form-control", "placeholder": 'e.g. "1 hour", "2-3 hours"'}
            ),
            "availability": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "e.g. Weekdays 4pm-8pm, Saturdays all day",
                }
            ),
            "status": forms.Select(attrs={"class": "form-select"}),
            "language": forms.TextInput(
                attrs={"class": "form-control", "placeholder": 'e.g. English, Luganda, Swahili'}
            ),
            "university": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Your university"}
            ),
        }

    def clean(self):
        cleaned_data = super().clean()
        price_type = cleaned_data.get("price_type")
        price_min = cleaned_data.get("price_min")
        price_max = cleaned_data.get("price_max")

        if price_type in ("fixed", "hourly"):
            if price_min is None:
                self.add_error("price_min", "Please enter a price for this price type.")
        if price_min is not None and price_max is not None:
            if price_max < price_min:
                self.add_error("price_max", "Maximum price cannot be less than minimum price.")
        return cleaned_data


class SkillPortfolioItemForm(forms.ModelForm):
    class Meta:
        model = SkillPortfolioItem
        fields = ["title", "description", "image", "link", "order"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control", "placeholder": "Portfolio item title"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "image": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "link": forms.URLInput(attrs={"class": "form-control", "placeholder": "https://..."}),
            "order": forms.HiddenInput(),
        }


SkillPortfolioFormSet = inlineformset_factory(
    SkillOffering,
    SkillPortfolioItem,
    form=SkillPortfolioItemForm,
    extra=3,
    max_num=10,
    can_delete=True,
)


class BookingRequestForm(forms.ModelForm):
    class Meta:
        model = SkillBooking
        fields = ["requested_date", "notes", "price_agreed"]
        widgets = {
            "requested_date": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "notes": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Describe what you need help with, any specific requirements, etc.",
                }
            ),
            "price_agreed": forms.NumberInput(
                attrs={"class": "form-control", "min": "0", "placeholder": "Agreed price (optional)"}
            ),
        }

    def clean_requested_date(self):
        from django.utils import timezone
        date = self.cleaned_data.get("requested_date")
        if date and date < timezone.now().date():
            raise forms.ValidationError("Requested date cannot be in the past.")
        return date


class ReviewForm(forms.ModelForm):
    RATING_CHOICES = [(i, str(i)) for i in range(1, 6)]

    rating = forms.ChoiceField(
        choices=RATING_CHOICES,
        widget=forms.RadioSelect(attrs={"class": "form-check-input star-rating"}),
    )

    class Meta:
        model = Review
        fields = ["rating", "comment"]
        widgets = {
            "comment": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Share your experience...",
                }
            ),
        }

    def clean_rating(self):
        rating = self.cleaned_data.get("rating")
        try:
            rating = int(rating)
        except (TypeError, ValueError):
            raise forms.ValidationError("Invalid rating value.")
        if not (1 <= rating <= 5):
            raise forms.ValidationError("Rating must be between 1 and 5.")
        return rating
