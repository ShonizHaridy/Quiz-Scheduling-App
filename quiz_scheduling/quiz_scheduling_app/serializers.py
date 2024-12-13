from django.shortcuts import get_object_or_404
from rest_framework import serializers

from .models import (
    User, Course, Section, Period, Schedule, Vote, 
    VoteOption, StudentVote, Notification
)

class UserRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = (
            'university_id', 'email', 'password', 'confirm_password',
            'first_name', 'last_name', 'user_type', 'phone'
        )

    def validate(self, data):
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError("Passwords don't match")
        return data

    def create(self, validated_data):
        validated_data.pop('confirm_password')
        password = validated_data.pop('password')
        
        # Set username equal to university_id
        validated_data['username'] = validated_data['university_id']
        
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user

# class UserProfileSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = User
#         fields = ('id', 'university_id', 'email', 'first_name', 'last_name', 
#                  'user_type', 'phone', 'profile_image')
#         read_only_fields = ('university_id', 'user_type')

class UserSerializer(serializers.ModelSerializer):
    profile_image_url = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ('id', 'university_id', 'email', 'first_name', 
                 'last_name', 'user_type', 'phone', 'profile_image_url')
        read_only_fields = ('university_id', 'user_type')

    def get_profile_image_url(self, obj):
        if obj.profile_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.profile_image.url)
        return None

class PasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=6)
    new_password = serializers.CharField(min_length=8, write_only=True)
    confirm_password = serializers.CharField(min_length=8, write_only=True)

    def validate(self, data):
        # Check if passwords match
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError({
                "password": "Passwords don't match"
            })
        return data

    def validate_otp(self, value):
        # Ensure OTP is numeric and 6 digits
        if not value.isdigit() or len(value) != 6:
            raise serializers.ValidationError(
                "OTP must be 6 digits"
            )
        return value

    def validate_new_password(self, value):
        # Add any password validation rules here
        if len(value) < 8:
            raise serializers.ValidationError(
                "Password must be at least 8 characters long"
            )
        return value


class PeriodSerializer(serializers.ModelSerializer):
    class Meta:
        model = Period
        fields = ['id', 'number', 'start_time', 'end_time', 'is_online']

class CourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = ['id', 'code', 'name']

class SectionSerializer(serializers.ModelSerializer):
    course_details = CourseSerializer(source='course', read_only=True)
    professor_name = serializers.SerializerMethodField()

    class Meta:
        model = Section
        fields = ['id', 'course', 'course_details', 'section_number', 
                 'activity_type', 'professor', 'professor_name']
        read_only_fields = ['professor']

    def get_professor_name(self, obj):
        return f"{obj.professor.first_name} {obj.professor.last_name}"

class ScheduleSerializer(serializers.ModelSerializer):
    period_details = PeriodSerializer(source='period', read_only=True)

    class Meta:
        model = Schedule
        fields = ['id', 'section', 'day', 'period', 'period_details']

class VoteOptionSerializer(serializers.ModelSerializer):
    period_details = PeriodSerializer(source='period', read_only=True)
    voters = serializers.SerializerMethodField()
    vote_count = serializers.SerializerMethodField()
    has_voted = serializers.SerializerMethodField()

    class Meta:
        model = VoteOption
        fields = ['id', 'date', 'period', 'period_details', 'vote_count', 'voters', 'has_voted']

    def get_voters(self, obj):
        request = self.context.get('request')
        if not request or request.user.user_type != 'faculty':
            return None

        return [{
            'id': vote.student.id,
            'name': f"{vote.student.first_name} {vote.student.last_name}",
            'university_id': vote.student.university_id
        } for vote in obj.studentvote_set.all()]

    def get_has_voted(self, obj):
        request = self.context.get('request')
        if not request or request.user.is_anonymous:
            return False
        
        return obj.studentvote_set.filter(student=request.user).exists()

    def get_vote_count(self, obj):
        return obj.studentvote_set.count()

class VoteSerializer(serializers.ModelSerializer):
    section = SectionSerializer()
    options = VoteOptionSerializer(many=True, read_only=True)
    selected_option = VoteOptionSerializer(read_only=True)
    student_vote = serializers.SerializerMethodField()  # Add this

    class Meta:
        model = Vote
        fields = [
            'id', 'section', 'professor', 'created_at', 'is_active',
            'selected_option', 'room', 'options', 'student_vote'
        ]

    def get_student_vote(self, obj):
        request = self.context.get('request')
        if not request or request.user.is_anonymous or request.user.user_type != 'student':
            return None
        
        student_vote = StudentVote.objects.filter(
            vote=obj,
            student=request.user
        ).first()
        
        if student_vote:
            return {
                'option_id': student_vote.option.id,
                'voted_at': student_vote.created_at
            }
        return None


    # class Meta:
    #     model = Vote
    #     # fields = ['id', 'section', 'professor', 'created_at', 'is_active',
    #     #          'selected_period', 'selected_date', 'room', 'options']
    #     fields = ['id', 'section', 'professor', 'created_at', 'is_active',
    #         'selected_option', 'room', 'options']

class CreateVoteSerializer(serializers.ModelSerializer):
    options = serializers.ListField(
        child=serializers.DictField()
    )

    class Meta:
        model = Vote
        fields = ['section', 'options']

    def create(self, validated_data):
        options_data = validated_data.pop('options')
        vote = Vote.objects.create(**validated_data)

        for option_data in options_data:
            VoteOption.objects.create(
                vote=vote,
                date=option_data['date'],
                period_id=option_data['period_id']
            )

        return vote

class StudentVoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentVote
        fields = ['vote', 'option']

    def validate(self, data):
        if data['option'].vote != data['vote']:
            raise serializers.ValidationError(
                "Vote option doesn't belong to this vote"
            )
        return data

class NotificationSerializer(serializers.ModelSerializer):
    sender_name = serializers.SerializerMethodField()
    section_details = SectionSerializer(source='section', read_only=True)
    recipient_count = serializers.SerializerMethodField()
    vote_details = VoteSerializer(source='vote', read_only=True)  # Direct reference to the vote

    class Meta:
        model = Notification
        fields = [
            'id', 
            'notification_type', 
            'title', 
            'message',
            'sender_name', 
            'section_details', 
            'vote_details',
            'created_at', 
            'is_read',
            'recipient_count'
        ]

    def get_sender_name(self, obj):
        return f"{obj.sender.first_name} {obj.sender.last_name}"

    def get_recipient_count(self, obj):
        if self.context['request'].user.user_type == 'faculty':
            return Notification.objects.filter(
                sender=obj.sender,
                title=obj.title,
                message=obj.message,
                created_at=obj.created_at
            ).count()
        return None

class CreateAnnouncementSerializer(serializers.Serializer):
    section_id = serializers.IntegerField()
    title = serializers.CharField(max_length=200)
    message = serializers.CharField()

class UserRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ('university_id', 'email', 'password', 'confirm_password', 
                 'first_name', 'last_name', 'user_type', 'phone')

    def validate(self, data):
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError("Passwords don't match")
        return data

    def create(self, validated_data):
        validated_data.pop('confirm_password')
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user

class LoginSerializer(serializers.Serializer):
    university_id = serializers.CharField()
    password = serializers.CharField()

class OTPVerificationSerializer(serializers.Serializer):
    university_id = serializers.CharField()
    otp_code = serializers.CharField()