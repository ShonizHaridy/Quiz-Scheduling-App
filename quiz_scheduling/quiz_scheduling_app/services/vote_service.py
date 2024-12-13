# quiz_scheduling_app/services/vote_service.py

from typing import List, Dict
from django.db.models import Q
from ..models import Schedule, Section, Period, User, Vote, VoteOption, StudentVote

class VoteService:
    @staticmethod
    def get_common_periods(section_id: int) -> List[Dict]:
        """Get common free periods for all students in a section"""
        section = Section.objects.get(id=section_id)
        students = section.students.all()
        
        # Get all periods 1-12 
        available_periods = Period.objects.filter(number__lte=12).order_by('number')
        
        common_periods = []
        days = ['sunday', 'monday', 'tuesday', 'wednesday', 'thursday']
        
        for day in days:
            for period in available_periods:
                # Check if period is free for all students
                is_common = True
                for student in students:
                    # Get all sections student is enrolled in
                    student_sections = student.enrolled_sections.all()
                    
                    # Check if student has any class in this period
                    has_class = Schedule.objects.filter(
                        section__in=student_sections,
                        day=day,
                        period=period
                    ).exists()
                    
                    if has_class:
                        is_common = False
                        break
                
                if is_common:
                    common_periods.append({
                        'day': day,
                        'period': period.number,
                        'start_time': period.start_time.strftime('%H:%M'),
                        'end_time': period.end_time.strftime('%H:%M'),
                        'is_online': period.is_online
                    })
        
        return common_periods

    @staticmethod
    def create_vote(section_id: int, professor_id: int, options: List[Dict]) -> Vote:
        """Create a new vote with options"""
        section = Section.objects.get(id=section_id)
        professor = User.objects.get(id=professor_id)
        
        vote = Vote.objects.create(
            section=section,
            professor=professor
        )
        
        for option in options:
            period = Period.objects.get(number=option['period'])
            VoteOption.objects.create(
                vote=vote,
                day=option['day'],
                period=period
            )
            
        return vote

    @staticmethod
    def submit_student_vote(vote_id: int, student_id: int, option_id: int) -> StudentVote:
        """Submit a student's vote"""
        vote = Vote.objects.get(id=vote_id)
        student = User.objects.get(id=student_id)
        option = VoteOption.objects.get(id=option_id)
        
        student_vote = StudentVote.objects.create(
            vote=vote,
            student=student,
            option=option
        )
        
        return student_vote

    @staticmethod
    def confirm_vote(vote_id: int, option_id: int, room: str) -> Vote:
        """Confirm a vote and set the selected option"""
        vote = Vote.objects.get(id=vote_id)
        option = VoteOption.objects.get(id=option_id)
        
        vote.selected_period = option.period
        vote.selected_day = option.day
        vote.room = room
        vote.is_active = False
        vote.save()
        
        return vote