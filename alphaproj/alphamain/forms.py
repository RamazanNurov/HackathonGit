from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

User = get_user_model()


class RegistrationForm(UserCreationForm):
    name = forms.CharField(label='Ваше имя', max_length=80)
    email = forms.EmailField(label='Email', max_length=150)

    class Meta:
        model = User
        fields = ('name', 'email', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['name'].widget.attrs['autocomplete'] = 'name'
        self.fields['email'].widget.attrs['autocomplete'] = 'email'
        # Fill identity before UserCreationForm validates password similarity.
        self.fields['password1'].label = 'Пароль'
        self.fields['password2'].label = 'Повторите пароль'

    def clean_email(self):
        email = self.cleaned_data['email'].lower()
        if User.objects.filter(username__iexact=email).exists() or User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('Аккаунт с таким email уже существует.')
        return email

    def _post_clean(self):
        self.instance.username = self.cleaned_data.get('email', '')
        self.instance.email = self.cleaned_data.get('email', '')
        self.instance.first_name = self.cleaned_data.get('name', '')
        super()._post_clean()

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = self.cleaned_data['email']
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['name']
        if commit:
            user.save()
        return user


class EmailAuthenticationForm(AuthenticationForm):
    username = forms.EmailField(label='Email', max_length=150, widget=forms.EmailInput(attrs={'autocomplete': 'email', 'autofocus': True}))

    def clean_username(self):
        return self.cleaned_data['username'].lower()
