from django.shortcuts import render, redirect, get_object_or_404
from .models import Announcement ,QuizShow, LiveEvent
from .models import StudentAnswerRecord
from django.conf import settings
import google.generativeai as genai

genai.configure(api_key=settings.GEMINI_API_KEY)

from django.shortcuts import render
from django.http import HttpResponse
from django.template.loader import get_template
from django.contrib.auth.decorators import user_passes_test
from .models import StudentProfile
import openpyxl # Ensure you have installed openpyxl
from xhtml2pdf import pisa # Ensure you have installed xhtml2pdf
from io import BytesIO

from django.http import HttpResponse
from .models import StudentAnswerRecord

import google.generativeai as genai
import re
import openpyxl
import os
from io import BytesIO
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import user_passes_test
from django.contrib import messages
from django.http import HttpResponse
from django.template.loader import get_template
from xhtml2pdf import pisa

from .models import AppSection, StudentProfile, SlideQuestion, QuestionSlide, MCQQuestion

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from .models import AppSection, MCQQuestion

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import user_passes_test
from .models import QuizShow








# --- Access Control ---
def is_admin(user):
    """Checks if the user is both logged in and a staff member."""
    return user.is_authenticated and user.is_staff


# --- Authentication & Public Views ---
def admin_login_view(request):
    if request.method == "POST":
        u, p = request.POST.get('username'), request.POST.get('password')
        user = authenticate(request, username=u, password=p)
        if user and user.is_staff:
            login(request, user)
            return redirect('dashboard')
        messages.error(request, "Invalid Admin Credentials")
    return render(request, 'admin-login.html')


def admin_logout_view(request):
    logout(request)
    return redirect('admin_login')


def index_view(request):
    return render(request, 'index.html')


# --- Dashboard ---
@user_passes_test(is_admin, login_url='admin_login')
def dashboard_view(request):
    # 1. Total Students: Live count from Firebase
    firebase_users = get_firebase_users()
    total_students_count = len(firebase_users)
    
    # 2. Active Quiz: Specifically count modules in Quiz Club (QC)
    active_qc_count = SlideQuestion.objects.filter(section__section_type='QC').count()
    
    # 3. Articles: Total sum of ThinkBell (TB) modules + NewsBytes (NB) MCQs
    tb_modules_count = SlideQuestion.objects.filter(section__section_type='TB').count()
    nb_mcqs_count = MCQQuestion.objects.filter(section__section_type='NB').count()
    total_articles = tb_modules_count + nb_mcqs_count
    
    # 4. Recent Activity: Exactly 4 most recent users from Firebase
    recent_students = firebase_users[:4]

    context = {
        'total_students': total_students_count,
        'active_quiz_count': active_qc_count,
        'articles_count': total_articles,
        'students': recent_students,
    }
    return render(request, 'dashboard.html', context)

# =========================================================
#                 THINKBELL MANAGEMENT
# =========================================================
@user_passes_test(is_admin, login_url='admin_login')
def thinkbell_view(request):
    sections = AppSection.objects.filter(section_type='TB')
    return render(request, 'thinkbell.html', {'sections': sections})


@user_passes_test(is_admin, login_url='admin_login')
def add_thinkbell_section(request):
    if request.method == "POST":
        name = request.POST.get('name')
        is_premium = request.POST.get('is_premium') == 'on'
        if name:
            AppSection.objects.create(name=name, section_type='TB', is_premium=is_premium)
    return redirect('thinkbell')


@user_passes_test(is_admin, login_url='admin_login')
def manage_thinkbell_questions(request, section_id):
    section = get_object_or_404(AppSection, id=section_id)
    questions = SlideQuestion.objects.filter(section=section).prefetch_related('slides')
    return render(request, 'thinkbell_questions.html', {'section': section, 'questions': questions})


@user_passes_test(is_admin, login_url='admin_login')
def add_thinkbell_question(request, section_id):
    section = get_object_or_404(AppSection, id=section_id)
    if request.method == "POST":
        title = request.POST.get('title')
        if not title:
            messages.error(request, "Module Title is required.")
            return redirect(request.path)
        q = SlideQuestion.objects.create(
            section=section,
            title=title,
            expected_answer_keywords=request.POST.get('keywords'),
            option_a=request.POST.get('opt_a'),
            option_b=request.POST.get('opt_b'),
            option_c=request.POST.get('opt_c'),
            option_d=request.POST.get('opt_d'),
            correct_option=request.POST.get('correct_option')
        )
        texts = request.POST.getlist('slide_text[]')
        images = request.FILES.getlist('slide_image[]')
        for i in range(len(texts)):
            QuestionSlide.objects.create(
                question=q,
                text_content=texts[i],
                image=images[i] if i < len(images) else None,
                order=i + 1
            )
        messages.success(request, "ThinkBell module published!")
        return redirect('manage_thinkbell_questions', section_id=section.id)
    return render(request, 'thinkbell_form.html', {'section': section})


def edit_thinkbell_question(request, pk):
    # 1. Fetch the existing module and its slides
    question = get_object_or_404(SlideQuestion, pk=pk)
    section = question.section
    slides = question.slides.all().order_by('order')

    if request.method == "POST":
        # 2. Update the main module data
        question.title = request.POST.get('title')
        question.expected_answer_keywords = request.POST.get('keywords')

        # Update MCQ Assessment fields
        question.option_a = request.POST.get('opt_a')
        question.option_b = request.POST.get('opt_b')
        question.option_c = request.POST.get('opt_c')
        question.option_d = request.POST.get('opt_d')
        question.correct_option = request.POST.get('correct_option')
        question.save()

        # 3. Update Learning Slides logic
        # For a clean update, we handle the slide IDs provided in the form
        texts = request.POST.getlist('slide_text[]')
        images = request.FILES.getlist('slide_image[]')

        # Clear existing slides to replace them with the new sequence from the form
        question.slides.all().delete()

        for i in range(len(texts)):
            new_slide = QuestionSlide(
                question=question,
                text_content=texts[i],
                order=i + 1
            )
            # Check if an image was uploaded for this specific index
            if i < len(images):
                new_slide.image = images[i]
            new_slide.save()

        messages.success(request, "ThinkBell module updated successfully!")
        return redirect('manage_thinkbell_questions', section_id=section.id)

    # 4. Pass 'is_edit' and existing data to the template
    return render(request, 'thinkbell_form.html', {
        'question': question,
        'slides': slides,
        'section': section,
        'is_edit': True
    })
