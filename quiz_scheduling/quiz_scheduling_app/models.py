from django.utils import timezone
from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    USER_TYPES = (
        ('faculty', 'Faculty'),
        ('student', 'Student')
    )
    
    university_id = models.CharField(max_length=20, unique=True)
    user_type = models.CharField(max_length=10, choices=USER_TYPES)
    profile_image = models.ImageField(upload_to='profiles/', null=True, blank=True)
    phone = models.CharField(max_length=15)

    USERNAME_FIELD = 'university_id'
    REQUIRED_FIELDS = ['email', 'first_name', 'last_name', 'user_type', 'phone']

    def save(self, *args, **kwargs):
        if not self.username:
            self.username = self.university_id  # Automatically set username to university_id
        super().save(*args, **kwargs)

class Course(models.Model):
    code = models.CharField(max_length=10)
    name = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.code} - {self.name}"

class Period(models.Model):
    number = models.IntegerField(unique=True)
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_online = models.BooleanField(default=False)

    class Meta:
        ordering = ['number']

    def __str__(self):
        return f"Period {self.number} ({self.start_time}-{self.end_time})"
    
class Section(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    section_number = models.CharField(max_length=10)
    # activity_type = models.CharField(max_length=20, choices=ACTIVITY_TYPES)
    activity_type = models.CharField(max_length=50)  # Free text field without choices

    professor = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)  # Changed this line
    students = models.ManyToManyField(User, related_name='enrolled_sections', blank=True)

    class Meta:
        unique_together = ['course', 'section_number', 'activity_type']

    def __str__(self):
        return f"{self.id} - {self.course.code} - {self.activity_type} - Section {self.section_number}"

class Schedule(models.Model):
    DAYS_OF_WEEK = (
        ('sunday', 'Sunday'),
        ('monday', 'Monday'),
        ('tuesday', 'Tuesday'),
        ('wednesday', 'Wednesday'),
        ('thursday', 'Thursday')
    )
    section = models.ForeignKey(Section, on_delete=models.CASCADE, related_name='schedules')
    day = models.CharField(max_length=15, choices=DAYS_OF_WEEK)
    period = models.ForeignKey(Period, on_delete=models.CASCADE)

    class Meta:
        unique_together = ['section', 'day', 'period']


class Quiz(models.Model):
    section = models.ForeignKey(Section, on_delete=models.CASCADE)
    date = models.DateField()
    period = models.ForeignKey(Period, on_delete=models.CASCADE)
    room = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['section', 'date', 'period']


# class Vote(models.Model):
#     section = models.ForeignKey(Section, on_delete=models.CASCADE)
#     professor = models.ForeignKey(User, on_delete=models.CASCADE)
#     created_at = models.DateTimeField(auto_now_add=True)
#     is_active = models.BooleanField(default=True)
#     # selected_period = models.ForeignKey(Period, null=True, blank=True, on_delete=models.SET_NULL)
#     # selected_day = models.CharField(max_length=15, null=True, blank=True)
#     selected_option = models.ForeignKey('VoteOption', null=True, blank=True, on_delete=models.SET_NULL, related_name='selected_for_votes')
#     room = models.CharField(max_length=20, null=True, blank=True)

class Vote(models.Model):
    section = models.ForeignKey(Section, on_delete=models.CASCADE)
    professor = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    selected_option = models.ForeignKey('VoteOption', null=True, blank=True, 
                                      on_delete=models.SET_NULL, 
                                      related_name='selected_for_votes')
    room = models.CharField(max_length=20, null=True, blank=True)
    duration = models.IntegerField(default=1)  # Duration in days
    ends_at = models.DateTimeField(null=True, blank=True)
    needs_room = models.BooleanField(default=False)  # Flag for automatic completion

    def save(self, *args, **kwargs):
        if not self.ends_at and self.duration:
            self.ends_at = timezone.now() + timezone.timedelta(days=self.duration)
        super().save(*args, **kwargs)

    @property
    def is_expired(self):
        return self.ends_at and timezone.now() >= self.ends_at
    
    def validate_quiz_time(self, option):
        """
        Validates if the selected option time is available for all students.
        Returns (bool, str) tuple: (is_valid, error_message)
        """
        students = self.section.students.all()
        
        for student in students:
            # Check for existing quiz at the same time
            existing_quiz = Quiz.objects.filter(
                section__students=student,
                date=option.date,
                period=option.period
            ).exists()
            
            if existing_quiz:
                return False, f"Student {student.university_id} already has a quiz scheduled at this time"
            
            # Check for two quizzes on the same day
            quizzes_on_day = Quiz.objects.filter(
                section__students=student,
                date=option.date
            ).count()
            
            if quizzes_on_day >= 2:
                return False, f"Student {student.university_id} already has two quizzes on this date"
        
        return True, ""

class VoteOption(models.Model):
    vote = models.ForeignKey(Vote, related_name='options', on_delete=models.CASCADE)
    date = models.DateField()  # Changed from day to full date
    period = models.ForeignKey(Period, on_delete=models.CASCADE)

    class Meta:
        unique_together = ['vote', 'date', 'period']

class ProfessorAnnouncement(models.Model):
    professor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_announcements')
    section = models.ForeignKey(Section, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

class StudentVote(models.Model):
    vote = models.ForeignKey(Vote, on_delete=models.CASCADE)
    student = models.ForeignKey(User, on_delete=models.CASCADE)
    option = models.ForeignKey(VoteOption, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['vote', 'student']

class OTPCode(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    def is_valid(self):
        from django.utils import timezone
        return not self.is_used and self.expires_at > timezone.now()

class Notification(models.Model):
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_notifications')
    notification_type = models.CharField(max_length=20)
    title = models.CharField(max_length=200)
    message = models.TextField()
    section = models.ForeignKey(Section, on_delete=models.CASCADE, null=True, blank=True)
    vote = models.ForeignKey(Vote, on_delete=models.CASCADE, null=True, blank=True)  # Add this field
    announcement_id = models.IntegerField(null=True, blank=True) 
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.notification_type} - {self.title} - To: {self.recipient.university_id}"

    class Meta:
        ordering = ['-created_at']
