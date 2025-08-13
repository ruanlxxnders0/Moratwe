from django.contrib import admin
from django.urls import path
from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import UserList, Invitee
import pandas as pd
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
import re

class InviteeInline(admin.TabularInline):
    model = Invitee
    extra = 1
    fields = ('email', 'first_name', 'last_name', 'mobile_number', 'guest_category')
    
    def get_formset(self, request, obj=None, **kwargs):
        formset = super().get_formset(request, obj, **kwargs)
        # Add help text to guest_category field
        if 'guest_category' in formset.form.base_fields:
            formset.form.base_fields['guest_category'].help_text = 'Select guest tier level'
        return formset
    
    class Media:
        css = {
            'all': ('admin/css/inline-responsive.css',)
        }

@admin.register(UserList)
class UserListAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at', 'updated_at', 'invitee_count', 'vip_count', 'vvip_count', 'regular_count')
    search_fields = ('name', 'description')
    inlines = [InviteeInline]
    change_list_template = 'admin/userlist_changelist.html'

    def invitee_count(self, obj):
        return obj.invitees.count()
    invitee_count.short_description = 'Total Invitees'

    def vip_count(self, obj):
        count = obj.invitees.filter(guest_category='vip').count()
        if count > 0:
            return mark_safe(f'<span class="guest-count-vip">{count}</span>')
        return count
    vip_count.short_description = 'VIP'

    def vvip_count(self, obj):
        count = obj.invitees.filter(guest_category='vvip').count()
        if count > 0:
            return mark_safe(f'<span class="guest-count-vvip">{count}</span>')
        return count
    vvip_count.short_description = 'VVIP'

    def regular_count(self, obj):
        count = obj.invitees.filter(guest_category='regular').count()
        if count > 0:
            return mark_safe(f'<span class="guest-count-regular">{count}</span>')
        return count
    regular_count.short_description = 'Regular'

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('upload-excel/', self.upload_excel_view, name='userlist-upload-excel'),
        ]
        return custom_urls + urls

    def get_mapped_column(self, df_columns, possible_names):
        """Helper function to find the actual column name from possible variations"""
        # Normalize column names by removing special characters, converting to lowercase
        def normalize_name(name):
            return re.sub(r'[^a-zA-Z0-9\s]', '', str(name).lower().strip()).replace('  ', ' ')
        
        df_columns_normalized = [normalize_name(col) for col in df_columns]
        
        for name in possible_names:
            # Normalize the search name the same way
            search_name = normalize_name(name)
            if search_name in df_columns_normalized:
                return df_columns[df_columns_normalized.index(search_name)]
        return None

    def upload_excel_view(self, request):
        if request.method == 'POST':
            try:
                excel_file = request.FILES['excel_file']
                user_list_id = request.POST.get('user_list_id')
                user_list = UserList.objects.get(id=user_list_id)

                # Define possible column names with extensive variations
                email_columns = ['email', 'email address', 'e-mail', 'mail', 'email id', 'e mail', 'emailaddress']
                first_name_columns = [
                    'first name', 'firstname', 'first_name', 'given name', 'fname', 'name', 'first',
                    'givenname', 'given_name', 'forename', 'christian name'
                ]
                last_name_columns = [
                    'last name', 'lastname', 'last_name', 'surname', 'family name', 'lname', 'last',
                    'familyname', 'family_name', 'sur name'
                ]
                mobile_columns = [
                    'mobile', 'mobile number', 'phone', 'phone number', 'cell', 'cell phone', 
                    'contact', 'mobile_number', 'mobile no', 'phone no', 'contact no', 'tel', 'telephone',
                    'cellphone', 'cell_phone', 'contact number', 'contact_number', 'number',
                    'mobilenumber', 'phonenumber', 'mobile num', 'phone num'
                ]
                category_columns = [
                    'guest category', 'guest_category', 'category', 'type', 'vip status', 'vip_status',
                    'guest type', 'guest_type', 'tier', 'level', 'status', 'priority', 'classification'
                ]

                # Read the Excel file
                if excel_file.name.endswith('.csv'):
                    df = pd.read_csv(excel_file, dtype=str)
                else:
                    df = pd.read_excel(excel_file, dtype=str)

                # Clean up the data - convert NaN to empty string and strip whitespace
                df = df.fillna('')
                
                # Show available columns for debugging
                available_columns = list(df.columns)
                messages.info(request, f'Available columns in uploaded file: {", ".join(available_columns)}')
                
                # Map column names
                email_col = self.get_mapped_column(df.columns, email_columns)
                if not email_col:
                    messages.error(request, f'Excel file must contain an email column. Accepted names: {", ".join(email_columns)}')
                    return HttpResponseRedirect(request.META.get('HTTP_REFERER'))

                first_name_col = self.get_mapped_column(df.columns, first_name_columns)
                last_name_col = self.get_mapped_column(df.columns, last_name_columns)
                mobile_col = self.get_mapped_column(df.columns, mobile_columns)
                category_col = self.get_mapped_column(df.columns, category_columns)

                # Track validation errors
                errors = []
                success_count = 0

                for index, row in df.iterrows():
                    try:
                        # Clean and validate email
                        email_raw = str(row[email_col])
                        if not email_raw:
                            errors.append(f'Row {index + 2}: Email is required')
                            continue
                        
                        # Clean the email: strip whitespace, newlines, tabs, etc.
                        email = email_raw.strip().replace('\n', '').replace('\r', '').replace('\t', '')
                        
                        if not email:
                            errors.append(f'Row {index + 2}: Email is required after cleaning')
                            continue
                        
                        # Additional cleaning for common issues
                        # Remove trailing dots (common Excel issue)
                        if email.endswith('.'):
                            email = email[:-1]
                        
                        # Skip validation for obviously invalid emails
                        if '@' not in email or email.count('@') != 1:
                            errors.append(f'Row {index + 2}: Invalid email format - missing or multiple @ symbols in "{email}"')
                            continue
                        
                        # Split email to check basic structure
                        local_part, domain_part = email.split('@', 1)
                        if not local_part or not domain_part:
                            errors.append(f'Row {index + 2}: Invalid email format - missing local or domain part in "{email}"')
                            continue
                        
                        # Check for common domain issues
                        if domain_part.startswith('.') or domain_part.endswith('.'):
                            errors.append(f'Row {index + 2}: Invalid email format - domain cannot start or end with dot in "{email}"')
                            continue
                        
                        if '..' in domain_part:
                            errors.append(f'Row {index + 2}: Invalid email format - consecutive dots in domain "{email}"')
                            continue
                        
                        # Try Django's validate_email
                        try:
                            validate_email(email)
                        except ValidationError:
                            # Provide more specific error message
                            errors.append(f'Row {index + 2}: Invalid email format "{email}" - please check the email address')
                            continue
                        
                        # Check for duplicate email in the list
                        if Invitee.objects.filter(user_list=user_list, email=email).exists():
                            errors.append(f'Row {index + 2}: Email {email} already exists in this list')
                            continue

                        # Clean up the data before saving
                        mobile = ''
                        if mobile_col and str(row[mobile_col]).strip():
                            mobile_raw = str(row[mobile_col]).strip()
                            
                            # Handle common Excel formatting issues with numbers
                            if isinstance(mobile_raw, float):
                                # Convert scientific notation to string
                                mobile_raw = str(int(mobile_raw))
                            
                            # Remove any potentially harmful characters but preserve +
                            if mobile_raw.startswith('+'):
                                mobile = '+' + re.sub(r'\D', '', mobile_raw[1:])
                            else:
                                mobile = re.sub(r'\D', '', mobile_raw)
                            
                            # Add + prefix for international format if it's long enough
                            if not mobile.startswith('+') and len(mobile) > 10:
                                # This might be a number with country code but missing +
                                # Assuming numbers like these are international
                                mobile = '+' + mobile
                        
                        # Handle guest category
                        guest_category = 'regular'  # Default
                        if category_col and str(row[category_col]).strip():
                            category_value = str(row[category_col]).strip().lower()
                            # Map common variations to our categories
                            if category_value in ['vip', 'v.i.p', 'v.i.p.', 'priority', 'premium']:
                                guest_category = 'vip'
                            elif category_value in ['vvip', 'v.v.i.p', 'v.v.i.p.', 'ultra', 'exclusive', 'top', 'ultra-premium']:
                                guest_category = 'vvip'
                            elif category_value in ['regular', 'standard', 'normal', 'general', 'basic']:
                                guest_category = 'regular'
                            # If none match, keep default 'regular'
                        
                        # Create invitee with cleaned data
                        invitee = Invitee(
                            user_list=user_list,
                            email=email,
                            first_name=str(row[first_name_col]).strip() if first_name_col else '',
                            last_name=str(row[last_name_col]).strip() if last_name_col else '',
                            mobile_number=mobile,
                            guest_category=guest_category
                        )
                        invitee.save()
                        success_count += 1

                    except Exception as e:
                        errors.append(f'Row {index + 2}: {str(e)}')

                if errors:
                    for error in errors:
                        messages.warning(request, error)
                if success_count > 0:
                    messages.success(request, f'Successfully imported {success_count} invitees')

                # Show which columns were mapped
                column_mapping = {
                    'Email': email_col,
                    'First Name': first_name_col or 'Not found',
                    'Last Name': last_name_col or 'Not found',
                    'Mobile Number': mobile_col or 'Not found',
                    'Guest Category': category_col or 'Not found (defaulting to Regular)'
                }
                messages.info(request, f'Column mapping used: {column_mapping}')

            except Exception as e:
                messages.error(request, f'Error processing file: {str(e)}')

            return HttpResponseRedirect(request.META.get('HTTP_REFERER'))

        return HttpResponseRedirect(request.META.get('HTTP_REFERER'))

@admin.register(Invitee)
class InviteeAdmin(admin.ModelAdmin):
    list_display = ('email', 'first_name', 'last_name', 'mobile_number', 'guest_category', 'user_list', 'created_at')
    list_filter = ('user_list', 'guest_category', 'created_at')
    search_fields = ('email', 'first_name', 'last_name', 'mobile_number')
    ordering = ('-created_at',)
    
    fieldsets = (
        (None, {
            'fields': ('user_list', 'email', 'first_name', 'last_name', 'mobile_number')
        }),
        ('Guest Category', {
            'fields': ('guest_category',),
            'description': 'Select the guest category level for this invitee'
        }),
    )
