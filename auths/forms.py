from django import forms



class UserLoginForm(forms.Form):
    email = forms.EmailField()
    password = forms.CharField()


class UserRegisterForm(forms.Form):
    email = forms.EmailField()
    password = forms.CharField()
    password_confirmation = forms.CharField()