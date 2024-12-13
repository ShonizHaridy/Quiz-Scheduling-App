# # quiz_scheduling_app/urls.py
# from django.urls import path, include
# from rest_framework.routers import DefaultRouter
# from rest_framework_simplejwt.views import TokenRefreshView
# from . import views

# # Initialize router
# router = DefaultRouter()

# # Register ViewSets
# router.register(r'votes', views.VoteViewSet, basename='vote')
# router.register(r'notifications', views.NotificationViewSet, basename='notification')
# router.register(r'sections', views.SectionViewSet, basename='section')
# router.register(r'profile', views.ProfileViewSet, basename='profile')

# urlpatterns = [
#     # Include router URLs
#     path('', include(router.urls)),
    
#     # Auth endpoints (these need to be separate paths since they're not ViewSets)
#     path('auth/register/', views.RegisterView.as_view(), name='register'),
#     path('auth/login/', views.login_view, name='login'),
#     path('auth/verify-otp/', views.verify_otp, name='verify-otp'),
#     path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
#     path('auth/request-password-reset/', views.request_password_reset, name='request-password-reset'),
#     path('auth/verify-reset-otp/', views.verify_reset_otp, name='verify-reset-otp'),
#     path('auth/reset-password/', views.reset_password, name='reset-password'),
    
#     # Course endpoint (since it's a simple function view)
#     path('courses/user-courses/', views.get_user_courses, name='user-courses'),

#     # Student schedule endpoint (since it's a special case)
#     path('students/<int:student_id>/schedule/', views.VoteViewSet.get_student_schedule, name='student-schedule'),
# ]


# quiz_scheduling_app/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from . import views

urlpatterns = [
    # Auth endpoints
    path('auth/register/', views.RegisterView.as_view(), name='register'),
    path('auth/login/', views.login_view, name='login'),
    path('auth/verify-otp/', views.verify_otp, name='verify-otp'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/request-password-reset/', views.request_password_reset, name='request-password-reset'), 
    path('auth/verify-reset-otp/', views.verify_reset_otp, name='verify-reset-otp'), 
    path('auth/reset-password/', views.reset_password, name='reset-password'),
    
    # Profile endpoints
    path('profile/', views.ProfileView.as_view(), name='profile'),
    path('profile/upload-image/', 
         views.ProfileViewSet.as_view({
             'post': 'upload_profile_image'
         }), 
         name='upload-profile-image'),
    
    # Schedule endpoints
    path('sections/upload-schedule/', views.SectionViewSet.as_view({'post': 'upload_schedule'}), name='upload-schedule'),

    path('students/quizzes/', views.get_student_quizzes, name='student-quizzes'),
    
    # Courses endpoint
    path('courses/user-courses/', views.get_user_courses, name='user-courses'),
    
    # Vote endpoints
    path('votes/available-sections/', views.VoteViewSet.as_view({'get': 'available_sections'}), name='available-sections'),
    path('votes/create/', views.VoteViewSet.as_view({'post': 'create_vote'}), name='create-vote'),
    path('votes/all/', views.VoteViewSet.as_view({'get': 'all_votes'}), name='all-votes'),
    path('votes/active/', views.VoteViewSet.as_view({'get': 'active_votes'}), name='active-votes'),
    path('votes/completed/', views.VoteViewSet.as_view({'get': 'completed_votes'}), name='completed-votes'),
    path('votes/<int:pk>/statistics/', views.VoteViewSet.as_view({'get': 'statistics'}), name='vote-statistics'),
    path('votes/<int:pk>/details/', views.VoteViewSet.as_view({'get': 'vote_details'}), name='vote-details'),
    path('votes/<int:pk>/cast-vote/', views.VoteViewSet.as_view({'post': 'cast_vote'}), name='cast-vote'),
    path('votes/<int:pk>/confirm/', views.VoteViewSet.as_view({'post': 'confirm_vote'}), name='confirm-vote'),
    path('votes/<int:pk>/delete/', views.VoteViewSet.as_view({'delete': 'delete_vote'}), name='delete-vote'),
    path('sections/<int:pk>/common-periods/', views.VoteViewSet.as_view({'get': 'common_periods'}), name='common-periods'),
    path('students/<int:student_id>/schedule/', views.VoteViewSet.get_student_schedule, name='student-schedule'),
    
    # Notification endpoints
    path('notifications/', views.NotificationViewSet.as_view({'get': 'list'}), name='notification-list'),
    path('notifications/professor-announcements/', views.NotificationViewSet.as_view({'get': 'professor_announcements'}), name='professor-announcements'),
    path('notifications/create-announcement/', views.NotificationViewSet.as_view({'post': 'create_announcement'}), name='create-announcement'),
    path('notifications/mark-read/<int:pk>/', views.NotificationViewSet.as_view({'post': 'mark_read'}), name='mark-notification-read'),
    path('notifications/mark-all-read/', views.NotificationViewSet.as_view({'post': 'mark_all_read'}), name='mark-all-notifications-read'),
    path('notifications/clear-announcements/', views.NotificationViewSet.as_view({'delete': 'clear_announcements'}),name='clear-announcements'),
    path('notifications/delete-announcement/<int:pk>/', views.NotificationViewSet.as_view({'delete': 'delete_announcement'}), name='delete-announcement'),
]