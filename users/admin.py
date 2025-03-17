from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _

from .models import CustomUser


class CustomUserAdmin(UserAdmin):
    """
    Custom User Admin that uses our CustomUser model.
    """
    model = CustomUser
    list_display = ('email', 'first_name', 'last_name', 'phone_number', 'is_staff', 'is_active', 'is_organizer')
    list_filter = ('is_staff', 'is_active', 'is_organizer')
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name', 'phone_number')}),
        (_('Permissions'), {'fields': ('is_active', 'is_staff', 'is_superuser', 'is_organizer',
                                       'groups', 'user_permissions')}),
        (_('Important dates'), {'fields': ('last_login',)}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'phone_number', 'password1', 'password2', 'is_staff', 'is_active', 'is_organizer')}
        ),
    )
    search_fields = ('email', 'first_name', 'last_name', 'phone_number')
    ordering = ('email',)


admin.site.register(CustomUser, CustomUserAdmin)