@user_passes_test(is_admin, login_url='admin_login')
def delete_thinkbell_question(request, pk):
    question = get_object_or_404(SlideQuestion, pk=pk)
    sid = question.section.id
    question.delete()
    messages.info(request, "Module removed successfully.")
    return redirect('manage_thinkbell_questions', section_id=sid)


# =========================================================
#                 QUIZ CLUB LOGIC
# =========================================================
@user_passes_test(is_admin, login_url='admin_login')
def quiz_club_view(request):
    sections = AppSection.objects.filter(section_type='QC')
    return render(request, 'quiz_club.html', {'sections': sections})


@user_passes_test(is_admin, login_url='admin_login')
def manage_quiz_club_questions(request, section_id):
    section = get_object_or_404(AppSection, id=section_id)
    questions = SlideQuestion.objects.filter(section=section).prefetch_related('slides')
    return render(request, 'quiz_club_questions.html', {'section': section, 'questions': questions})


@user_passes_test(is_admin, login_url='admin_login')
@user_passes_test(is_admin, login_url='admin_login')
def add_quiz_club_question(request):
    section_id = request.POST.get('section_id') or request.GET.get('section_id')
    section = get_object_or_404(AppSection, id=section_id)

    if request.method == "POST":
        title = request.POST.get('title')
        
        # Create the main Question object
        q = SlideQuestion.objects.create(
            section=section,
            title=title,
            expected_answer_keywords=request.POST.get('keywords', ''),
            option_a=request.POST.get('opt_a'),
            option_b=request.POST.get('opt_b'),
            option_c=request.POST.get('opt_c'),
            option_d=request.POST.get('opt_d'),
            correct_option=request.POST.get('correct_option')
        )

        texts = request.POST.getlist('slide_text[]')
        
        # FIX: Loop through indices to match text with the specific file input
        for i in range(len(texts)):
            # We look for slide_image_0, slide_image_1, etc.
            image_key = f'slide_image_{i}'
            slide_image = request.FILES.get(image_key) 

            QuestionSlide.objects.create(
                question=q,
                text_content=texts[i],
                image=slide_image,
                order=i + 1
            )

        messages.success(request, "Module created successfully!")
        return redirect('manage_quiz_club_questions', section_id=section.id)

    return render(request, 'quiz_club_form.html', {'section': section})

@user_passes_test(is_admin, login_url='admin_login')
def edit_quiz_club_question(request, pk):
    question = get_object_or_404(SlideQuestion, pk=pk)
    section = question.section

    if request.method == "POST":
        question.title = request.POST.get('title')
        question.expected_answer_keywords = request.POST.get('keywords')
        question.option_a = request.POST.get('opt_a')
        question.option_b = request.POST.get('opt_b')
        question.option_c = request.POST.get('opt_c')
        question.option_d = request.POST.get('opt_d')
        question.correct_option = request.POST.get('correct_option')
        question.save()

        # Handle Slides: Delete old ones and recreate
        texts = request.POST.getlist('slide_text[]')
        
        # Optional: Store old images in a dict if you want to keep them if no new one is uploaded
        old_slides = list(question.slides.all().order_by('order'))
        question.slides.all().delete()

        for i in range(len(texts)):
            image_key = f'slide_image_{i}'
            new_image = request.FILES.get(image_key)
            
            # Logic: Use new image if uploaded, else try to keep the old one (if index exists)
            existing_image = None
            if not new_image and i < len(old_slides):
                existing_image = old_slides[i].image

            QuestionSlide.objects.create(
                question=question,
                text_content=texts[i],
                image=new_image if new_image else existing_image,
                order=i + 1
            )

        messages.success(request, "Updated successfully!")
        return redirect('manage_quiz_club_questions', section_id=section.id)

    return render(request, 'quiz_club_form.html', {
        'question': question, 'section': section, 
        'slides': question.slides.all().order_by('order'), 'is_edit': True
    })
@user_passes_test(is_admin, login_url='admin_login')
def delete_quiz_club_question(request, pk):
    question = get_object_or_404(SlideQuestion, pk=pk)
    sid = question.section.id
    question.delete()
    return redirect('manage_quiz_club_questions', section_id=sid)


# =========================================================
#                 NEWSBYTES LOGIC
# =========================================================
@user_passes_test(is_admin, login_url='admin_login')
def newsbytes_view(request):
    """Renders the main NewsBytes sections dashboard."""
    sections = AppSection.objects.filter(section_type='NB')
    return render(request, 'newsbytes.html', {'sections': sections})

@user_passes_test(is_admin, login_url='admin_login')
def add_news_section(request):
    """Creates a new NewsBytes section category."""
    if request.method == "POST":
        name = request.POST.get('name')
        is_premium = request.POST.get('is_premium') == 'True'
        if name:
            AppSection.objects.create(name=name, section_type='NB', is_premium=is_premium)
    return redirect('newsbytes')

@user_passes_test(is_admin, login_url='admin_login')
def manage_news_section(request, section_id):
    """Displays the table of MCQs for a specific section."""
    section = get_object_or_404(AppSection, id=section_id)
    # This pulls data specifically for the table view
    questions = MCQQuestion.objects.filter(section=section).order_by('-id')
    return render(request, 'newsbytes_manage.html', {'section': section, 'questions': questions})

@user_passes_test(is_admin, login_url='admin_login')
def add_news_mcq(request, section_id):
    """Saves new MCQ data and redirects to the table."""
    section = get_object_or_404(AppSection, id=section_id)
    if request.method == "POST":
        MCQQuestion.objects.create(
            section=section,
            content=request.POST.get('content'),
            image=request.FILES.get('image'),
            option_a=request.POST.get('opt_a'),
            option_b=request.POST.get('opt_b'),
            option_c=request.POST.get('opt_c'),
            option_d=request.POST.get('opt_d'),
            correct_option=request.POST.get('correct_option')
        )
        messages.success(request, "MCQ Published!")
        return redirect('manage_news_section', section_id=section.id)
    return render(request, 'newsbytes_form.html', {'section': section, 'is_edit': False})

@user_passes_test(is_admin, login_url='admin_login')
def edit_news_mcq(request, pk):
    """Views existing data in the form and saves updates."""
    mcq = get_object_or_404(MCQQuestion, pk=pk)
    section = mcq.section
    if request.method == "POST":
        mcq.content = request.POST.get('content')
        mcq.option_a = request.POST.get('opt_a')
        mcq.option_b = request.POST.get('opt_b')
        mcq.option_c = request.POST.get('opt_c')
        mcq.option_d = request.POST.get('opt_d')
        mcq.correct_option = request.POST.get('correct_option')
        if request.FILES.get('image'):
            mcq.image = request.FILES.get('image')
        mcq.save()
        return redirect('manage_news_section', section_id=section.id)
    return render(request, 'newsbytes_form.html', {'mcq': mcq, 'section': section, 'is_edit': True})

