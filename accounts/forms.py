import re

from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, PasswordChangeForm
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

User = get_user_model()

ALLOWED_EMAIL_DOMAIN = 'students.cavendish.ac.ug'
MAX_PHOTO_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB
ALLOWED_IMAGE_TYPES = [
    'image/jpeg', 'image/jpg', 'image/png',
    'image/heic', 'image/heif',          # iPhone default formats
    'image/heic-sequence', 'image/heif-sequence',
    'image/webp',                         # Chrome/Android
]
ALLOWED_EXTENSIONS = ('.jpg', '.jpeg', '.png', '.heic', '.heif', '.webp')


class RegistrationForm(UserCreationForm):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': f'yourname@{ALLOWED_EMAIL_DOMAIN}',
            'autocomplete': 'email',
            'id': 'id_email',
        }),
        help_text=f'Only @{ALLOWED_EMAIL_DOMAIN} addresses are accepted.',
    )
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Choose a username',
            'autocomplete': 'username',
        }),
        help_text='Letters, digits and @/./+/-/_ only.',
    )
    full_name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Full name as on your student ID',
        }),
    )
    student_id = forms.CharField(
        max_length=50,
        label='Student ID',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g. 121-353',
        }),
        help_text='Format: digits-digits, e.g. 121-353',
    )
    university = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Name of your university',
        }),
    )
    course = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g. Bachelor of Science in Computer Science',
        }),
    )
    year_of_study = forms.ChoiceField(
        choices=User.YEAR_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    phone_number = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '+256 700 000000',
        }),
        help_text='Your phone number is used for account security. SMS verification will be available soon.',
    )

    def clean_year_of_study(self):
        val = self.cleaned_data.get('year_of_study')
        try:
            return int(val)
        except (TypeError, ValueError):
            raise ValidationError('Please select a valid year of study.')

    password1 = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Create a strong password',
            'autocomplete': 'new-password',
        }),
    )
    password2 = forms.CharField(
        label='Confirm Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Repeat your password',
            'autocomplete': 'new-password',
        }),
    )
    profile_photo = forms.ImageField(
        required=False,
        widget=forms.ClearableFileInput(attrs={'class': 'form-control'}),
        help_text='Optional. Upload a clear photo of yourself.',
    )

    class Meta:
        model = User
        fields = (
            'email', 'username', 'full_name', 'student_id',
            'university', 'course', 'year_of_study', 'phone_number',
            'password1', 'password2', 'profile_photo',
        )

    def clean_email(self):
        email = self.cleaned_data.get('email', '').lower().strip()
        # Domain gate — server-side (client-side JS mirrors this)
        if not email.endswith(f'@{ALLOWED_EMAIL_DOMAIN}'):
            raise ValidationError(
                'Only Cavendish University Uganda student emails are accepted. '
                f'Please use your @{ALLOWED_EMAIL_DOMAIN} address.'
            )
        if User.objects.filter(email=email).exists():
            raise ValidationError(
                'An account with this email already exists. Try logging in instead.'
            )
        return email

    def clean_student_id(self):
        student_id = self.cleaned_data.get('student_id', '').strip()
        if not re.match(r'^\d+-\d+$', student_id):
            raise ValidationError(
                'Student ID must be in the format 121-353 (digits, hyphen, digits).'
            )
        if User.objects.filter(student_id=student_id).exists():
            raise ValidationError(
                'This student ID is already registered on the platform. '
                'If you believe this is an error, contact support.'
            )
        return student_id

    def clean_username(self):
        username = self.cleaned_data.get('username', '').strip()
        if User.objects.filter(username__iexact=username).exists():
            raise ValidationError('This username is already taken.')
        return username


class EmailLoginForm(AuthenticationForm):
    username = forms.EmailField(
        label='Email Address',
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your email',
            'autocomplete': 'email',
            'autofocus': True,
        }),
    )
    password = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your password',
            'autocomplete': 'current-password',
        }),
    )
    remember_me = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label='Remember me',
    )


class ProfileEditForm(forms.ModelForm):
    full_name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )
    university = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )
    course = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )
    year_of_study = forms.ChoiceField(
        choices=User.YEAR_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    phone_number = forms.CharField(
        required=False,
        max_length=20,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )
    bio = forms.CharField(
        required=False,
        max_length=500,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Tell other students a little about yourself…',
        }),
    )
    profile_photo = forms.ImageField(
        required=False,
        widget=forms.ClearableFileInput(attrs={'class': 'form-control'}),
        help_text='Upload a new photo to replace the current one.',
    )

    class Meta:
        model = User
        fields = (
            'full_name', 'university', 'course', 'year_of_study',
            'phone_number', 'bio', 'profile_photo',
        )

    def clean_year_of_study(self):
        val = self.cleaned_data.get('year_of_study')
        try:
            return int(val)
        except (TypeError, ValueError):
            raise ValidationError('Please select a valid year of study.')


class StudentPasswordChangeForm(PasswordChangeForm):
    old_password = forms.CharField(
        label='Current Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'autocomplete': 'current-password',
        }),
    )
    new_password1 = forms.CharField(
        label='New Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'autocomplete': 'new-password',
        }),
    )
    new_password2 = forms.CharField(
        label='Confirm New Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'autocomplete': 'new-password',
        }),
    )


class IdentityVerificationForm(forms.Form):
    id_card_photo = forms.ImageField(
        label='Photo of your student ID card',
        help_text=(
            'Take a clear photo of your Cavendish University student ID card. '
            'Make sure your name, student number, and photo on the card are clearly visible. '
            'Accepted formats: JPG, PNG, HEIC (iPhone), WebP. Max size: 5 MB.'
        ),
        widget=forms.ClearableFileInput(attrs={
            'class': 'form-control',
            'accept': 'image/jpeg,image/png,image/jpg,image/heic,image/heif,image/webp',
        }),
    )
    selfie_photo = forms.ImageField(
        label='A clear photo of your face',
        help_text=(
            'Take a selfie in good lighting facing the camera directly. '
            'Your full face must be clearly visible. '
            'This is compared against the photo on your student ID card to confirm your identity. '
            'Accepted formats: JPG, PNG, HEIC (iPhone), WebP. Max size: 5 MB.'
        ),
        widget=forms.ClearableFileInput(attrs={
            'class': 'form-control',
            'accept': 'image/jpeg,image/png,image/jpg,image/heic,image/heif,image/webp',
        }),
    )
    consent = forms.BooleanField(
        required=True,
        label=(
            'I confirm these photos show my real identity and I am a currently enrolled '
            'student at Cavendish University Uganda.'
        ),
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
    )

    def _validate_photo(self, field_name):
        photo = self.cleaned_data.get(field_name)
        if photo:
            if photo.size > MAX_PHOTO_SIZE_BYTES:
                raise ValidationError('File size must be under 5 MB.')
            content_type = getattr(photo, 'content_type', '')
            name = photo.name.lower()
            has_valid_ext = name.endswith(ALLOWED_EXTENSIONS)
            has_valid_type = content_type in ALLOWED_IMAGE_TYPES
            if not has_valid_ext and not has_valid_type:
                raise ValidationError(
                    'Accepted formats: JPG, PNG, HEIC (iPhone), WebP.'
                )
        return photo

    def clean_id_card_photo(self):
        return self._validate_photo('id_card_photo')

    def clean_selfie_photo(self):
        return self._validate_photo('selfie_photo')
