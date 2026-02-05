from django import forms


class RedeemPrizeCodeForm(forms.Form):
    code = forms.CharField(max_length=10, widget=forms.HiddenInput())