@user_passes_test(is_admin, login_url='admin_login')
def delete_news_mcq(request, pk):
    """Deletes an MCQ and refreshes the table."""
    mcq = get_object_or_404(MCQQuestion, pk=pk)
    section_id = mcq.section.id
    mcq.delete()
    return redirect('manage_news_section', section_id=section_id)
# =========================================================
#                 STUDENTS & EXPORTS
# =========================================================
# Import the helper you just created
from django.db.models import Sum, Q
from .firebase_helper import get_firebase_users
from .models import StudentProfile, StudentAnswerRecord
@user_passes_test(is_admin, login_url='admin_login')
def all_students_view(request):

    firebase_users = get_firebase_users()

    # 🔹 Get section-wise scores from DB
    profiles = StudentProfile.objects.annotate(
        thinkbell_score=Sum(
            "studentanswerrecord__points_awarded",
            filter=Q(studentanswerrecord__thinkbell_question__isnull=False)
        ),
        quizclub_score=Sum(
            "studentanswerrecord__points_awarded",
            filter=Q(studentanswerrecord__slide_question__isnull=False)
        ),
        newsbytes_score=Sum(
            "studentanswerrecord__points_awarded",
            filter=Q(studentanswerrecord__news_question__isnull=False)
        ),
    )

    # 🔹 Convert to dictionary for fast lookup by email
    profile_map = {p.email: p for p in profiles}

    merged_students = []

    for user in firebase_users:
        email = user.get("email")

        profile = profile_map.get(email)

        merged_students.append({
            "email": email,
            "provider": user.get("provider"),
            "created": user.get("created"),
            "signed_in": user.get("signed_in"),
            "uid": user.get("uid"),

            # ✅ PHONE NUMBER FROM DB
            "phone_number": profile.phone_number if profile and profile.phone_number else None,

            # ✅ SCORES
            "thinkbell_score": profile.thinkbell_score if profile and profile.thinkbell_score else 0,
            "quizclub_score": profile.quizclub_score if profile and profile.quizclub_score else 0,
            "newsbytes_score": profile.newsbytes_score if profile and profile.newsbytes_score else 0,
            "total_score": profile.total_score if profile else 0,
        })

    return render(request, 'students_list.html', {
        'students': merged_students
    })






@user_passes_test(is_admin, login_url='admin_login')
def export_students_excel(request):
    """Generates Excel download of student data."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(['Username', 'Total Score', 'City'])
    for s in StudentProfile.objects.all():
        ws.append([s.user.username, s.total_score, s.city])
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename=Students.xlsx'
    wb.save(response)
    return response

@user_passes_test(is_admin, login_url='admin_login')
def export_students_pdf(request):
    """Generates PDF download using a template."""
    students = StudentProfile.objects.all()
    template = get_template('pdf_template.html')
    html = template.render({'students': students})
    result = BytesIO()
    pisa.pisaDocument(BytesIO(html.encode("UTF-8")), result)
    return HttpResponse(result.getvalue(), content_type='application/pdf')@user_passes_test(is_admin, login_url='admin_login')

@user_passes_test(is_admin, login_url='admin_login')
def export_students_excel(request):
    """Generates Excel download of student data from Firebase."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Firebase Students"
    
    # 1. Update headers to match your Firebase data structure
    ws.append(['Email/Identifier', 'Provider', 'Created At', 'Last Signed In', 'UID'])
    
    # 2. Fetch live data from Firebase (same helper used in the list view)
    firebase_users = get_firebase_users()
    
    # 3. Iterate through the list of dictionaries
    for s in firebase_users:
        ws.append([
            s.get('email', 'N/A'),
            s.get('provider', 'N/A'),
            s.get('created', 'N/A'),
            s.get('signed_in', 'N/A'),
            s.get('uid', 'N/A')
        ])
    
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename=Firebase_Students_List.xlsx'
    wb.save(response)
    return response

@user_passes_test(is_admin, login_url='admin_login')
def export_students_pdf(request):
    """Generates PDF download using Firebase data."""
    # Change this line:
    students = get_firebase_users() 
    
    template = get_template('pdf_template.html')
    html = template.render({'students': students})
    result = BytesIO()
    pisa.pisaDocument(BytesIO(html.encode("UTF-8")), result)
    return HttpResponse(result.getvalue(), content_type='application/pdf')

@user_passes_test(is_admin, login_url='admin_login')
def delete_section_view(request, pk):
    section = get_object_or_404(AppSection, pk=pk)
    s_type = section.section_type
    section.delete()
    messages.info(request, "Section deleted successfully.")
    if s_type == 'TB':
        return redirect('thinkbell')
    elif s_type == 'NB':
        return redirect('newsbytes')
    return redirect('quiz_club')


from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import user_passes_test
from .models import Announcement

def is_admin(user):
    return user.is_superuser


# Assuming is_admin is defined elsewhere
@user_passes_test(is_admin, login_url='admin_login')
def announcement_manage(request):
    if request.method == "POST":
        # Only collecting title and image from the request
        Announcement.objects.create(
            title=request.POST.get('title'),
            image=request.FILES.get('image')
        )
        return redirect('announcements')

    announcements = Announcement.objects.all().order_by('-date_posted')
    return render(request, 'announcements.html', {
        'announcements': announcements
    })

def delete_announcement(request, pk):
    item = get_object_or_404(Announcement, pk=pk)
    item.delete()
    return redirect('announcements')


# @user_passes_test(is_admin, login_url='admin_login')
# def announcement_manage(request):
#     if request.method == "POST":
#         Announcement.objects.create(
#             title=request.POST.get('title'),
#             content=request.POST.get('content'),
#             target_audience="All Students",  # Set default to avoid IntegrityError
#             image=request.FILES.get('image')
#         )
#         return redirect('announcements')

#     # Use 'date_posted' instead of 'created_at' to fix the FieldError
#     announcements = Announcement.objects.all().order_by('-date_posted')
#     return render(request, 'announcements.html', {'announcements': announcements})


def quiz_shows_manage(request):
    if request.method == "POST":
        title = request.POST.get('title')
        link = request.POST.get('youtube_link')
        desc = request.POST.get('description')

        # Save to database
        QuizShow.objects.create(
            title=title,
            youtube_link=link,
            description=desc
        )
        return redirect('quiz_shows')

    shows = QuizShow.objects.all().order_by('-created_at')
    return render(request, 'quiz_shows.html', {'shows': shows})

