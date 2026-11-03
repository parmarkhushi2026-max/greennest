from django import forms
from django.contrib.auth.models import User
from .models import CareReminder, JournalComment, JournalPost, JournalTag, Product, Review


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


class JournalCommentForm(forms.ModelForm):
    class Meta:
        model = JournalComment
        fields = ["body"]
        widgets = {
            "body": forms.Textarea(attrs={
                "class": "journal-comment-input",
                "rows": 3,
                "placeholder": "Share your thoughts, tips, or experiences about this plant...",
                "required": True,
            }),
        }
        labels = {
            "body": "Your Comment",
        }


class JournalPostForm(forms.ModelForm):
    tags_input = forms.CharField(
        label="Tags (Comma-separated)",
        required=False,
        widget=forms.TextInput(attrs={
            "class": "form-field-input",
            "placeholder": "e.g. Monstera Care, Beginner Tips, Plant Styling",
        }),
    )

    class Meta:
        model = JournalPost
        fields = [
            "title",
            "slug",
            "excerpt",
            "body",
            "cover_image",
            "category",
            "product",
            "status",
            "published_at",
            "seo_title",
            "seo_description",
        ]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-field-input", "placeholder": "Article Title", "required": True}),
            "slug": forms.TextInput(attrs={"class": "form-field-input", "placeholder": "leave blank to auto-generate"}),
            "excerpt": forms.Textarea(attrs={"class": "form-field-input", "rows": 2, "placeholder": "Short summary for preview cards..."}),
            "body": forms.Textarea(attrs={"class": "form-field-input", "rows": 10, "placeholder": "Write full plant article content...", "required": True}),
            "cover_image": forms.URLInput(attrs={"class": "form-field-input", "placeholder": "https://images.unsplash.com/..."}),
            "category": forms.Select(attrs={"class": "form-field-input"}),
            "product": forms.Select(attrs={"class": "form-field-input"}),
            "status": forms.Select(attrs={"class": "form-field-input"}),
            "published_at": forms.DateTimeInput(attrs={"class": "form-field-input", "type": "datetime-local"}),
            "seo_title": forms.TextInput(attrs={"class": "form-field-input", "placeholder": "SEO Title (optional)"}),
            "seo_description": forms.TextInput(attrs={"class": "form-field-input", "placeholder": "Meta Description (optional)"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].required = False
        self.fields["product"].required = False
        self.fields["slug"].required = False
        self.fields["published_at"].required = False
        if self.instance and self.instance.pk:
            self.fields["tags_input"].initial = ", ".join(t.name for t in self.instance.tags.all())

    def save(self, commit=True):
        post = super().save(commit=False)
        if commit:
            post.save()
            tag_names = [t.strip() for t in self.cleaned_data.get("tags_input", "").split(",") if t.strip()]
            tag_objs = []
            for name in tag_names:
                tag, _ = JournalTag.objects.get_or_create(name=name)
                tag_objs.append(tag)
            post.tags.set(tag_objs)
        return post
