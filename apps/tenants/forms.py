from django import forms


class RestaurantImportForm(forms.Form):
    import_file = forms.FileField(
        label='Export faylı (.json)',
        help_text='Local bazadan export_restaurant_data ilə çıxarılmış JSON fayl.',
    )