@user_passes_test(is_admin, login_url='admin_login')
def delete_quiz_show(request, pk):
    show = get_object_or_404(QuizShow, pk=pk)
    show.delete()
    return redirect('quiz_shows')


# LIVE EVENTS VIEW
def live_events_manage(request):
    if request.method == "POST":
        LiveEvent.objects.create(
            event_name=request.POST.get('event_name'),
            description=request.POST.get('description'),
            event_date=request.POST.get('event_date'),
            location=request.POST.get('location')
        )
        return redirect('live_events')

    events = LiveEvent.objects.all().order_by('-event_date')
    return render(request, 'live_events.html', {'events': events})


# GENERIC DELETE (Optional helper)
def delete_item(request, model_type, pk):
    models = {'announcement': Announcement, 'quiz': QuizShow, 'event': LiveEvent}
    item = get_object_or_404(models[model_type], pk=pk)
    item.delete()
    return redirect(request.META.get('HTTP_REFERER'))

import google.generativeai as genai
import re
from django.shortcuts import render, get_object_or_404
from .models import Question, StudentAnswer

# Configure Gemini API
# genai.configure(api_key="AIzaSyCm49WK4EErBCiJziylVBdMtJW7K8Gg0os")
print("GEMINI KEY:", settings.GEMINI_API_KEY)

from django.http import HttpResponse
from .models import StudentAnswerRecord, StudentProfile
import re

def student_exam_view(request, question_id):
    question = get_object_or_404(Question, id=question_id)
    result = None

    if request.method == "POST":
        student_text = request.POST.get('student_answer')

        # 🔐 get student (session or fallback for now)
        email = request.session.get("email")

        if email:
            try:
                student = StudentProfile.objects.get(email=email)
            except StudentProfile.DoesNotExist:
                student = StudentProfile.objects.first()
        else:
            student = StudentProfile.objects.first()

        # 🚫 prevent multiple attempts
        already = StudentAnswerRecord.objects.filter(
            student=student,
            thinkbell_question=question
        ).exists()

        if already:
            return HttpResponse("You already answered this question")

        # 🤖 AI PROMPT (YOUR NO2 FIXED FORMAT)
        prompt = f"""
Analyze this student's answer based on the question.

Question: {question.text}
Student Answer: {student_text}

Above is the question and answer by a student. Now give report in below format

Gallup – Thinking & Decision-Making Report

Purpose: This report helps parents understand how their child thinks, reasons, and makes decisions in challenging situations.

Scenario Summary:
The student was given a situation where a police officer must decide whether to continue chasing a dangerous criminal or stop to help an injured civilian.

Student’s Decision
The student chose to continue chasing the criminal, believing that stopping the criminal would prevent greater harm to society in the future.

Detailed Evaluation

Area Assessed – Observation
Understanding of Situation – Clear understanding of the problem and the choices involved.
Decision Clarity – Decision was firm and confident.
Reasoning Ability – Good logical thinking with focus on future consequences.
Values Shown – Concern for public safety and society at large.
Empathy & Responsibility – Needs improvement in showing care for the injured individual.

Final Thinking Score
7.5 / 10 – Good thinking maturity for the age group.

Strong Points

Thinks about long-term impact

Prioritises safety of many people

Shows confidence in difficult decisions

Thinking Style Identified
Future-focused and outcome-oriented thinker.

Areas to Work On

Showing empathy alongside strong decisions

Taking responsibility even when delegating tasks

Parent Note
Your child is developing strong logical and decision-making skills. Encouraging them to balance firm choices with compassion will help them grow into a thoughtful and responsible individual.
"""

        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(prompt)

        if response and hasattr(response, "text"):
            cleaned_text = re.sub(r'\*+', '', response.text)
            result = cleaned_text.strip()
        else:
            result = "AI could not generate feedback at this time."

        # 🧾 Save AI report (your existing table)
        StudentAnswer.objects.create(
            question=question,
            answer_text=student_text,
            ai_feedback=result
        )

        # 🧠 EXTRACT SCORE FROM FIXED TEXT (7.5 / 10)
        score_match = re.search(r'(\d+(\.\d+)?)\s*/\s*10', result)

        if score_match:
            ai_score_10 = float(score_match.group(1))  # e.g. 7.5
            score = round(ai_score_10 / 2)  # convert to 0–5 scale
        else:
            score = 0

        # 🗂 Save for Admin scoring table
        StudentAnswerRecord.objects.create(
            student=student,
            thinkbell_question=question,
            descriptive_answer=student_text,
            ai_score=score,
            points_awarded=score
        )

        # ➕ Update total score
        student.total_score += score
        student.save()

    return render(request, 'exam.html', {
        'question': question,
        'result': result
    })



def add_points(student, points):
    student.total_score += points
    student.save()



def submit_quizclub_mcq(request, question_id):
    question = get_object_or_404(SlideQuestion, id=question_id)

    if request.method == "POST":
        selected_option = request.POST.get("selected_option")

        email = request.session.get("email")
        if not email:
            return HttpResponse("Student not logged in")

        student = StudentProfile.objects.get(email=email)

        correct = question.correct_option == selected_option
        points = 1 if correct else 0

        already = StudentAnswerRecord.objects.filter(
            student=student,
            slide_question=question
        ).exists()

        if already:
            return HttpResponse("You already answered this question")

        StudentAnswerRecord.objects.create(
            student=student,
            slide_question=question,
            selected_option=selected_option,
            is_correct=correct,
            points_awarded=points
        )

        add_points(student, points)

        return HttpResponse("Answer submitted")

    return HttpResponse("Invalid request")




def submit_news_mcq(request, question_id):
    question = get_object_or_404(MCQQuestion, id=question_id)

    if request.method == "POST":
        selected_option = request.POST.get("selected_option")

        email = request.session.get("email")
        if not email:
            return HttpResponse("Student not logged in")

        student = StudentProfile.objects.get(email=email)

        correct = question.correct_option == selected_option
        points = 1 if correct else 0

        # prevent multiple attempts
        already = StudentAnswerRecord.objects.filter(
            student=student,
            news_question=question
        ).exists()

        if already:
            return HttpResponse("You already answered this question")

        # save answer
        StudentAnswerRecord.objects.create(
            student=student,
            news_question=question,
            selected_option=selected_option,
            is_correct=correct,
            points_awarded=points
        )

        # update total score
        student.total_score += points
        student.save()

        return HttpResponse("Answer submitted")

    return HttpResponse("Invalid request")


def get_current_student(request):
    email = request.session.get("email")
    if not email:
        return None
    try:
        return StudentProfile.objects.get(email=email)
    except StudentProfile.DoesNotExist:
        return None
    



