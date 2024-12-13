# quiz_scheduling_app/services/notification_service.py

from django.db.models import Q
from ..models import Notification, ProfessorAnnouncement, User, Section, Vote
from django.utils import timezone

class NotificationService:
    @staticmethod
    def send_vote_created_notification(vote: Vote):
        """Send notifications to students when a new vote is created"""
        students = vote.section.students.all()
        notifications = []

        for student in students:
            notifications.append(
                Notification(
                    recipient=student,
                    sender=vote.professor,
                    notification_type='vote_created',
                    title='New Quiz Vote Available',
                    message=f'A new vote has been created for {vote.section.course.code} - Section {vote.section.section_number}',
                    section=vote.section,
                    vote=vote  # All notifications reference the same vote
                )
            )

        if notifications:
            Notification.objects.bulk_create(notifications)

    @staticmethod
    def send_vote_completed_notification(vote: Vote):
        """Send notifications when a vote is completed"""
        if not vote.selected_option:
            return
            
        students = vote.section.students.all()
        notifications = []

        selected_option = vote.selected_option
        period_time = f"{selected_option.period.start_time.strftime('%H:%M')} - {selected_option.period.end_time.strftime('%H:%M')}"
        online_text = " (Online)" if selected_option.period.number >= 9 else ""

        for student in students:
            notifications.append(
                Notification(
                    recipient=student,
                    sender=vote.professor,
                    notification_type='vote_completed',
                    title='Quiz Time Confirmed',
                    message=(
                        f'Quiz for {vote.section.course.code} has been scheduled:\n'
                        f'Date: {selected_option.date.strftime("%A, %B %d")}\n'
                        f'Time: {period_time}\n'
                        f'Room: {vote.room}{online_text}'
                    ),
                    section=vote.section,
                    vote=vote  # Add this reference
                )
            )

        if notifications:
            Notification.objects.bulk_create(notifications)

    @staticmethod
    def send_announcement(section_id: int, professor_id: int, title: str, message: str):
        """Send custom announcement to students in a section"""
        try:
            section = Section.objects.get(id=section_id)
            professor = User.objects.get(id=professor_id)

            if section.professor != professor:
                return {
                    "status": "error",
                    "message": "Not authorized to send announcements for this section"
                }

            # Create single professor announcement
            announcement = ProfessorAnnouncement.objects.create(
                professor=professor,
                section=section,
                title=title,
                message=message
            )

            # Create student notifications in bulk
            notifications = [
                Notification(
                    recipient=student,
                    sender=professor,
                    notification_type='announcement',
                    title=title,
                    message=message,
                    section=section,
                    announcement_id=announcement.id  
                ) for student in section.students.all()
            ]

            if notifications:
                Notification.objects.bulk_create(notifications)

            return {
                "status": "success",
                "message": f"Announcement sent to {len(notifications)} students"
            }

        except (Section.DoesNotExist, User.DoesNotExist) as e:
            return {
                "status": "error",
                "message": str(e)
            }

    @staticmethod
    def clear_professor_announcements(professor_id: int):
        """Clear all announcements for a professor"""
        try:
            # Get all professor announcements
            announcements = ProfessorAnnouncement.objects.filter(professor_id=professor_id)
            
            # Delete related student notifications
            Notification.objects.filter(
                sender_id=professor_id,
                notification_type='announcement'
            ).delete()
            
            # Delete professor announcements
            announcements.delete()
            
            return {
                "status": "success",
                "message": "All announcements cleared"
            }
        except Exception as e:
            return {
                "status": "error", 
                "message": str(e)
            }

    @staticmethod
    def delete_vote_notifications(vote_id: int):
        """Delete all notifications related to a vote"""
        Notification.objects.filter(
            vote_id=vote_id
        ).delete()

    @staticmethod
    def mark_as_read(notification_id: int, user_id: int):
        """Mark a notification as read"""
        try:
            notification = Notification.objects.get(
                id=notification_id,
                recipient_id=user_id
            )
            notification.is_read = True
            notification.save()
            return True
        except Notification.DoesNotExist:
            return False

    @staticmethod
    def mark_all_as_read(user_id: int):
        """Mark all notifications as read for a user"""
        Notification.objects.filter(
            recipient_id=user_id,
            is_read=False
        ).update(is_read=True)

    @staticmethod
    def get_unread_count(user_id: int) -> int:
        """Get count of unread notifications for a user"""
        return Notification.objects.filter(
            recipient_id=user_id,
            is_read=False
        ).count()