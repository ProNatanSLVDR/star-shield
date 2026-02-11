from django import forms


class UserProfileForm(forms.Form):
    first_name = forms.CharField(
        max_length=150,
        required=False,
        label="Prénom",
    )
    last_name = forms.CharField(
        max_length=150,
        required=False,
        label="Nom",
    )
    profile_picture = forms.ImageField(
        required=False,
        label="Photo de profil",
        help_text="Téléchargez une nouvelle photo de profil.",
    )


class ProfilePictureForm(forms.Form):
    profile_picture = forms.ImageField(
        required=False,
        label="Photo de profil",
    )
    delete_profile_picture = forms.BooleanField(
        required=False,
    )