from rest_framework.views import APIView
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.db.models import Sum


def get_section_progress(student, section_type):
    data = []

    if section_type == 'QC':
        sections = AppSection.objects.filter(section_type='QC')
        for section in sections:
            total = SlideQuestion.objects.filter(section=section).count()

            attempted = StudentAnswerRecord.objects.filter(
                student=student,
                slide_question__section=section
            ).count()

            score = StudentAnswerRecord.objects.filter(
                student=student,
                slide_question__section=section
            ).aggregate(total=Sum("points_awarded"))["total"] or 0

            completed = total > 0 and attempted == total

            data.append({
                "section_id": section.id,
                "section_name": section.name,
                "total_questions": total,
                "attempted_questions": attempted,
                "score": score,
                "completed": completed
            })

    if section_type == 'NB':
        sections = AppSection.objects.filter(section_type='NB')
        for section in sections:
            total = MCQQuestion.objects.filter(section=section).count()

            attempted = StudentAnswerRecord.objects.filter(
                student=student,
                news_question__section=section
            ).count()

            score = StudentAnswerRecord.objects.filter(
                student=student,
                news_question__section=section
            ).aggregate(total=Sum("points_awarded"))["total"] or 0

            completed = total > 0 and attempted == total

            data.append({
                "section_id": section.id,
                "section_name": section.name,
                "total_questions": total,
                "attempted_questions": attempted,
                "score": score,
                "completed": completed
            })

    return data



class NewsBytesProgressAPI(APIView):

    @swagger_auto_schema(
        operation_description="NewsBytes progress",
        manual_parameters=[
            openapi.Parameter('email', openapi.IN_QUERY, type=openapi.TYPE_STRING)
        ]
    )
    def get(self, request):
        email = request.GET.get("email")
        student = get_object_or_404(StudentProfile, email=email)

        data = get_section_progress(student, 'NB')
        return Response(data)
    



class FullProgressAPI(APIView):

    @swagger_auto_schema(
        operation_description="Full progress",
        manual_parameters=[
            openapi.Parameter('email', openapi.IN_QUERY, type=openapi.TYPE_STRING)
        ]
    )
    def get(self, request):
        email = request.GET.get("email")
        student = get_object_or_404(StudentProfile, email=email)

        return Response({
            "quizclub": get_section_progress(student, 'QC'),
            "newsbytes": get_section_progress(student, 'NB'),
            "total_score": student.total_score
        })
    


class AIExamAPI(APIView):

    @swagger_auto_schema(
        operation_description="Submit descriptive answer and get AI evaluation",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["email", "question_id", "student_answer"],
            properties={
                "email": openapi.Schema(type=openapi.TYPE_STRING),
                "question_id": openapi.Schema(type=openapi.TYPE_INTEGER),
                "student_answer": openapi.Schema(type=openapi.TYPE_STRING),
            },
        ),
    )
    def post(self, request):

        email = request.data.get("email")
        question_id = request.data.get("question_id")
        student_text = request.data.get("student_answer")

        student = get_object_or_404(StudentProfile, email=email)
        question = get_object_or_404(Question, id=question_id)

        already = StudentAnswerRecord.objects.filter(
            student=student,
            thinkbell_question=question
        ).exists()

        if already:
            return Response({"message": "Already answered"}, status=400)

        prompt = f"""
Question: {question.text}
Student Answer: {student_text}
Give report and final score like 7.5 / 10
"""

        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(prompt)

        ai_result = response.text if response and hasattr(response, "text") else "AI failed"

        score_match = re.search(r'(\d+(\.\d+)?)\s*/\s*10', ai_result)
        score = round(float(score_match.group(1)) / 2) if score_match else 0

        StudentAnswerRecord.objects.create(
            student=student,
            thinkbell_question=question,
            descriptive_answer=student_text,
            ai_score=score,
            points_awarded=score
        )

        student.total_score += score
        student.save()

        return Response({
            "ai_feedback": ai_result,
            "score_awarded": score,
            "total_score": student.total_score
        })
    



class LeaderboardAPI(APIView):

    @swagger_auto_schema(operation_description="Top students leaderboard")
    def get(self, request):

        top_students = StudentProfile.objects.order_by('-total_score')[:10]

        data = []
        for s in top_students:
            data.append({
                "email": s.email,
                "total_score": s.total_score
            })

        return Response(data)
    



    # =============================
# 🔥 SWAGGER APIs START
# =============================

from rest_framework.views import APIView
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.db.models import Sum

# 🟢 TEST API
class TestAPI(APIView):
    def get(self, request):
        return Response({"message": "Swagger working"})


# 🟢 QUIZCLUB PROGRESS API
class QuizClubProgressAPI(APIView):

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter('email', openapi.IN_QUERY, type=openapi.TYPE_STRING)
        ]
    )
    def get(self, request):

        email = request.GET.get("email")
        student = get_object_or_404(StudentProfile, email=email)

        sections = AppSection.objects.filter(section_type='QC')

        data = []

        for section in sections:
            total = SlideQuestion.objects.filter(section=section).count()

            attempted = StudentAnswerRecord.objects.filter(
                student=student,
                slide_question__section=section
            ).count()

            score = StudentAnswerRecord.objects.filter(
                student=student,
                slide_question__section=section
            ).aggregate(total=Sum("points_awarded"))["total"] or 0

            completed = total > 0 and attempted == total

            data.append({
                "section_name": section.name,
                "total_questions": total,
                "attempted_questions": attempted,
                "score": score,
                "completed": completed
            })

        return Response(data)


# 🟢 NEWSBYTES PROGRESS API
class NewsBytesProgressAPI(APIView):

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter('email', openapi.IN_QUERY, type=openapi.TYPE_STRING)
        ]
    )
    def get(self, request):

        email = request.GET.get("email")
        student = get_object_or_404(StudentProfile, email=email)

        sections = AppSection.objects.filter(section_type='NB')

        data = []

        for section in sections:
            total = MCQQuestion.objects.filter(section=section).count()

            attempted = StudentAnswerRecord.objects.filter(
                student=student,
                news_question__section=section
            ).count()

            score = StudentAnswerRecord.objects.filter(
                student=student,
                news_question__section=section
            ).aggregate(total=Sum("points_awarded"))["total"] or 0

            completed = total > 0 and attempted == total

            data.append({
                "section_name": section.name,
                "total_questions": total,
                "attempted_questions": attempted,
                "score": score,
                "completed": completed
            })

        return Response(data)


