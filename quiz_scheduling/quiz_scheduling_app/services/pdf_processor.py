# quiz_scheduling_app/services/pdf_processor.py

import tabula
import pandas as pd
from typing import Dict
import io
from ..models import Course, Section, Period, Schedule, User


day_mapping = {
    'Sun': 'Sunday',
    'Mon': 'Monday',
    'Tue': 'Tuesday',
    'Wed': 'Wednesday',
    'Thu': 'Thursday'
}

class PDFProcessor:
    @staticmethod
    def process_faculty_schedule(pdf_file, professor_id: str) -> Dict:
        try:
            file_bytes = io.BytesIO(pdf_file.read())
            tables = tabula.read_pdf(file_bytes, pages='all', multiple_tables=True, lattice=True)
            
            professor = User.objects.get(university_id=professor_id)
            processed_sections = []

            # Get the second table - exactly like reference
            course_table = tables[1]
            first_col = course_table.columns[0]

            for i in range(len(course_table)):
                row = course_table.iloc[i]

                # Skip rows - exactly like reference
                if pd.isna(row[first_col]) or not str(row[first_col]).startswith('CS'):
                    continue

                try:
                    # Extract data exactly like reference
                    course_code = str(row[first_col]).strip()
                    course_name = str(row['Unnamed: 0']).strip()
                    activity_type = str(row['Unnamed: 3']).strip()
                    section_number = str(row['Unnamed: 4']).strip()

                    # Create/update course
                    course, _ = Course.objects.get_or_create(
                        code=course_code,
                        defaults={'name': course_name}
                    )

                    # Create/update section
                    section, _ = Section.objects.update_or_create(
                        course=course,
                        section_number=section_number,
                        activity_type=activity_type,
                        defaults={'professor': professor}
                    )

                    # Process schedule exactly like reference
                    schedule = {}
                    days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday']
                    for idx, day in enumerate(days):
                        period = row[f'Unnamed: {idx+6}']
                        if not pd.isna(period):
                            period_numbers = str(period).strip().split(',')
                            schedule[day] = []
                            for period_num in period_numbers:
                                try:
                                    period_number = int(period_num.strip())
                                    # Get period by number field, not id
                                    period = Period.objects.filter(number=period_number).first()
                                    if period:
                                        Schedule.objects.get_or_create(
                                            section=section,
                                            day=day.lower(),
                                            period=period  # Use the period object
                                        )
                                        schedule[day].append(period_number)
                                    else:
                                        print(f"Period number {period_number} not found in database")
                                except ValueError:
                                    print(f"Invalid period number: {period_num}")
                                    continue

                    # Add section with schedule to processed sections
                    processed_sections.append({
                        'id': section.id,
                        'course_code': course_code,
                        'course_name': course_name,
                        'section_number': section_number,
                        'activity_type': activity_type,
                        'schedule': {day: ','.join(map(str, periods)) for day, periods in schedule.items() if periods}
                    })

                except Exception as e:
                    print(f"Error processing course {course_code if 'course_code' in locals() else 'unknown'}: {str(e)}")
                    continue

            return {
                "status": "success",
                "message": f"Processed {len(processed_sections)} sections",
                "sections": processed_sections
            }

        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }
    
    @staticmethod
    def process_student_schedule(pdf_file, student_id: str) -> Dict:
        try:
            file_bytes = io.BytesIO(pdf_file.read())
            tables = tabula.read_pdf(file_bytes, pages='all', multiple_tables=True, lattice=True)
            
            student = User.objects.get(university_id=student_id)
            processed_sections = []

            # Find the course table (exactly like reference script)
            course_table = None
            for table in tables:
                if 'Course Code' in table.columns:
                    course_table = table
                    break
            
            if course_table is None:
                raise Exception("Could not find course table in PDF")

            # Clear student's existing enrollments
            student.enrolled_sections.clear()

            # Process exactly like reference script
            days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu']
            
            for i in range(len(course_table)):
                row = course_table.iloc[i]
                
                # Skip header row and total row (exactly like reference)
                if pd.isna(row['Course Code']) or row['Course Code'] == 'Course Code' or row['Course Code'] == 'Total':
                    continue

                try:
                    course_code = str(row['Course Code']).strip()
                    course_name = str(row['Course Name']).strip()
                    activity_type = str(row['Unnamed: 1']).strip()
                    section_number = str(row['Details']).strip()
                    
                    # Create course and section
                    course, _ = Course.objects.get_or_create(
                        code=course_code,
                        defaults={'name': course_name}
                    )

                    section, _ = Section.objects.get_or_create(
                        course=course,
                        section_number=section_number,
                        activity_type=activity_type,
                        defaults={'professor': None}
                    )

                    # Add student to section
                    section.students.add(student)

                    # Process schedule exactly like reference script
                    schedule_data = {}
                    for day in days:
                        period = row[f'Unnamed: {days.index(day) + 2}']
                        if not pd.isna(period):
                            period_numbers = str(period).strip().split(',')
                            for period_num in period_numbers:
                                if period_num.strip().isdigit():
                                    Schedule.objects.get_or_create(
                                        section=section,
                                        day=day_mapping[day].lower(),  # Convert short day to long day
                                        period_id=int(period_num.strip())
                                    )

                    processed_sections.append({
                        'id': section.id,
                        'course_code': course_code,
                        'course_name': course_name,
                        'section_number': section_number,
                        'activity_type': activity_type,
                        'professor': 'Not assigned'  # Since this is student schedule
                    })

                except Exception as e:
                    print(f"Error processing course {course_code if 'course_code' in locals() else 'unknown'}: {str(e)}")
                    continue

            return {
                "status": "success",
                "message": f"Enrolled in {len(processed_sections)} sections",
                "sections": processed_sections
            }

        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }