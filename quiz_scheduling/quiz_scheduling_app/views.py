from typing import Dict
from django_q.tasks import schedule
from rest_framework import viewsets, status, generics
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.serializers import ValidationError  # Add this import
import string  # Needed for password reset token generation
from django.core.cache import cache  # Needed for password reset cache
from django.shortcuts import get_object_or_404
from django.contrib.auth import authenticate
from django.utils import timezone
from django.db.models import Q
from rest_framework_simplejwt.tokens import RefreshToken
import pyotp
import random
from datetime import datetime, timedelta
from .services.common_time_service import CommonTimeService
from django.db.models import Prefetch
import os
from django.db import transaction  # Correct import
from rest_framework.decorators import action
import logging
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser

logger = logging.getLogger(__name__)

# from quiz_scheduling.courses import serializers

from .models import (
    ProfessorAnnouncement, Quiz, Schedule, Section, User, Course, Period, Vote, VoteOption, 
    StudentVote, Notification, OTPCode
)
from .serializers import (
    PasswordResetSerializer, UserRegisterSerializer, CourseSerializer,
    VoteSerializer, CreateVoteSerializer, StudentVoteSerializer,
    NotificationSerializer, LoginSerializer, OTPVerificationSerializer,
    
)
from .services.pdf_processor import PDFProcessor
from .services.notification_service import NotificationService
from .services.email_service import EmailService
from rest_framework_simplejwt.tokens import RefreshToken