# 🟢 FULL PROGRESS API
class FullProgressAPI(APIView):

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter('email', openapi.IN_QUERY, type=openapi.TYPE_STRING)
        ]
    )
    def get(self, request):

        email = request.GET.get("email")
        student = get_object_or_404(StudentProfile, email=email)

        return Response({
            "quizclub": QuizClubProgressAPI().get(request).data,
            "newsbytes": NewsBytesProgressAPI().get(request).data,
            "total_score": student.total_score
        })


# 🟢 AI EXAM API (THINKBELL DESCRIPTIVE)
class AIExamAPI(APIView):

    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["email", "question_id", "student_answer"],
            properties={
                "email": openapi.Schema(type=openapi.TYPE_STRING),
                "question_id": openapi.Schema(type=openapi.TYPE_INTEGER),
                "student_answer": openapi.Schema(type=openapi.TYPE_STRING),
            },
        )
    )
    def post(self, request):

        email = request.data.get("email")
        question_id = request.data.get("question_id")
        student_text = request.data.get("student_answer")

        student = get_object_or_404(StudentProfile, email=email)
        question = get_object_or_404(Question, id=question_id)

        prompt = f"Question: {question.text} Student Answer: {student_text} Give final score like 7.5 / 10"

        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(prompt)

        ai_result = response.text if response and hasattr(response, "text") else "AI failed"

        score_match = re.search(r'(\d+(\.\d+)?)\s*/\s*10', ai_result)
        score = round(float(score_match.group(1)) / 2) if score_match else 0

        StudentAnswerRecord.objects.create(
            student=student,
            thinkbell_question=question,
            descriptive_answer=student_text,
            ai_score=score,
            points_awarded=score
        )

        student.total_score += score
        student.save()

        return Response({
            "ai_feedback": ai_result,
            "score_awarded": score,
            "total_score": student.total_score
        })


# 🟢 LEADERBOARD API
class LeaderboardAPI(APIView):

    def get(self, request):

        top_students = StudentProfile.objects.order_by('-total_score')[:10]

        data = []

        for s in top_students:
            data.append({
                "email": s.email,
                "total_score": s.total_score
            })

        return Response(data)




# 🟢 ANNOUNCEMENTS API
class AnnouncementAPI(APIView):

    def get(self, request):
        announcements = Announcement.objects.all().order_by('-date_posted')

        data = []

        for a in announcements:
            data.append({
                "id": a.id,
                "title": a.title,
                "content": a.content,
                "image": a.image.url if a.image else None,
                "date_posted": a.date_posted
            })

        return Response(data)


# 🟢 QUIZ SHOWS API
class QuizShowAPI(APIView):

    def get(self, request):
        shows = QuizShow.objects.all().order_by('-created_at')

        data = []

        for s in shows:
            data.append({
                "id": s.id,
                "title": s.title,
                "youtube_link": s.youtube_link,
                "description": s.description,
                "created_at": s.created_at
            })

        return Response(data)


# 🟢 LIVE EVENTS API
class LiveEventAPI(APIView):

    def get(self, request):
        events = LiveEvent.objects.all().order_by('-event_date')

        data = []

        for e in events:
            data.append({
                "id": e.id,
                "event_name": e.event_name,
                "description": e.description,
                "event_date": e.event_date,
                "location": e.location
            })

        return Response(data)



from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
import re

class CheckPhoneAPI(APIView):

    @swagger_auto_schema(
        operation_description="Check if phone number is required for this student",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["email"],
            properties={
                "email": openapi.Schema(type=openapi.TYPE_STRING, example="student@gmail.com"),
            },
        ),
        responses={
            200: openapi.Response(
                description="Phone check result",
                examples={
                    "application/json": {
                        "phone_required": True
                    }
                }
            )
        }
    )
    def post(self, request):

        email = request.data.get("email")

        if not email:
            return Response({"error": "Email required"}, status=400)

        student, created = StudentProfile.objects.get_or_create(email=email)

        if student.phone_number:
            return Response({
                "phone_required": False,
                "phone_number": student.phone_number
            })

        return Response({
            "phone_required": True
        })

# ✅ 2️⃣ SAVE PHONE API
class SavePhoneAPI(APIView):

    @swagger_auto_schema(
        operation_description="Save phone number for first time login",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["email", "phone_number"],
            properties={
                "email": openapi.Schema(type=openapi.TYPE_STRING, example="student@gmail.com"),
                "phone_number": openapi.Schema(type=openapi.TYPE_STRING, example="9876543210"),
            },
        ),
        responses={
            200: openapi.Response(
                description="Phone saved successfully",
                examples={
                    "application/json": {
                        "message": "Phone number saved successfully"
                    }
                }
            )
        }
    )
    def post(self, request):

        email = request.data.get("email")
        phone = request.data.get("phone_number")

        if not email or not phone:
            return Response({"error": "Email and phone required"}, status=400)

        import re
        if not re.match(r'^[6-9]\d{9}$', phone):
            return Response({"error": "Invalid phone number"}, status=400)

        student = get_object_or_404(StudentProfile, email=email)

        if student.phone_number:
            return Response({"message": "Phone already saved"}, status=400)

        student.phone_number = phone
        student.save()

        return Response({
            "message": "Phone number saved successfully"
        })


class QuizClubQuestionAPI(APIView):

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter('section_id', openapi.IN_QUERY, type=openapi.TYPE_INTEGER)
        ]
    )
    def get(self, request):

        section_id = request.GET.get("section_id")

        if not section_id:
            return Response({"error": "section_id required"}, status=400)

        section = get_object_or_404(AppSection, id=section_id, section_type='QC')

        questions = SlideQuestion.objects.filter(section=section).order_by("id")

        if not questions.exists():
            return Response({"error": "No questions in this section"}, status=404)

        data = []

        for index, q in enumerate(questions, start=1):
            data.append({
                "question_id": q.id,
                "question_number": index,

                "section_id": section.id,        # ✅ ADDED
                "section_name": section.name,    # ✅ ADDED

                "question": q.title,
                "options": {
                    "A": q.option_a,
                    "B": q.option_b,
                    "C": q.option_c,
                    "D": q.option_d,
                }
            })

        return Response({
            "total_questions": questions.count(),
            "questions": data
        })
    
