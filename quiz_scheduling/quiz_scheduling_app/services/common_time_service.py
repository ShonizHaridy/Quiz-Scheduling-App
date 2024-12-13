# quiz_scheduling_app/services/common_time_service.py

from typing import List, Dict
from django.db.models import Q, Count
from ..models import Quiz, Section, Period, Schedule
from datetime import datetime

# class CommonTimeService:
#     @staticmethod
#     def get_available_periods(section_id: int, date: datetime.date) -> Dict:
#         try:
#             section = Section.objects.get(id=section_id)
#             students = section.students.all()
            
#             if not students:
#                 return {
#                     "status": "error",
#                     "message": "No students enrolled in this section"
#                 }

#             # Get the day of week from the date
#             day_of_week = date.strftime('%A').lower()
            
#             # Get periods 1-15
#             periods = Period.objects.filter(number__lte=15).order_by('number')
            
#             # Check how many quizzes each student has on this date
#             student_quiz_counts = {}
#             for student in students:
#                 quiz_count = Quiz.objects.filter(
#                     section__students=student,
#                     date=date
#                 ).count()
#                 student_quiz_counts[student.id] = quiz_count

#             # If any student already has 2 quizzes on this date, return empty
#             if any(count >= 2 for count in student_quiz_counts.values()):
#                 return {
#                     "status": "success",
#                     "data": []
#                 }

#             available_periods = []
#             for period in periods:
#                 # Check if this period is free for ALL students
#                 is_available = True
#                 for student in students:
#                     # Check regular schedule for this day of week
#                     has_class = Schedule.objects.filter(
#                         section__in=student.enrolled_sections.all(),
#                         day=day_of_week,
#                         period=period
#                     ).exists()
                    
#                     # Check if student has a quiz on this specific date and period
#                     has_quiz = Quiz.objects.filter(
#                         section__students=student,
#                         date=date,
#                         period=period
#                     ).exists()
                    
#                     if has_class or has_quiz:
#                         is_available = False
#                         break
                
#                 if is_available:
#                     available_periods.append({
#                         'period_number': period.number,
#                         'start_time': period.start_time.strftime('%H:%M'),
#                         'end_time': period.end_time.strftime('%H:%M'),
#                         'is_online': period.number >= 9,
#                     })
            
#             return {
#                 "status": "success",
#                 "data": available_periods
#             }
            
#         except Section.DoesNotExist:
#             return {
#                 "status": "error",
#                 "message": "Section not found"
#             }
#         except Exception as e:
#             return {
#                 "status": "error",
#                 "message": str(e)
#             }

class CommonTimeService:
    @staticmethod
    def get_available_periods(section_id: int, date: datetime.date) -> Dict:
        """
        Get common free periods for all students in a section for a specific date.
        Takes into account:
        - Regular schedules
        - Existing quizzes
        - Maximum 2 quizzes per day rule
        - Only periods 1-15 are considered
        """
        try:
            section = Section.objects.get(id=section_id)
            students = section.students.all()

            if not students:
                return {
                    "status": "error",
                    "message": "No students enrolled in this section"
                }

            # Get day of week from the date
            day_of_week = date.strftime('%A').lower()

            # Get periods 1-15 only
            periods = Period.objects.filter(number__lte=15).order_by('number')

            # Check students' quiz count for the given date
            students_with_two_quizzes = Quiz.objects.filter(
                date=date,
                section__students__in=students
            ).values('section__students').annotate(
                quiz_count=Count('id')
            ).filter(quiz_count__gte=2)

            # If any student has 2 quizzes, no periods are available
            if students_with_two_quizzes.exists():
                return {
                    "status": "success",
                    "data": []
                }

            available_periods = []
            for period in periods:
                is_available = True
                
                for student in students:
                    # Check regular schedule for this day
                    has_class = Schedule.objects.filter(
                        section__students=student,
                        day=day_of_week,
                        period=period
                    ).exists()

                    # Check if student has a quiz at this period
                    has_quiz = Quiz.objects.filter(
                        section__students=student,
                        date=date,
                        period=period
                    ).exists()

                    if has_class or has_quiz:
                        is_available = False
                        break

                if is_available:
                    available_periods.append({
                        'period_number': period.number,
                        'start_time': period.start_time.strftime('%H:%M'),
                        'end_time': period.end_time.strftime('%H:%M'),
                        'is_online': period.number >= 9,
                    })

            return {
                "status": "success",
                "data": available_periods
            }

        except Section.DoesNotExist:
            return {
                "status": "error", 
                "message": "Section not found"
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }

    # Modify in services/common_time_service.py
    # quiz_scheduling_app/services/common_time_service.py

