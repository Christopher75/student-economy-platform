from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, PasswordChangeForm
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

User = get_user_model()


class RegistrationForm(UserCreationForm):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your university email',
            'autocomplete': 'email',
        }),
        help_text='Use your official university email address.',
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
            'placeholder': 'e.g. 21/U/1234',
        }),
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
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '+256 700 000000',
        }),
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
        if User.objects.filter(email=email).exists():
            raise ValidationError('A student account with this email already exists.')
        return email

    def clean_student_id(self):
        student_id = self.cleaned_data.get('student_id', '').strip()
        if User.objects.filter(student_id=student_id).exists():
            raise ValidationError('This student ID is already registered.')
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