class SubmitQuizClubMCQAPI(APIView):

    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["email", "question_id", "selected_option"],
            properties={
                "email": openapi.Schema(type=openapi.TYPE_STRING),
                "question_id": openapi.Schema(type=openapi.TYPE_INTEGER),
                "selected_option": openapi.Schema(type=openapi.TYPE_STRING),
            },
        ),
    )
    def post(self, request):

        email = request.data.get("email")
        question_id = request.data.get("question_id")
        selected_option = request.data.get("selected_option")

        student = get_object_or_404(StudentProfile, email=email)
        question = get_object_or_404(SlideQuestion, id=question_id)

        already = StudentAnswerRecord.objects.filter(
            student=student,
            slide_question=question
        ).exists()

        if already:
            return Response({"message": "Already answered"}, status=400)

        correct = question.correct_option == selected_option
        points = 1 if correct else 0

        StudentAnswerRecord.objects.create(
            student=student,
            slide_question=question,
            selected_option=selected_option,
            is_correct=correct,
            points_awarded=points
        )

        student.total_score += points
        student.save()

        # ✅ Section completion check
        total = SlideQuestion.objects.filter(section=question.section).count()
        attempted = StudentAnswerRecord.objects.filter(
            student=student,
            slide_question__section=question.section
        ).count()

        section_completed = total > 0 and attempted == total

        return Response({
            "question_id": question_id,
            "correct": correct,
            "correct_answer": question.correct_option if not correct else None,
            "points_awarded": points,
            "section_completed": section_completed,
            "total_score": student.total_score
        })

class SubmitNewsBytesMCQAPI(APIView):

    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["email", "question_id", "selected_option"],
            properties={
                "email": openapi.Schema(type=openapi.TYPE_STRING),
                "question_id": openapi.Schema(type=openapi.TYPE_INTEGER),
                "selected_option": openapi.Schema(type=openapi.TYPE_STRING),
            },
        ),
    )
    def post(self, request):

        email = request.data.get("email")
        question_id = request.data.get("question_id")
        selected_option = request.data.get("selected_option")

        student = get_object_or_404(StudentProfile, email=email)
        question = get_object_or_404(MCQQuestion, id=question_id)

        already = StudentAnswerRecord.objects.filter(
            student=student,
            news_question=question
        ).exists()

        if already:
            return Response({"message": "Already answered"}, status=400)

        correct = question.correct_option == selected_option
        points = 1 if correct else 0

        StudentAnswerRecord.objects.create(
            student=student,
            news_question=question,
            selected_option=selected_option,
            is_correct=correct,
            points_awarded=points
        )

        student.total_score += points
        student.save()

        # ✅ Section completion check
        total = MCQQuestion.objects.filter(section=question.section).count()
        attempted = StudentAnswerRecord.objects.filter(
            student=student,
            news_question__section=question.section
        ).count()

        section_completed = total > 0 and attempted == total

        return Response({
            "question_id": question_id,
            "correct": correct,
            "correct_answer": question.correct_option if not correct else None,
            "points_awarded": points,
            "section_completed": section_completed,
            "total_score": student.total_score
        })



class AIExamQuestionAPI(APIView):

    def get(self, request):

        questions = Question.objects.all().order_by("id")

        if not questions.exists():
            return Response({"error": "No questions available"}, status=404)

        data = []

        for index, q in enumerate(questions, start=1):
            data.append({
                "question_number": index,
                "question": q.text
            })

        return Response(data)




class AIExamAPI(APIView):

    @swagger_auto_schema(
        operation_description="Submit Descriptive Answer for AI Evaluation",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["email", "question_number", "student_answer"],
            properties={
                "email": openapi.Schema(type=openapi.TYPE_STRING, example="student@gmail.com"),
                "question_number": openapi.Schema(type=openapi.TYPE_INTEGER, example=1),
                "student_answer": openapi.Schema(type=openapi.TYPE_STRING, example="I would save the civilian because it is the right thing to do."),
            },
        ),
    )
    def post(self, request):
        email = request.data.get("email")
        question_number = request.data.get("question_number")
        student_text = request.data.get("student_answer")

        # 1. Validation
        missing_fields = [f for f, v in [("email", email), ("question_number", question_number), ("student_answer", student_text)] if not v]
        if missing_fields:
            return Response({"error": f"Missing fields: {', '.join(missing_fields)}"}, status=400)

        student = get_object_or_404(StudentProfile, email=email)
        questions = Question.objects.all().order_by("id")

        try:
            q_num = int(question_number)
            question = questions[q_num - 1]
        except (ValueError, IndexError):
            return Response({"error": "Invalid question_number"}, status=400)

        # 2. Prevent Multiple Attempts
        already = StudentAnswerRecord.objects.filter(
            student=student,
            thinkbell_question=question
        ).exists()

        if already:
            return Response({"message": "Already answered"}, status=400)

        # 3. AI Evaluation Prompt
        prompt = f"""
Analyze this student's answer based on the question.

Question: {question.text}
Student Answer: {student_text}

Above is the question and answer by a student. Now give report in below format

Gallup – Thinking & Decision-Making Report

Purpose: This report helps parents understand how their child thinks, reasons, and makes decisions in challenging situations.

Scenario Summary:
Write a short summary of the situation.

Student’s Decision
Explain what the student decided.

Detailed Evaluation

Area Assessed – Observation
Understanding of Situation –
Decision Clarity –
Reasoning Ability –
Values Shown –
Empathy & Responsibility –

Final Thinking Score
Give score like 7.5 / 10

Strong Points
Give 3 bullet points

Thinking Style Identified
One line

Areas to Work On
Give 2 bullet points

Parent Note
2–3 lines for parents
"""

        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(prompt)

        if response and hasattr(response, "text"):
            ai_result = re.sub(r"\*+", "", response.text).strip()
        else:
            ai_result = "AI could not generate feedback"

        # 4. Extract Score
        score_match = re.search(r'(\d+(\.\d+)?)\s*/\s*10', ai_result)

        if score_match:
            ai_score_10 = float(score_match.group(1))
            score = round(ai_score_10 / 2)  # Convert to 0–5 scale
        else:
            score = 0

        # 5. Save to Database
        StudentAnswerRecord.objects.create(
            student=student,
            thinkbell_question=question,
            descriptive_answer=student_text,
            ai_score=score,
            points_awarded=score
        )

        student.total_score += score
        student.save()

        # 6. Check Completion Status
        total = questions.count()
        attempted = StudentAnswerRecord.objects.filter(
            student=student,
            thinkbell_question__isnull=False
        ).count()

        completed = (total > 0 and attempted >= total)
        task_msg = "All AI tasks completed successfully!" if completed else "AI Analysis saved."

        return Response({
            "question": question.text,
            "student_answer": student_text,
            "ai_feedback": ai_result,
            "score_awarded": score,
            "total_score": student.total_score,
            "completed": completed,
            "task_status": task_msg
        })




