from django import forms

class NewIPAAccountForm(forms.Form):
    
    # First name
    first_name = forms.CharField(widget=forms.TextInput(attrs={'placeholder': 'First Name', 'style': 'width: 300px;', 'class': 'form-control'}))
    # Last name
    last_name = forms.CharField(widget=forms.TextInput(attrs={'placeholder': 'Last Name', 'style': 'width: 300px;', 'class': 'form-control'}))
    # Company
    company = forms.CharField(widget=forms.TextInput(attrs={'placeholder': 'Company', 'style': 'width: 300px;', 'class': 'form-control'}))
    # Email
    email = forms.CharField(widget=forms.TextInput(attrs={'placeholder': 'Email', 'style': 'width: 300px;', 'class': 'form-control', "readonly": True}))

class ReadOnlyIPAAccountForm(forms.Form):
    # IPA Username
    ipa_username = forms.CharField(required=False, widget=forms.TextInput(attrs={'placeholder': 'IPA Username', 'style': 'width: 300px;', 'class': 'form-control', "readonly": True}))
    # First name
    first_name = forms.CharField(required=False, widget=forms.TextInput(attrs={'placeholder': 'First Name', 'style': 'width: 300px;', 'class': 'form-control', "readonly": True}))
    # Last name
    last_name = forms.CharField(required=False, widget=forms.TextInput(attrs={'placeholder': 'Last Name', 'style': 'width: 300px;', 'class': 'form-control', "readonly": True}))
    # Company
    company = forms.CharField(required=False, widget=forms.TextInput(attrs={'placeholder': 'Company', 'style': 'width: 300px;', 'class': 'form-control', "readonly": True}))
    # Email
    email = forms.CharField(required=False, widget=forms.TextInput(attrs={'placeholder': 'Email', 'style': 'width: 300px;', 'class': 'form-control', "readonly": True}))

class ConflictIPAAcountForm(forms.Form):
    # IPA Username
    ipa_username = forms.CharField(widget=forms.TextInput(attrs={'placeholder': 'IPA Username', 'style': 'width: 300px;', 'class': 'form-control'}))
    # First name
    first_name = forms.CharField(widget=forms.TextInput(attrs={'placeholder': 'First Name', 'style': 'width: 300px;', 'class': 'form-control'}))
    # Last name
    last_name = forms.CharField(widget=forms.TextInput(attrs={'placeholder': 'Last Name', 'style': 'width: 300px;', 'class': 'form-control'}))
    # Company
    company = forms.CharField(widget=forms.TextInput(attrs={'placeholder': 'Company', 'style': 'width: 300px;', 'class': 'form-control'}))
    # Email
    email = forms.CharField(widget=forms.TextInput(attrs={'placeholder': 'Email', 'style': 'width: 300px;', 'class': 'form-control', "readonly": True}))

class SetCompanyForm(forms.Form):
    # Company
    company = forms.CharField(required=True, widget=forms.TextInput(attrs={'placeholder': 'Company', 'style': 'width: 300px;', 'class': 'form-control'}))

class SetSSHForm(forms.Form):
    # SSH key
    ssh_public_key = forms.CharField(required=True, widget=forms.Textarea(attrs={'placeholder': 'SSH Public Key', 'style': 'width: 300px;', 'class': 'form-control'}))


