from django import forms


class MessageForm(forms.Form):
    content = forms.CharField(
        widget=forms.Textarea(attrs={
            "rows": 3,
            "placeholder": "Write a message…",
            "class": "form-control",
        }),
        label="Message",
    )

    def clean_content(self):
        content = self.cleaned_data.get("content", "")
        content = content.strip()
        if not content:
            raise forms.ValidationError("Message cannot be empty.")
        return content
