from django.contrib import admin
from django.urls import path
from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.urls import reverse
from .models import UserList, Invitee
import pandas as pd
from django.core.validators import validate_email
from django.core.exceptions import ValidationError

class InviteeInline(admin.TabularInline):
    model = Invitee
    extra = 1
    fields = ('email', 'first_name', 'last_name', 'mobile_number')

@admin.register(UserList)
class UserListAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at', 'updated_at', 'invitee_count')
    search_fields = ('name', 'description')
    inlines = [InviteeInline]
    change_list_template = 'admin/userlist_changelist.html'

    def invitee_count(self, obj):
        return obj.invitees.count()
    invitee_count.short_description = 'Number of Invitees'

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('upload-excel/', self.upload_excel_view, name='userlist-upload-excel'),
        ]
        return custom_urls + urls

    def get_mapped_column(self, df_columns, possible_names):
        """Helper function to find the actual column name from possible variations"""
        df_columns_lower = [col.lower().strip() for col in df_columns]
        for name in possible_names:
            if name.lower() in df_columns_lower:
                return df_columns[df_columns_lower.index(name.lower())]
        return None

    def upload_excel_view(self, request):
        if request.method == 'POST':
            try:
                excel_file = request.FILES['excel_file']
                user_list_id = request.POST.get('user_list_id')
                user_list = UserList.objects.get(id=user_list_id)

                # Define possible column names
                email_columns = ['email', 'email address', 'e-mail', 'mail', 'email id']
                first_name_columns = ['first name', 'firstname', 'first_name', 'given name']
                last_name_columns = ['last name', 'lastname', 'last_name', 'surname', 'family name']
                mobile_columns = ['mobile', 'mobile number', 'phone', 'phone number', 'contact', 'mobile_number']

                # Read the Excel file
                if excel_file.name.endswith('.csv'):
                    df = pd.read_csv(excel_file, dtype=str)
                else:
                    df = pd.read_excel(excel_file, dtype=str)

                # Clean up the data - convert NaN to empty string and strip whitespace
                df = df.fillna('')
                
                # Map column names
                email_col = self.get_mapped_column(df.columns, email_columns)
                if not email_col:
                    messages.error(request, f'Excel file must contain an email column. Accepted names: {", ".join(email_columns)}')
                    return HttpResponseRedirect(request.META.get('HTTP_REFERER'))

                first_name_col = self.get_mapped_column(df.columns, first_name_columns)
                last_name_col = self.get_mapped_column(df.columns, last_name_columns)
                mobile_col = self.get_mapped_column(df.columns, mobile_columns)

                # Track validation errors
                errors = []
                success_count = 0

                for index, row in df.iterrows():
                    try:
                        # Validate email
                        email = str(row[email_col]).strip()
                        if not email:
                            errors.append(f'Row {index + 2}: Email is required')
                            continue
                            
                        validate_email(email)
                        
                        # Check for duplicate email in the list
                        if Invitee.objects.filter(user_list=user_list, email=email).exists():
                            errors.append(f'Row {index + 2}: Email {email} already exists in this list')
                            continue

                        # Create invitee with cleaned data
                        invitee = Invitee(
                            user_list=user_list,
                            email=email,
                            first_name=str(row[first_name_col]).strip() if first_name_col else '',
                            last_name=str(row[last_name_col]).strip() if last_name_col else '',
                            mobile_number=str(row[mobile_col]).strip() if mobile_col else '',
                            rsvp_status='pending'  # Set default RSVP status
                        )
                        invitee.save()
                        success_count += 1

                    except ValidationError:
                        errors.append(f'Row {index + 2}: Invalid email format for {row[email_col]}')
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
                    'Mobile Number': mobile_col or 'Not found'
                }
                messages.info(request, f'Column mapping used: {column_mapping}')

            except Exception as e:
                messages.error(request, f'Error processing file: {str(e)}')

            return HttpResponseRedirect(request.META.get('HTTP_REFERER'))

        return HttpResponseRedirect(request.META.get('HTTP_REFERER'))

@admin.register(Invitee)
class InviteeAdmin(admin.ModelAdmin):
    list_display = ('email', 'first_name', 'last_name', 'mobile_number', 'user_list', 'created_at')
    list_filter = ('user_list', 'created_at')
    search_fields = ('email', 'first_name', 'last_name', 'mobile_number')
    ordering = ('-created_at',)