from .serializers import (
    UserRegisterSerializer, UserSerializer, CourseSerializer,
    SectionSerializer, VoteSerializer, CreateVoteSerializer, 
    StudentVoteSerializer, NotificationSerializer, LoginSerializer, 
    OTPVerificationSerializer, CreateAnnouncementSerializer
)
from .services.pdf_processor import PDFProcessor
from .services.email_service import EmailService

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserRegisterSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        try:
            if serializer.is_valid():
                serializer.save()  # This will use the create method from your serializer
                return Response({
                    "status": "success",
                    "message": "User registered successfully",
                    "data": serializer.data
                }, status=status.HTTP_201_CREATED)
            return Response({
                "status": "error",
                "message": "Registration failed",
                "errors": serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                "status": "error",
                "message": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user

@api_view(['POST'])
def login_view(request):
    serializer = LoginSerializer(data=request.data)
    if serializer.is_valid():
        user = authenticate(
            university_id=serializer.validated_data['university_id'],
            password=serializer.validated_data['password']
        )
        
        if user:
            # Generate 6-digit OTP
            otp = ''.join([str(random.randint(0, 9)) for _ in range(6)])
            
            # Save OTP to database
            OTPCode.objects.create(
                user=user,
                code=otp,
                expires_at=timezone.now() + timedelta(minutes=5)
            )
            
            # Send OTP via email
            EmailService.send_otp_email(user.email, otp)
            
            return Response({
                "status": "success",
                "message": "OTP sent to your registered email"
            })
        
        return Response({
            "status": "error",
            "message": "Invalid credentials"
        }, status=status.HTTP_401_UNAUTHORIZED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
def verify_otp(request):
    serializer = OTPVerificationSerializer(data=request.data)
    print("data for otp verification is", request.data)
    if serializer.is_valid():
        try:
            user = User.objects.get(
                university_id=serializer.validated_data['university_id']
            )
            otp_obj = OTPCode.objects.filter(
                user=user,
                code=serializer.validated_data['otp_code'],
                is_used=False,
                expires_at__gt=timezone.now()
            ).latest('created_at')
            
            otp_obj.is_used = True
            otp_obj.save()
            
            refresh = RefreshToken.for_user(user)
            return Response({
                "status": "success",
                "tokens": {
                    "access": str(refresh.access_token),
                    "refresh": str(refresh)
                },
                "user": UserSerializer(user, context={'request': request}).data  # Pass context
            })
            
        except (User.DoesNotExist, OTPCode.DoesNotExist):
            return Response({
                "status": "error",
                "message": "Invalid OTP or user"
            }, status=status.HTTP_400_BAD_REQUEST)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)





@api_view(['POST'])
def request_password_reset(request):
    """First stage: Request password reset and send OTP"""
    email = request.data.get('email')
    try:
        user = User.objects.get(email=email)
        # Generate 6-digit OTP
        otp = ''.join([str(random.randint(0, 9)) for _ in range(6)])
        
        # Save OTP in database
        OTPCode.objects.create(
            user=user,
            code=otp,
            expires_at=timezone.now() + timedelta(minutes=15)
        )
        
        # Send OTP via email
        EmailService.send_password_reset_email(email, otp)
        
        return Response({
            "status": "success",
            "message": "Reset code sent to your email"
        })
    except User.DoesNotExist:
        return Response({
            "status": "error",
            "message": "No user found with this email"
        }, status=status.HTTP_404_NOT_FOUND)

@api_view(['POST'])
def verify_reset_otp(request):
    """Second stage part 1: Verify OTP"""
    email = request.data.get('email')
    otp = request.data.get('otp')
    
    try:
        user = User.objects.get(email=email)
        otp_obj = OTPCode.objects.filter(
            user=user,
            code=otp,
            is_used=False,
            expires_at__gt=timezone.now()
        ).latest('created_at')
        
        otp_obj.is_used = True
        otp_obj.save()
        
        # Generate a temporary token for password reset
        temp_token = ''.join(random.choices(string.ascii_letters + string.digits, k=32))
        cache.set(f'pwd_reset_{temp_token}', user.id, timeout=300)  # 5 minutes expiry
        
        return Response({
            "status": "success",
            "message": "OTP verified successfully",
            "reset_token": temp_token
        })
    except (User.DoesNotExist, OTPCode.DoesNotExist):
        return Response({
            "status": "error",
            "message": "Invalid OTP or email"
        }, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
def reset_password(request):
    """Second stage part 2: Set new password"""
    reset_token = request.data.get('reset_token')
    new_password = request.data.get('new_password')
    confirm_password = request.data.get('confirm_password')
    
    if new_password != confirm_password:
        return Response({
            "status": "error",
            "message": "Passwords don't match"
        }, status=status.HTTP_400_BAD_REQUEST)
    
    user_id = cache.get(f'pwd_reset_{reset_token}')
    if not user_id:
        return Response({
            "status": "error",
            "message": "Invalid or expired reset token"
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        user = User.objects.get(id=user_id)
        user.set_password(new_password)
        user.save()
        
        # Clear the reset token
        cache.delete(f'pwd_reset_{reset_token}')
        
        return Response({
            "status": "success",
            "message": "Password reset successful"
        })
    except User.DoesNotExist:
        return Response({
            "status": "error",
            "message": "User not found"
        }, status=status.HTTP_404_NOT_FOUND)
    

@api_view(['GET'])
def get_student_quizzes(request):
    """Get all quizzes for the current student"""
    try:
        quizzes = Quiz.objects.filter(
            section__students=request.user,
        ).select_related(
            'section',
            'section__course',
            'period'
        ).order_by('date', 'period__number')

        return Response({
            "status": "success",
            "quizzes": [
                {
                    "id": quiz.id,
                    "course": {
                        "code": quiz.section.course.code,
                        "name": quiz.section.course.name,
                    },
                    "section_number": quiz.section.section_number,
                    "date": quiz.date,
                    "period": {
                        "number": quiz.period.number,
                        "start_time": quiz.period.start_time.strftime('%H:%M'),
                        "end_time": quiz.period.end_time.strftime('%H:%M'),
                        "is_online": quiz.period.is_online,
                    },
                    "room": quiz.room,
                }
                for quiz in quizzes
            ]
        })
    except Exception as e:
        return Response({
            "status": "error",
            "message": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SectionViewSet(viewsets.ModelViewSet):
    serializer_class = SectionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.user_type == 'faculty':
            return Section.objects.filter(professor=user)
        return Section.objects.filter(students=user)

    @action(detail=False, methods=['POST'])
    def upload_schedule(self, request):
        """Upload and process schedule PDF"""
        if 'file' not in request.FILES:
            return Response({
                "status": "error",
                "message": "No file provided"
            }, status=status.HTTP_400_BAD_REQUEST)

        pdf_file = request.FILES['file']
        if not pdf_file.name.endswith('.pdf'):
            return Response({
                "status": "error",
                "message": "File must be a PDF"
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Process based on user type
            if request.user.user_type == 'faculty':
                # Start transaction
                with transaction.atomic():
                    print("just here")
                    # Get all sections where this professor teaches
                    old_sections = Section.objects.filter(professor=request.user)
                    print(old_sections)
                    
                    # Get all votes associated with this professor
                    votes_to_delete = Vote.objects.filter(professor=request.user)


                    Notification.objects.filter(Q(notification_type='announcement'), sender_id=request.user.id).delete()
                    Notification.objects.filter(section__in=old_sections, notification_type='announcement').delete()


                    announcements_to_delete = ProfessorAnnouncement.objects.filter(professor=request.user)
                    print(announcements_to_delete)
                    ProfessorAnnouncement.objects.filter(professor=request.user).delete()

                    # Notification.objects.filter(Q(notification_type='announcement'), professor = request.user)
                    
                    # For each vote, delete related data
                    for vote in votes_to_delete:
                        # Delete notifications related to the vote
                        Notification.objects.filter(
                            Q(notification_type='vote_created') |
                            Q(notification_type='vote_completed'),
                            vote=vote
                        ).delete()
                        
                        
                        # Delete student votes
                        StudentVote.objects.filter(vote=vote).delete()
                        
                        # Delete vote options
                        VoteOption.objects.filter(vote=vote).delete()
                        
                        # Delete quizzes related to the vote
                        Quiz.objects.filter(
                            section=vote.section,
                            date__in=[opt.date for opt in vote.options.all()],
                        ).delete()
                    
                    # Finally delete the votes
                    votes_to_delete.delete()
                    
                    print("Votes to delete:", votes_to_delete.count())
                    print("SQL Query:", votes_to_delete.query)

                    # Clear professor assignments
                    old_sections.update(professor=None)
                    print("Deleted all")
                    # Process new schedule
                    result = PDFProcessor.process_faculty_schedule(
                        pdf_file,
                        request.user.university_id
                    )
            else:
                print("we are here")
                result = PDFProcessor.process_student_schedule(
                    pdf_file,
                    request.user.university_id
                )

            return Response(result,
                status=status.HTTP_200_OK if result["status"] == "success"
                else status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            print(f"Error processing PDF: {str(e)}")
            return Response({
                "status": "error",
                "message": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        





class VoteViewSet(viewsets.ModelViewSet):
    serializer_class = VoteSerializer
    permission_classes = [IsAuthenticated]
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    def get_queryset(self):
        user = self.request.user
        if user.user_type == 'faculty':
            return Vote.objects.filter(professor=user)
        return Vote.objects.filter(section__students=user)

    @action(detail=False, methods=['GET'])
    def available_sections(self, request):
        """Get sections where professor can create votes"""
        if request.user.user_type != 'faculty':
            return Response({
                "status": "error",
                "message": "Only faculty can access this endpoint"
            }, status=status.HTTP_403_FORBIDDEN)
        
        sections = Section.objects.filter(professor=request.user)
        return Response({
            "status": "success",
            "sections": SectionSerializer(sections, many=True).data
        })

    # quiz_scheduling_app/views.py

    @action(detail=True, methods=['GET'])
    def common_periods(self, request, pk=None):
        print("This is request")
        print(request.data)
        print(request.query_params)
        try:
            section = get_object_or_404(Section, id=pk)

            if section.professor != request.user:
                return Response({
                    "status": "error",
                    "message": "Not authorized for this section"
                }, status=status.HTTP_403_FORBIDDEN)

            # Get date from query params
            date_str = request.query_params.get('date')
            if not date_str:
                return Response({
                    "status": "error",
                    "message": "Date parameter is required"
                }, status=status.HTTP_400_BAD_REQUEST)

            try:
                date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                return Response({
                    "status": "error",
                    "message": "Invalid date format. Use YYYY-MM-DD"
                }, status=status.HTTP_400_BAD_REQUEST)

            # Instead of sending the date object directly, get the day name first
            day = date.strftime('%A').lower()
            
            result = CommonTimeService.get_available_periods(pk, date)
            return Response(result)

        except Exception as e:
            return Response({
                "status": "error",
                "message": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

 

    @action(detail=False, methods=['POST'])
    def create_vote(self, request):
        try:
            section_id = request.data.get('section_id')
            options = request.data.get('options', [])
            duration = request.data.get('duration', 1)

            section = Section.objects.get(id=section_id, professor=request.user)

            vote = Vote.objects.create(
                section=section,
                professor=request.user,
                is_active=True,
                duration=duration
            )

            # Create vote options
            for option in options:
                VoteOption.objects.create(
                    vote=vote,
                    date=option['date'],
                    period_id=option['period_id']
                )

            # Schedule automatic completion
            schedule(
                'quiz_scheduling_app.tasks.complete_expired_votes',
                schedule_type='O',
                next_run=timezone.now() + timezone.timedelta(days=duration)
            )

            # Sending vote created notification to all students
            NotificationService.send_vote_created_notification(vote)

            return Response({
                "status": "success",
                "message": "Vote created successfully",
                "vote": VoteSerializer(vote).data
            })

        except Section.DoesNotExist:
            return Response({
                "status": "error",
                "message": "Section not found or not authorized"
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Internal server error: {str(e)}")
            return Response({
                "status": "error",
                "message": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['GET'])
    def active_votes(self, request):
        try:
            if request.user.user_type == 'faculty':
                votes = Vote.objects.filter(
                    professor=request.user,
                    is_active=True
                )
            else:
                votes = Vote.objects.filter(
                    section__students=request.user,
                    is_active=True
                )

            serializer = VoteSerializer(votes, many=True, context={'request': request})
            


            return Response({
                "status": "success",
                "votes": serializer.data
            })
        except Exception as e:
            return Response({
                "status": "error",
                "message": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['GET'])
    def completed_votes(self, request):
        try:
            if request.user.user_type == 'faculty':
                votes = Vote.objects.filter(
                    professor=request.user,
                    is_active=False
                )
            else:
                votes = Vote.objects.filter(
                    section__students=request.user,
                    is_active=False
                )

            serializer = VoteSerializer(votes, many=True, context={'request': request})
            
            return Response({
                "status": "success",
                "votes": serializer.data
            })
        except Exception as e:
            return Response({
                "status": "error",
                "message": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        

    @action(detail=False, methods=['GET'])
    def all_votes(self, request):
        """Get all votes with optional filtering"""
        try:
            # Get query parameters
            is_active = request.query_params.get('is_active')
            course_id = request.query_params.get('course_id')
            section_id = request.query_params.get('section_id')

            # Base queryset
            if request.user.user_type == 'faculty':
                votes = Vote.objects.filter(professor=request.user)
            else:
                votes = Vote.objects.filter(section__students=request.user)

            # Apply filters if provided
            if is_active is not None:
                votes = votes.filter(is_active=is_active.lower() == 'true')
            if course_id:
                votes = votes.filter(section__course_id=course_id)
            if section_id:
                votes = votes.filter(section_id=section_id)

            # Include related data
            votes = votes.select_related(
                'section',
                'section__course',
                'selected_period'
            ).prefetch_related(
                'options',
                'options__period'
            )

            return Response({
                "status": "success",
                "votes": VoteSerializer(votes, many=True).data
            })
        except Exception as e:
            return Response({
                "status": "error",
                "message": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        

    @action(detail=True, methods=['GET'])
    def statistics(self, request, pk=None):
        try:
            vote = self.get_object()
            
            if vote.professor != request.user:
                return Response({
                    "status": "error",
                    "message": "Not authorized to view statistics"
                }, status=status.HTTP_403_FORBIDDEN)

            options_data = []
            total_votes = sum(option.studentvote_set.count() for option in vote.options.all())

            for option in vote.options.all():
                vote_count = option.studentvote_set.count()
                percentage = (vote_count / total_votes * 100) if total_votes > 0 else 0
                
                voters_data = []
                if request.user.user_type == 'faculty':
                    for student_vote in option.studentvote_set.all():
                        voters_data.append({
                            'id': student_vote.student.id,
                            'name': f"{student_vote.student.first_name} {student_vote.student.last_name}",
                            'university_id': student_vote.student.university_id
                        })

                options_data.append({
                    'option_id': option.id,
                    'date': option.date,
                    'period': {
                        'number': option.period.number,
                        'start_time': option.period.start_time.strftime('%H:%M'),
                        'end_time': option.period.end_time.strftime('%H:%M'),
                        'is_online': option.period.is_online
                    },
                    'vote_count': vote_count,
                    'percentage': round(percentage, 2),
                    'voters': voters_data if request.user.user_type == 'faculty' else None
                })

            return Response({
                "status": "success",
                "vote_id": vote.id,
                "total_votes": total_votes,
                "options": options_data,
                "is_completed": vote.isCompleted
            })

        except Exception as e:
            return Response({
                "status": "error",
                "message": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['GET'])
    def vote_details(self, request, pk=None):
        """Get detailed vote information including student votes"""
        vote = self.get_object()
        
        if vote.professor != request.user and request.user not in vote.section.students.all():
            return Response({
                "status": "error",
                "message": "Not authorized to view this vote"
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Get vote statistics
        options_data = []
        for option in vote.options.all():
            student_votes = StudentVote.objects.filter(option=option)
            voters = []
            
            if request.user.user_type == 'faculty':
                # Include student details for faculty
                for sv in student_votes:
                    voters.append({
                        "id": sv.student.id,
                        "name": f"{sv.student.first_name} {sv.student.last_name}",
                        "university_id": sv.student.university_id
                    })
            
            options_data.append({
                "id": option.id,
                "day": option.day,
                "period": {
                    "number": option.period.number,
                    "start_time": option.period.start_time.strftime('%H:%M'),
                    "end_time": option.period.end_time.strftime('%H:%M'),
                    "is_online": option.period.number >= 9
                },
                "vote_count": student_votes.count(),
                "voters": voters if request.user.user_type == 'faculty' else None
            })
        
        return Response({
            "status": "success",
            "vote": {
                "id": vote.id,
                "section": SectionSerializer(vote.section).data,
                "is_active": vote.is_active,
                "created_at": vote.created_at,
                "options": options_data,
                "selected_option": vote.selected_period_id,
                "room": vote.room
            }
        })

    @action(detail=True, methods=['POST'])
    def cast_vote(self, request, pk=None):
        try:
            vote = self.get_object()  # This will now work with get_queryset
            if request.user.user_type != 'student':
                return Response({
                    "status": "error",
                    "message": "Only students can cast votes"
                }, status=status.HTTP_403_FORBIDDEN)

            # Check if vote is still active
            if not vote.is_active:
                return Response({
                    "status": "error",
                    "message": "This vote is no longer active"
                }, status=status.HTTP_400_BAD_REQUEST)

            # Check if student is enrolled in the section
            if not vote.section.students.filter(id=request.user.id).exists():
                return Response({
                    "status": "error",
                    "message": "You are not enrolled in this section"
                }, status=status.HTTP_403_FORBIDDEN)

            # Check if student has already voted
            if StudentVote.objects.filter(vote=vote, student=request.user).exists():
                return Response({
                    "status": "error",
                    "message": "You have already voted"
                }, status=status.HTTP_400_BAD_REQUEST)

            option_id = request.data.get('option_id')
            try:
                option = vote.options.get(id=option_id)
            except VoteOption.DoesNotExist:
                return Response({
                    "status": "error",
                    "message": "Invalid option"
                }, status=status.HTTP_400_BAD_REQUEST)

            # Create the vote
            StudentVote.objects.create(
                vote=vote,
                student=request.user,
                option=option
            )

            return Response({
                "status": "success",
                "message": "Vote cast successfully"
            })

        except Exception as e:
            return Response({
                "status": "error",
                "message": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['POST'])
    def confirm_vote(self, request, pk=None):
        try:
            vote = self.get_object()

            if vote.professor != request.user:
                return Response({
                    "status": "error",
                    "message": "Not authorized to confirm this vote"
                }, status=status.HTTP_403_FORBIDDEN)

            option_id = request.data.get('option_id')
            room = request.data.get('room')

            if not option_id:
                return Response({
                    "status": "error",
                    "message": "Option ID is required"
                }, status=status.HTTP_400_BAD_REQUEST)

            if not room:
                return Response({
                    "status": "error",
                    "message": "Room number is required"
                }, status=status.HTTP_400_BAD_REQUEST)

            try:
                option = vote.options.get(id=option_id)
            except VoteOption.DoesNotExist:
                return Response({
                    "status": "error",
                    "message": "Invalid option ID"
                }, status=status.HTTP_400_BAD_REQUEST)

            # Validate quiz time
            try:
                is_valid, error_message = vote.validate_quiz_time(option)
                if not is_valid:
                    return Response({
                        "status": "error",
                        "message": error_message,
                        "error_type": "quiz_conflict"  # Add error type for specific handling
                    }, status=status.HTTP_400_BAD_REQUEST)

                # Start a transaction to ensure both vote and quiz are saved or neither is
                with transaction.atomic():
                    # Update the vote
                    vote.selected_option = option
                    vote.room = room
                    vote.is_active = False
                    vote.save()

                    # Create the quiz
                    Quiz.objects.create(
                        section=vote.section,
                        date=option.date,
                        period=option.period,
                        room=room,
                        created_at=timezone.now()
                    )

                # Send notifications
                NotificationService.send_vote_completed_notification(vote)

                return Response({
                    "status": "success",
                    "message": "Quiz time confirmed successfully"
                })

            except ValidationError as e:
                logger.warning(f"Validation error during vote confirmation: {str(e)}")
                return Response({
                    "status": "error",
                    "message": str(e),
                    "error_type": "validation_error"
                }, status=status.HTTP_400_BAD_REQUEST)

            except Exception as e:
                logger.error(f"Error during vote confirmation: {str(e)}", exc_info=True)
                return Response({
                    "status": "error",
                    "message": "An error occurred while confirming the quiz time. Please try again."
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        except Exception as e:
            logger.error(f"Unexpected error in confirm_vote: {str(e)}", exc_info=True)
            return Response({
                "status": "error",
                "message": "An unexpected error occurred. Please try again."
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



    @action(detail=True, methods=['DELETE'])
    def delete_vote(self, request, pk=None):
        """Delete a vote and all related data"""
        try:
            vote = self.get_object()
            
            # Check if user is authorized to delete this vote
            if vote.professor != request.user:
                return Response({
                    "status": "error",
                    "message": "Not authorized to delete this vote"
                }, status=status.HTTP_403_FORBIDDEN)
            
            # Use transaction to ensure all related data is deleted
            with transaction.atomic():
                # Delete related notifications
                Notification.objects.filter(
                    Q(notification_type='vote_created') | 
                    Q(notification_type='vote_completed'),
                    vote=vote
                ).delete()
                
                # Delete student votes
                StudentVote.objects.filter(vote=vote).delete()
                
                # Delete vote options
                VoteOption.objects.filter(vote=vote).delete()
                
                # Delete the vote itself
                vote.delete()
            
            return Response({
                "status": "success",
                "message": "Vote deleted successfully"
            })
            
        except Exception as e:
            return Response({
                "status": "error",
                "message": f"Failed to delete vote: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
        
        
    @api_view(['GET'])
    def get_student_schedule(request, student_id):
        """Get schedule for a specific student"""
        try:
            print(f"Fetching schedule for student ID: {student_id}") # Debug print

            # Check if user is faculty
            if request.user.user_type != 'faculty':
                return Response({
                    "status": "error",
                    "message": "Not authorized to view student schedules"
                }, status=status.HTTP_403_FORBIDDEN)

            # Get student
            student = User.objects.get(id=student_id, user_type='student')
            
            # Get student's sections with related data
            student_sections = Section.objects.filter(
                students=student
            ).values_list('id', flat=True)

            # Get all confirmed quiz times for these sections
            quizzes = Quiz.objects.filter(
                section_id__in=student_sections,
                date__gte=timezone.now().date()
            ).select_related(
                'section',
                'section__course',
                'period'
            ).order_by('date', 'period__number')

            # Get regular schedule
            sections = Section.objects.filter(
                students=student
            ).select_related(
                'course'
            ).prefetch_related(
                'schedules',
                'schedules__period'
            )

            # Organize schedule by days
            schedule_data = {
                'sunday': [],
                'monday': [],
                'tuesday': [],
                'wednesday': [],
                'thursday': []
            }

            # Add regular classes
            for section in sections:
                for schedule in section.schedules.all():
                    schedule_data[schedule.day].append({
                        'course': {
                            'code': section.course.code,
                            'name': section.course.name
                        },
                        'section_number': section.section_number,
                        'activity_type': section.activity_type,
                        'period': {
                            'number': schedule.period.number,
                            'start_time': schedule.period.start_time.strftime('%H:%M'),
                            'end_time': schedule.period.end_time.strftime('%H:%M'),
                            'is_online': schedule.period.is_online
                        },
                        'is_quiz': False
                    })

            # Add quizzes to schedule
            for quiz in quizzes:
                quiz_day = quiz.date.strftime('%A').lower()
                if quiz_day in schedule_data:
                    schedule_data[quiz_day].append({
                        'course': {
                            'code': quiz.section.course.code,
                            'name': quiz.section.course.name
                        },
                        'section_number': quiz.section.section_number,
                        'activity_type': 'Quiz',
                        'period': {
                            'number': quiz.period.number,
                            'start_time': quiz.period.start_time.strftime('%H:%M'),
                            'end_time': quiz.period.end_time.strftime('%H:%M'),
                            'is_online': quiz.period.is_online
                        },
                        'is_quiz': True,
                        'quiz_date': quiz.date.strftime('%Y-%m-%d'),
                        'room': quiz.room
                    })

            return Response({
                "status": "success",
                "student": {
                    "name": f"{student.first_name} {student.last_name}",
                    "university_id": student.university_id
                },
                "schedule": schedule_data
            })

        except User.DoesNotExist:
            return Response({
                "status": "error",
                "message": "Student not found"
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            print(f"Error in get_student_schedule: {str(e)}")
            return Response({
                "status": "error",
                "message": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)






class NotificationViewSet(viewsets.ModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        print("DEBUG: get_queryset called")
        user = self.request.user

        if user.user_type == 'faculty':
            # For faculty, get announcements they've sent
            return Notification.objects.filter(
                sender=user,
                notification_type='announcement'
            ).order_by('-created_at').distinct()
        else:
            # For students, get all notifications where they are the recipient
            return Notification.objects.filter(recipient=user).order_by('-created_at')
    
    @action(detail=False, methods=['GET'])
    def list(self, request):
        print("DEBUG: List method called")
        print(f"DEBUG: Current user: {request.user.university_id}")
        print(f"DEBUG: User type: {request.user.user_type}")
        
        notifications = self.get_queryset()
        print(f"DEBUG: Found {notifications.count()} notifications")
        
        serializer = self.get_serializer(notifications, many=True)
        return Response({
            "status": "success",
            "notifications": serializer.data
        })

    @action(detail=False, methods=['POST'])
    def create_announcement(self, request):
        """Create a new announcement for a section"""
        print("DEBUG: Create announcement called")
        if request.user.user_type != 'faculty':
            return Response({
                "status": "error",
                "message": "Only faculty can create announcements"
            }, status=status.HTTP_403_FORBIDDEN)

        try:
            section_id = request.data.get('section_id')
            title = request.data.get('title')
            message = request.data.get('message')

            if not all([section_id, title, message]):
                return Response({
                    "status": "error",
                    "message": "Section ID, title and message are required"
                }, status=status.HTTP_400_BAD_REQUEST)

            section = Section.objects.get(id=section_id)
            if section.professor != request.user:
                return Response({
                    "status": "error",
                    "message": "Not authorized for this section"
                }, status=status.HTTP_403_FORBIDDEN)

            with transaction.atomic():
                # Create ProfessorAnnouncement record
                announcement = ProfessorAnnouncement.objects.create(
                    professor=request.user,
                    section=section,
                    title=title,
                    message=message
                )

                # Create notifications for all students in section
                notifications = []
                for student in section.students.all():
                    notification = Notification.objects.create(
                        recipient=student,
                        sender=request.user,
                        notification_type='announcement',
                        title=title,
                        message=message,
                        section=section,
                        announcement_id=announcement.id  
                    )
                    notifications.append(notification)

                print(f"DEBUG: Created announcement and {len(notifications)} notifications")

                return Response({
                    "status": "success",
                    "message": f"Announcement sent to {len(notifications)} students"
                })

        except Section.DoesNotExist:
            return Response({
                "status": "error",
                "message": "Section not found"
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            print(f"DEBUG: Error creating announcement: {str(e)}")
            return Response({
                "status": "error",
                "message": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    @action(detail=False, methods=['DELETE'])
    def clear_announcements(self, request):
        try:
            with transaction.atomic():
                # Get all announcements by this professor
                announcements = ProfessorAnnouncement.objects.filter(professor=request.user)
                
                # Get all related notifications
                notifications = Notification.objects.filter(
                    sender=request.user,
                    notification_type='announcement'
                )
                
                # Delete both announcements and notifications
                announcements_count = announcements.count()
                announcements.delete()
                notifications.delete()

                return Response({
                    'status': 'success',
                    'message': f'Successfully cleared {announcements_count} announcements'
                })
                
        except Exception as e:
            return Response({
                'status': 'error',
                'message': f'Failed to clear announcements: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        

    @action(detail=False, methods=['GET'])
    def professor_announcements(self, request):
        """Get all announcements created by the professor"""
        try:
            if request.user.user_type != 'faculty':
                return Response({
                    "status": "error",
                    "message": "Only faculty can access this endpoint"
                }, status=status.HTTP_403_FORBIDDEN)

            announcements = ProfessorAnnouncement.objects.filter(
                professor=request.user
            ).select_related('section').order_by('-created_at')

            data = []
            for announcement in announcements:
                data.append({
                    'id': announcement.id,
                    'title': announcement.title,
                    'message': announcement.message,
                    'section': {
                        'id': announcement.section.id,
                        'course_code': announcement.section.course.code,
                        'section_number': announcement.section.section_number,
                    },
                    'created_at': announcement.created_at,
                })

            return Response({
                "status": "success",
                "announcements": data
            })

        except Exception as e:
            return Response({
                "status": "error",
                "message": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


    @action(detail=True, methods=['DELETE'])
    def delete_announcement(self, request, pk=None):
        try:
            # Get the announcement
            announcement = ProfessorAnnouncement.objects.get(
                id=pk,
                professor=request.user
            )
            
            with transaction.atomic():
                # Delete related notifications
                Notification.objects.filter(
                    announcement_id=announcement.id,
                    notification_type='announcement'
                ).delete()
                
                # Delete the announcement
                announcement.delete()
            
            return Response({
                'status': 'success',
                'message': 'Announcement deleted successfully'
            })
            
        except ProfessorAnnouncement.DoesNotExist:
            return Response({
                'status': 'error',
                'message': 'Announcement not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'status': 'error',
                'message': f'Failed to delete announcement: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @api_view(['GET'])
    def get_notifications(request):
        """Get all notifications for current user"""
        print(request.data)
        try:
            notifications = Notification.objects.filter(
                recipient=request.user
            ).order_by('-created_at')
            print("These are notifications", notifications)
            return Response({
                "status": "success",
                "notifications": NotificationSerializer(notifications, many=True).data
            })

        except Exception as e:
            return Response({
                "status": "error",
                "message": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        

    @action(detail=True, methods=['POST'])
    def mark_read(self, request, pk=None):
        notification = self.get_object()
        notification.is_read = True
        notification.save()
        return Response(NotificationSerializer(notification).data)

    @action(detail=False, methods=['POST'])
    def mark_all_read(self, request):
        self.get_queryset().update(is_read=True)
        return Response({'message': 'All notifications marked as read'})
    
class ProfileViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer
    parser_classes = (MultiPartParser, FormParser)

    
    def get_object(self):
        return self.request.user
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context
    
    @api_view(['GET', 'PATCH'])
    def profile_view(request):
        try:
            if request.method == 'GET':
                serializer = UserSerializer(request.user, context={'request': request})
                return Response({
                    "status": "success",
                    "user": serializer.data
                })
            
            elif request.method == 'PATCH':
                # Only allow updating specific fields
                allowed_fields = {'first_name', 'last_name', 'phone'}
                update_data = {
                    key: value for key, value in request.data.items() 
                    if key in allowed_fields
                }
                
                serializer = UserSerializer(
                    request.user, 
                    data=update_data, 
                    partial=True,
                    context={'request': request}
                )
                
                if serializer.is_valid():
                    serializer.save()
                    return Response({
                        "status": "success",
                        "message": "Profile updated successfully",
                        "user": serializer.data
                    })
                
                return Response({
                    "status": "error",
                    "message": "Invalid data",
                    "errors": serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            return Response({
                "status": "error",
                "message": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


    @action(detail=False, methods=['PATCH'])
    def update_profile(self, request, *args, **kwargs):
        try:
            user = request.user
            serializer = self.get_serializer(user, data=request.data, partial=True)
            
            print("This is data")
            print(serializer.data)
            if serializer.is_valid():
                serializer.save()
                return Response({
                    "status": "success",
                    "message": "Profile updated successfully",
                    "user": serializer.data
                })
            
            return Response({
                "status": "error",
                "message": serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                "status": "error",
                "message": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @method_decorator(csrf_exempt)
    @action(detail=False, methods=['POST'], parser_classes=[MultiPartParser])
    def upload_profile_image(self, request, *args, **kwargs):
        """Upload profile image"""
        if 'image' not in request.FILES:
            return Response({
                "status": "error",
                "message": "No image provided"
            }, status=status.HTTP_400_BAD_REQUEST)

        image = request.FILES['image']

        # Validate file extension instead of content type
        allowed_extensions = ['.jpg', '.jpeg', '.png']
        file_extension = os.path.splitext(image.name)[1].lower()

        if file_extension not in allowed_extensions:
            return Response({
                "status": "error",
                "message": "Invalid file type. Only JPG, JPEG, PNG allowed"
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = request.user
            # Delete old image if exists
            if user.profile_image:
                user.profile_image.delete()

            user.profile_image = image
            user.save()
            
            # Return the full URL
            image_url = request.build_absolute_uri(user.profile_image.url)
            
            serializer = self.get_serializer(user)
            return Response({
                "status": "success", 
                "message": "Profile image updated",
                "user": serializer.data,
                "image_url": image_url
            })

        except Exception as e:
            print(f"Error uploading image: {str(e)}")  # Debug print
            return Response({
                "status": "error",
                "message": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


    @action(detail=False, methods=['GET'])
    def schedule(self, request):
        """Get user's schedule"""
        user = request.user
        if user.user_type == 'student':
            sections = user.enrolled_sections.all().prefetch_related('schedules')
        else:
            sections = Section.objects.filter(professor=user).prefetch_related('schedules')
            
        schedule_data = {}
        days = ['sunday', 'monday', 'tuesday', 'wednesday', 'thursday']
        
        for section in sections:
            for schedule in section.schedules.all():
                day = schedule.day
                if day not in schedule_data:
                    schedule_data[day] = []
                    
                schedule_data[day].append({
                    'course_code': section.course.code,
                    'course_name': section.course.name,
                    'section_number': section.section_number,
                    'activity_type': section.activity_type,
                    'period': {
                        'number': schedule.period.number,
                        'start_time': schedule.period.start_time.strftime('%H:%M'),
                        'end_time': schedule.period.end_time.strftime('%H:%M'),
                        'is_online': schedule.period.number >= 9
                    }
                })
                
        return Response(schedule_data)
    



@api_view(['GET'])
def get_user_courses(request):
    try:
        user = request.user  # Gets the logged-in user
        
        if user.user_type == 'faculty':
            sections = Section.objects.filter(professor=user).select_related(
                'course'
            ).prefetch_related('schedules', 'schedules__period')
        else:
            sections = user.enrolled_sections.all().select_related(
                'course'
            ).prefetch_related('schedules', 'schedules__period')

        # Group by course and activity
        courses_data = {}
        for section in sections:
            course_id = section.course.id
            if course_id not in courses_data:
                courses_data[course_id] = {
                    'id': course_id,
                    'code': section.course.code,
                    'name': section.course.name,
                    'activities': {}
                }
            
            activity = section.activity_type
            print(section)
            if activity not in courses_data[course_id]['activities']:
                courses_data[course_id]['activities'][activity] = []
            
            courses_data[course_id]['activities'][activity].append({
                'id': section.id,
                'section_number': section.section_number,
                'course_id': course_id,
                'schedules': [
                    {
                        'id': schedule.id,
                        'day': schedule.day,
                        'period': {
                            'id':    schedule.period.number,
                            'period_number':    schedule.period.number,
                            'start_time': schedule.period.start_time.strftime('%H:%M'),
                            'end_time': schedule.period.end_time.strftime('%H:%M'),
                            'is_online': schedule.period.number >= 9
                        },
                        
                    }
                    for schedule in section.schedules.all()
                ]
            })

        return Response({
            "status": "success",
            "courses": list(courses_data.values())
        })

    except Exception as e:
        return Response({
            "status": "error",
            "message": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)