class SubmitThinkBellAIAPI(APIView):

    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["email", "question_id", "student_answer"],
            properties={
                "email": openapi.Schema(type=openapi.TYPE_STRING),
                "question_id": openapi.Schema(type=openapi.TYPE_INTEGER),
                "student_answer": openapi.Schema(type=openapi.TYPE_STRING),
            },
        ),
    )
    def post(self, request):

        email = request.data.get("email")
        question_id = request.data.get("question_id")
        student_text = request.data.get("student_answer")

        if not email or not question_id or not student_text:
            return Response({"error": "Missing fields"}, status=400)

        student = get_object_or_404(StudentProfile, email=email)
        question = get_object_or_404(SlideQuestion, id=question_id)

        # 🚫 prevent multiple attempts
        already = StudentAnswerRecord.objects.filter(
            student=student,
            thinkbell_question=question
        ).exists()

        if already:
            return Response({"message": "Already answered"}, status=400)

        # 🧠 FULL GALLUP PROMPT
        prompt = f"""
Analyze this student's answer based on the question.

Question: {question.title}
Student Answer: {student_text}

Above is the question and answer by a student. Now give report in below format

Gallup – Thinking & Decision-Making Report

Purpose: This report helps parents understand how their child thinks, reasons, and makes decisions in challenging situations.

Scenario Summary:
Write a short summary of the situation.

Student’s Decision
Explain what the student decided.

Detailed Evaluation

Area Assessed – Observation
Understanding of Situation –
Decision Clarity –
Reasoning Ability –
Values Shown –
Empathy & Responsibility –

Final Thinking Score
Give score like 7.5 / 10

Strong Points
Give 3 bullet points

Thinking Style Identified
One line

Areas to Work On
Give 2 bullet points

Parent Note
2–3 lines for parents
"""

        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(prompt)

        if response and hasattr(response, "text"):
            ai_result = re.sub(r"\*+", "", response.text).strip()
        else:
            ai_result = "AI could not generate feedback."

        # 🎯 Extract score from AI text
        score_match = re.search(r'(\d+(\.\d+)?)\s*/\s*10', ai_result)

        if score_match:
            ai_score_10 = float(score_match.group(1))  # e.g. 7.5
            score = round(ai_score_10 / 2)  # convert to 0–5
        else:
            score = 0

        # 💾 Save answer record
        StudentAnswerRecord.objects.create(
            student=student,
            thinkbell_question=question,
            descriptive_answer=student_text,
            ai_score=score,
            points_awarded=score
        )

        student.total_score += score
        student.save()

        # ✅ Section completion check
        total = SlideQuestion.objects.filter(section=question.section).count()
        attempted = StudentAnswerRecord.objects.filter(
            student=student,
            thinkbell_question__section=question.section
        ).count()

        section_completed = total > 0 and attempted == total

        return Response({
            "section_id": question.section.id,
            "question_id": question_id,
            "ai_feedback": ai_result,
            "score_awarded": score,
            "section_completed": section_completed,
            "total_score": student.total_score
        })
    


class ThinkBellSectionAPI(APIView):
    def get(self, request):

        sections = AppSection.objects.filter(section_type='TB')

        data = []
        for s in sections:
            total_questions = SlideQuestion.objects.filter(section=s).count()

            data.append({
                "section_id": s.id,
                "section_name": s.name,
                "total_questions": total_questions,
                "is_premium": s.is_premium
            })

        return Response(data)
    


class ThinkBellQuestionAPI(APIView):

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter('section_id', openapi.IN_QUERY, type=openapi.TYPE_INTEGER)
        ]
    )
    def get(self, request):

        section_id = request.GET.get("section_id")

        if not section_id:
            return Response({"error": "section_id required"}, status=400)

        section = get_object_or_404(AppSection, id=section_id, section_type='TB')

        questions = SlideQuestion.objects.filter(section=section).order_by("id")

        if not questions.exists():
            return Response({"error": "No questions in this section"}, status=404)

        data = []

        for q in questions:
            data.append({
                "question_id": q.id,

                "section_id": section.id,        # ✅ ADDED
                "section_name": section.name,    # ✅ ADDED

                "question": q.title
            })

        return Response({
            "total_questions": questions.count(),
            "questions": data
        })



class NewsBytesQuestionAPI(APIView):

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                'section_id',
                openapi.IN_QUERY,
                type=openapi.TYPE_INTEGER,
                description="NewsBytes Section ID"
            )
        ]
    )
    def get(self, request):

        section_id = request.GET.get("section_id")

        if not section_id:
            return Response({"error": "section_id required"}, status=400)

        section = get_object_or_404(AppSection, id=section_id, section_type='NB')

        questions = MCQQuestion.objects.filter(section=section).order_by("id")

        if not questions.exists():
            return Response({"error": "No questions in this section"}, status=404)

        data = []

        for q in questions:
            data.append({
                "question_id": q.id,

                "section_id": section.id,        # ✅ ADDED
                "section_name": section.name,    # ✅ ADDED

                "question": q.content,
                "options": {
                    "A": q.option_a,
                    "B": q.option_b,
                    "C": q.option_c,
                    "D": q.option_d,
                }
            })

        return Response({
            "total_questions": questions.count(),
            "questions": data
        })



# =========================================================
# ✅ SECTION LIST APIs (FOR FRONTEND)
# =========================================================

from rest_framework.views import APIView
from rest_framework.response import Response

# 🔹 QUIZ CLUB SECTIONS LIST
class QuizClubSectionAPI(APIView):

    def get(self, request):

        sections = AppSection.objects.filter(section_type='QC').order_by('id')

        data = []

        for s in sections:
            data.append({
                "section_id": s.id,
                "section_name": s.name,
                "is_premium": s.is_premium
            })

        return Response({
            "total_sections": len(data),
            "sections": data
        })


# 🔹 NEWSBYTES SECTIONS LIST
class NewsBytesSectionAPI(APIView):

    def get(self, request):

        sections = AppSection.objects.filter(section_type='NB').order_by('id')

        data = []

        for s in sections:
            data.append({
                "section_id": s.id,
                "section_name": s.name,
                "is_premium": s.is_premium
            })

        return Response({
            "total_sections": len(data),
            "sections": data
        })


# 🔹 THINKBELL SECTIONS LIST
class ThinkBellSectionAPI(APIView):

    def get(self, request):

        sections = AppSection.objects.filter(section_type='TB').order_by('id')

        data = []

        for s in sections:
            data.append({
                "section_id": s.id,
                "section_name": s.name,
                "is_premium": s.is_premium
            })

        return Response({
            "total_sections": len(data),
            "sections": data
        })