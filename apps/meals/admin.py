from apps.printers.models.place import PreparationPlace
from django.contrib import messages
from django import forms
from django.urls import path
from django.shortcuts import render, redirect
from apps.meals.models import Meal
from apps.meals.models import MealCategory
from apps.meals.models import MealGroup
from django.contrib.admin.helpers import ACTION_CHECKBOX_NAME


from django.contrib import admin


admin.site.register(MealGroup)
admin.site.register(MealCategory)


class PreparationPlaceActionForm(forms.Form):
    _selected_action = forms.CharField(widget=forms.MultipleHiddenInput)
    preparation_place = forms.ModelChoiceField(
        queryset=PreparationPlace.objects.all(),
        required=True,
        label="Hazırlanma yeri"
    )


@admin.register(Meal)
class MealAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'preparation_place', 'price']
    list_filter = ['category', 'preparation_place']
    search_fields = ['name', 'description']
    actions = ['set_preparation_place']

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                'set-preparation-place/',
                self.admin_site.admin_view(self.set_preparation_place_view),
                name='set_preparation_place',
            ),
        ]
        return custom_urls + urls

    def set_preparation_place(self, request, queryset):
        selected = request.POST.getlist(ACTION_CHECKBOX_NAME)
        return redirect(
            f"set-preparation-place/?ids={','.join(selected)}"
        )

    set_preparation_place.short_description = "Seçilmiş yeməklərə hazırlanma yeri təyin et"

    def set_preparation_place_view(self, request):
        ids = request.GET.get("ids", "")
        meal_ids = ids.split(",")
        meals = Meal.objects.filter(pk__in=meal_ids)

        if request.method == "POST":
            form = PreparationPlaceActionForm(request.POST)
            if form.is_valid():
                preparation_place = form.cleaned_data['preparation_place']
                meals.update(preparation_place=preparation_place)
                self.message_user(
                    request,
                    f"{meals.count()} yeməyə '{preparation_place}' təyin olundu.",
                    messages.SUCCESS
                )
                return redirect("admin:meals_meal_changelist")
        else:
            form = PreparationPlaceActionForm(
                initial={'_selected_action': ids})

        return render(request, "admin/set_preparation_place.html", {
            'meals': meals,
            'form': form,
            'title': "Hazırlanma yeri təyin et",
            'selected_ids': meal_ids,  # Pass as a list, not a string
        })
