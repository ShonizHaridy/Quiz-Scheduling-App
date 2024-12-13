# quiz_scheduling_app/tasks.py

from django.utils import timezone
from django.db.models import Count
import random
from django.db import transaction  
from .models import Notification, Vote, VoteOption, Quiz


def complete_expired_votes():
    # Get all expired but still active votes
    expired_votes = Vote.objects.filter(
        is_active=True,
        ends_at__lte=timezone.now()
    )

    for vote in expired_votes:
        # Get vote options with their counts
        options_with_counts = VoteOption.objects.filter(
            vote=vote
        ).annotate(
            vote_count=Count('studentvote')
        ).order_by('-vote_count')

        if not options_with_counts:
            continue

        # Get maximum vote count
        max_votes = options_with_counts.first().vote_count

        # Get all options with maximum votes
        top_options = list(options_with_counts.filter(vote_count=max_votes))
        
        # Try each top option until we find one that works
        valid_option = None
        error_message = None
        
        for option in top_options:
            is_valid, message = vote.validate_quiz_time(option)
            if is_valid:
                valid_option = option
                break
            error_message = message
        
        if not valid_option:
            # If no valid option was found, mark vote as needing attention
            vote.is_active = False
            vote.needs_room = True
            vote.save()
            
            # Create notification for professor about the issue
            Notification.objects.create(
                recipient=vote.professor,
                sender=vote.professor,  # System notification
                notification_type='vote_error',
                title='Vote Completion Failed',
                message=f'Vote for {vote.section.course.code} could not be automatically completed: {error_message}',
                section=vote.section
            )
            continue

        try:
            with transaction.atomic():
                # Update vote with valid option
                vote.selected_option = valid_option
                vote.is_active = False
                vote.needs_room = True
                vote.save()

                # If the vote has a room already (like for online quizzes), create the quiz
                if vote.room:
                    Quiz.objects.create(
                        section=vote.section,
                        date=valid_option.date,
                        period=valid_option.period,
                        room=vote.room,
                        created_at=timezone.now()
                    )

                # Create a notification for professor to set room
                Notification.objects.create(
                    recipient=vote.professor,
                    sender=vote.professor,  # System notification
                    notification_type='room_needed',
                    title='Room Assignment Needed',
                    message=f'Please assign a room for the quiz in {vote.section.course.code}',
                    section=vote.section
                )
        except Exception as e:
            print(f"Error completing vote {vote.id}: {str(e)}")
            continue