# In quiz_scheduling_app/services/common_time_service.py

    # @staticmethod
    # def get_available_periods(section_id: int, day: str) -> Dict:
    #     """
    #     Get common free periods for all students in a section.
    #     Takes day as a string (e.g., 'sunday', 'monday', etc.)
    #     """
    #     try:
    #         if day not in ['sunday', 'monday', 'tuesday', 'wednesday', 'thursday']:
    #             return {
    #                 "status": "error",
    #                 "message": "Invalid day. Must be Sunday through Thursday"
    #             }

    #         section = Section.objects.get(id=section_id)
    #         students = section.students.all()

    #         if not students:
    #             return {
    #                 "status": "error",
    #                 "message": "No students enrolled in this section"
    #             }

    #         # Get periods 1-15 only - explicitly exclude period 16
    #         periods = Period.objects.filter(
    #             number__lte=15,  # Keep this
    #             number__ne=16    # Add this exclusion
    #         ).order_by('number')
    #         print("Periods are ")
    #         print(periods)
            
    #         available_periods = []
            
    #         for period in periods:
    #             # Check if this period is free for ALL students
    #             is_common = True
    #             for student in students:
    #                 # Check if student has any class in this period
    #                 has_class = Schedule.objects.filter(
    #                     section__in=student.enrolled_sections.all(),
    #                     day=day,
    #                     period=period
    #                 ).exists()

    #                 if has_class:
    #                     is_common = False
    #                     break

    #             if is_common:
    #                 available_periods.append({
    #                     'period_number': period.number,
    #                     'start_time': period.start_time.strftime('%H:%M'),
    #                     'end_time': period.end_time.strftime('%H:%M'),
    #                     'is_online': period.number >= 9
    #                 })

    #         return {
    #             "status": "success",
    #             "data": available_periods
    #         }

    #     except Section.DoesNotExist:
    #         return {
    #             "status": "error",
    #             "message": "Section not found"
    #         }
    #     except Exception as e:
    #         return {
    #             "status": "error",
    #             "message": str(e)
    #         }

























    # @staticmethod
    # def get_available_periods(section_id: int, day: str) -> Dict:
    #     """
    #     Get common free periods for all students in a section.
    #     Takes day as a string (e.g., 'sunday', 'monday', etc.)
    #     """
    #     try:
    #         if day not in ['sunday', 'monday', 'tuesday', 'wednesday', 'thursday']:
    #             return {
    #                 "status": "error",
    #                 "message": "Invalid day. Must be Sunday through Thursday"
    #             }

    #         section = Section.objects.get(id=section_id)
    #         students = section.students.all()

    #         if not students:
    #             return {
    #                 "status": "error",
    #                 "message": "No students enrolled in this section"
    #             }

    #         # Get periods 1-15 only
    #         periods = Period.objects.filter(number__lte=15).order_by('number')
            
    #         available_periods = []
            
    #         for period in periods:
    #             # Check if this period is free for ALL students
    #             is_common = True
    #             for student in students:
    #                 # Check if student has any class in this period
    #                 has_class = Schedule.objects.filter(
    #                     section__in=student.enrolled_sections.all(),
    #                     day=day,
    #                     period=period
    #                 ).exists()

    #                 # Check if student has a quiz at this period
    #                 has_quiz = Quiz.objects.filter(
    #                     section__students=student,
    #                     date=date,
    #                     period=period
    #                 ).exists()

    #                 if has_class or has_quiz:

    #                     is_common = False
    #                     break

    #             if is_common:
    #                 available_periods.append({
    #                     'period_number': period.number,
    #                     'start_time': period.start_time.strftime('%H:%M'),
    #                     'end_time': period.end_time.strftime('%H:%M'),
    #                     'is_online': period.number >= 9
    #                 })

    #         return {
    #             "status": "success",
    #             "data": available_periods
    #         }

    #     except Section.DoesNotExist:
    #         return {
    #             "status": "error",
    #             "message": "Section not found"
    #         }
    #     except Exception as e:
    #         print(f"Error in get_available_periods: {str(e)}")  # For debugging
    #         return {
    #             "status": "error",
    #             "message": str(e)
    #         }