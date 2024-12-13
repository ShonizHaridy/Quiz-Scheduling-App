from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import (
    User, Period, Course, Schedule, Vote, 
    VoteOption, StudentVote, Notification, OTPCode
)

class CustomUserAdmin(UserAdmin):
    list_display = ('university_id', 'email', 'first_name', 'last_name', 'user_type')
    search_fields = ('university_id', 'email', 'first_name', 'last_name')
    ordering = ('university_id',)

admin.site.register(User, CustomUserAdmin)
admin.site.register(Period)
admin.site.register(Course)
admin.site.register(Schedule)
admin.site.register(Vote)
admin.site.register(VoteOption)
admin.site.register(StudentVote)
admin.site.register(Notification)
admin.site.register(OTPCode)