from django import forms
from django.contrib.auth.models import User
from .models import CareReminder, Product, Review


class LoginForm(forms.Form):
    username_or_email = forms.CharField(
        label="Username or Email",
        widget=forms.TextInput(attrs={
            "class": "auth-field-input",
            "placeholder": "Enter username or email address",
            "autocomplete": "off",
            "required": True,
        }),
    )
    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={
            "class": "auth-field-input password-input",
            "placeholder": "Enter your password",
            "autocomplete": "new-password",
            "required": True,
        }),
    )
    remember_me = forms.BooleanField(
        label="Keep me signed in",
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={"class": "auth-checkbox"}),
    )


class RegisterForm(forms.ModelForm):
    first_name = forms.CharField(
        label="Full Name",
        max_length=150,
        widget=forms.TextInput(attrs={
            "class": "auth-field-input",
            "placeholder": "e.g. Rahul Sharma",
            "required": True,
        }),
    )
    username = forms.CharField(
        label="Username",
        max_length=150,
        widget=forms.TextInput(attrs={
            "class": "auth-field-input",
            "placeholder": "Choose a username (e.g. rahul_green)",
            "required": True,
        }),
    )
    email = forms.EmailField(
        label="Email Address",
        widget=forms.EmailInput(attrs={
            "class": "auth-field-input",
            "placeholder": "name@example.com",
            "required": True,
        }),
    )
    password = forms.CharField(
        label="Password",
        min_length=6,
        widget=forms.PasswordInput(attrs={
            "class": "auth-field-input password-input",
            "placeholder": "Create password (min 6 characters)",
            "required": True,
        }),
    )
    password_confirm = forms.CharField(
        label="Confirm Password",
        widget=forms.PasswordInput(attrs={
            "class": "auth-field-input password-input",
            "placeholder": "Re-type your password",
            "required": True,
        }),
    )

    class Meta:
        model = User
        fields = ["first_name", "username", "email"]

    def clean_username(self):
        username = self.cleaned_data.get("username", "").strip()
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("This username is already taken. Please choose another.")
        return username

    def clean_email(self):
        email = self.cleaned_data.get("email", "").strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email address already exists.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        password_confirm = cleaned_data.get("password_confirm")
        if password and password_confirm and password != password_confirm:
            self.add_error("password_confirm", "Passwords do not match. Please verify and try again.")
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user


class CheckoutForm(forms.Form):
    customer_name = forms.CharField(
        max_length=140,
        widget=forms.TextInput(attrs={
            "class": "checkout-field-input",
            "placeholder": "Enter full recipient name",
            "required": True,
        })
    )
    email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={
            "class": "checkout-field-input",
            "placeholder": "Enter email to receive order invoice & receipt",
        })
    )
    phone = forms.CharField(
        max_length=30,
        widget=forms.TextInput(attrs={
            "class": "checkout-field-input",
            "placeholder": "10-digit mobile number for courier tracking",
            "required": True,
        })
    )
    address = forms.CharField(
        widget=forms.Textarea(attrs={
            "class": "checkout-field-input",
            "rows": 3,
            "placeholder": "Flat/House no, Apartment/Building, Street, Area, City, State & PIN code",
            "required": True,
        })
    )
    payment_method = forms.ChoiceField(
        choices=[
            ("cod", "Cash on Delivery (COD)"),
            ("razorpay", "Razorpay Secure (UPI, GPay, Cards, NetBanking)"),
        ],
        widget=forms.RadioSelect(attrs={"class": "payment-radio-input"}),
        initial="cod",
    )
    razorpay_payment_id = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.HiddenInput()
    )


class CouponForm(forms.Form):
    code = forms.CharField(max_length=32)


class CareReminderForm(forms.ModelForm):
    class Meta:
        model = CareReminder
        fields = ["plant_name", "product", "interval_days", "next_reminder"]
        widgets = {
            "next_reminder": forms.DateInput(attrs={"type": "date"}),
            "product": forms.Select(attrs={"required": False}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["product"].queryset = Product.objects.filter(active=True)
        self.fields["product"].required = False


class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ["rating", "comment"]
        widgets = {
            "rating": forms.Select(choices=[(n, f"{n} / 5") for n in range(5, 0, -1)]),
            "comment": forms.Textarea(attrs={"rows": 3}),
        }
