from django.urls import path
from . import views
from .views import (
    NewsBytesSectionAPI,
    QuizClubSectionAPI,
    TestAPI,
    QuizClubProgressAPI,
    NewsBytesProgressAPI,
    FullProgressAPI,
    AIExamAPI,
    LeaderboardAPI,
    AnnouncementAPI,
    QuizShowAPI,
    LiveEventAPI,
    CheckPhoneAPI,
    SavePhoneAPI,
    QuizClubQuestionAPI,
    SubmitQuizClubMCQAPI,
    NewsBytesQuestionAPI,
    SubmitNewsBytesMCQAPI,
    AIExamQuestionAPI,
    ThinkBellSectionAPI,
    ThinkBellQuestionAPI,
    SubmitThinkBellAIAPI,
    SubmitThinkBellSectionSingleAIAPI,
   
)
 



urlpatterns = [
    # --- Authentication & Core ---
    path('', views.index_view, name='index'),
    path('admin-login/', views.admin_login_view, name='admin_login'),
    path('logout/', views.admin_logout_view, name='admin_logout'),
    path('dashboard/', views.dashboard_view, name='dashboard'),

    # --- ThinkBell Management ---
    path('thinkbell/', views.thinkbell_view, name='thinkbell'),
    # Fixed: Action to create a new SECTION (Category card)
    path('thinkbell/add-section/', views.add_thinkbell_section, name='add_thinkbell_section'),
    # Fixed: Management table view
    path('thinkbell/manage/<int:section_id>/', views.manage_thinkbell_questions, name='manage_thinkbell_questions'),
    # Fixed: Correctly mapped to add_thinkbell_question view
    path('thinkbell/add-question/<int:section_id>/', views.add_thinkbell_question, name='add_thinkbell_question'),
    path('thinkbell/edit/<int:pk>/', views.edit_thinkbell_question, name='edit_thinkbell_question'),
    path('thinkbell/delete/<int:pk>/', views.delete_thinkbell_question, name='delete_thinkbell_question'),

    # --- Quiz Club ---
    path('quiz-club/', views.quiz_club_view, name='quiz_club'),
    # Fixed: Logic for adding sections and modules
    path('quiz-club/add/', views.add_quiz_club_question, name='add_quiz_club_question'),
    path('quiz-club/manage/<int:section_id>/', views.manage_quiz_club_questions, name='manage_quiz_club_questions'),
    path('quiz-club/edit/<int:pk>/', views.edit_quiz_club_question, name='edit_quiz_club_question'),
    path('quiz-club/delete-question/<int:pk>/', views.delete_quiz_club_question, name='delete_quiz_club_question'),

    # --- NewsBytes ---
    path('newsbytes/', views.newsbytes_view, name='newsbytes'),
    path('newsbytes/add/', views.add_news_section, name='add_news_section'),
    path('newsbytes/manage/<int:section_id>/', views.manage_news_section, name='manage_news_section'),
    path('newsbytes/add-mcq/<int:section_id>/', views.add_news_mcq, name='add_news_mcq'),
    path('newsbytes/edit-mcq/<int:pk>/', views.edit_news_mcq, name='edit_news_mcq'),
    path('newsbytes/delete-mcq/<int:pk>/', views.delete_news_mcq, name='delete_news_mcq'),


    # --- Students & Reporting ---
    path('students-report/', views.all_students_view, name='all_students'),
    path('export/excel/', views.export_students_excel, name='export_students_excel'),
    path('export/pdf/', views.export_students_pdf, name='export_students_pdf'),


    path('announcements/', views.announcement_manage, name='announcements'),
    path('announcements/delete/<int:pk>/', views.delete_announcement, name='delete_announcement'),
    path('quiz-shows/', views.quiz_shows_manage, name='quiz_shows'),
    path('quiz-shows/delete/<int:pk>/', views.delete_quiz_show, name='delete_quiz_show'),
    path('live-events/', views.live_events_manage, name='live_events'),
    # Unified delete path
    path('delete/<str:model_type>/<int:pk>/', views.delete_item, name='delete_item'),
    path('section/delete/<int:pk>/', views.delete_section_view, name='delete_section'),
    path('exam/<int:question_id>/', views.student_exam_view, name='student-exam'),
    path('submit-quizclub/<int:question_id>/', views.submit_quizclub_mcq, name='submit_quizclub'),
    path('submit-news/<int:question_id>/', views.submit_news_mcq, name='submit_news'),
     # =============================
    # 🔥 API ROUTES (MOBILE / SWAGGER)
    # =============================


    # TEST
    path('api/test/', TestAPI.as_view()),

    # PROGRESS
    path('api/progress/quizclub/', QuizClubProgressAPI.as_view()),
    path('api/progress/newsbytes/', NewsBytesProgressAPI.as_view()),
    path('api/progress/full/', FullProgressAPI.as_view()),

    # THINKBELL
    path('api/thinkbell/sections/', ThinkBellSectionAPI.as_view()),
    path('api/thinkbell/questions/', ThinkBellQuestionAPI.as_view()),
    path('api/thinkbell/submit/', SubmitThinkBellAIAPI.as_view()),

    # AI EXAM (OLD GLOBAL QUESTIONS)
    path('api/ai-exam/question/', AIExamQuestionAPI.as_view()),
    path('api/ai-exam/', AIExamAPI.as_view()),

    # QUIZCLUB MCQ
    path('api/quizclub/question/', QuizClubQuestionAPI.as_view()),
    path('api/quizclub/submit/', SubmitQuizClubMCQAPI.as_view()),

    # NEWSBYTES MCQ
    path('api/newsbytes/question/', NewsBytesQuestionAPI.as_view()),
    path('api/newsbytes/submit/', SubmitNewsBytesMCQAPI.as_view()),

    # LEADERBOARD & CONTENT
    path('api/leaderboard/', LeaderboardAPI.as_view()),
    path('api/announcements/', AnnouncementAPI.as_view()),
    path('api/quiz-shows/', QuizShowAPI.as_view()),
    path('api/live-events/', LiveEventAPI.as_view()),

    # PHONE CHECK
    path('api/check-phone/', CheckPhoneAPI.as_view()),
    path('api/save-phone/', SavePhoneAPI.as_view()),
    # ✅ SECTION LIST APIs
    path('api/quizclub/sections/', QuizClubSectionAPI.as_view(), name='quizclub-sections'),
    path('api/newsbytes/sections/', NewsBytesSectionAPI.as_view(), name='newsbytes-sections'),
    path('api/thinkbell/sections/', ThinkBellSectionAPI.as_view(), name='thinkbell-sections'),
    path('submit-thinkbell-section-single-ai/', SubmitThinkBellSectionSingleAIAPI.as_view()),
   






]


