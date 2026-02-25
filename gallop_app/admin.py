from django.contrib import admin
from django.utils import timezone
from django.db.models import Sum

from .models import (
    AppSection,
    MCQQuestion,
    SlideQuestion,
    QuestionSlide,
    
    StudentProfile,
    StudentAnswerRecord,
)

# ==============================
# 🔹 Slide Inline for Modules
# ==============================
class SlideInline(admin.StackedInline):   # ✅ CHANGED
    model = QuestionSlide
    extra = 0
    fields = ("order", "text_content", "image")  # ✅ SHOW TEACHING TEXT
    ordering = ("order",)


# ==============================
# 🔹 ThinkBell / QuizClub Modules
# ==============================
@admin.register(SlideQuestion)
class SlideQuestionAdmin(admin.ModelAdmin):
    list_display = ("title", "section", "slide_count", "correct_option")
    list_filter = ("section",)
    search_fields = ("title",)
    inlines = [SlideInline]

    def slide_count(self, obj):
        return obj.slides.count()
    slide_count.short_description = "Slides"


# ==============================
# 🔹 App Sections (TB / NB / QC)
# ==============================
@admin.register(AppSection)
class AppSectionAdmin(admin.ModelAdmin):
    list_display = ("name", "section_type", "is_premium", "is_active")
    list_filter = ("section_type", "is_premium", "is_active")
    search_fields = ("name",)


# ==============================
# 🔹 NewsBytes MCQ
# ==============================
@admin.register(MCQQuestion)
class MCQQuestionAdmin(admin.ModelAdmin):
    list_display = ("content", "section", "correct_option")
    list_filter = ("section",)
    search_fields = ("content",)


# ==============================
# 🔹 Firebase Students + TOTAL SCORE
# ==============================
@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = (
        "email",
        "firebase_uid",
        "phone_number",
        "provider",
        "total_score",
        "account_created_date",
        "last_login_date",
        "thinkbell_score",
        "quizclub_score",
        "newsbytes_score",
    )

    search_fields = ("email", "firebase_uid", "phone_number")
    list_filter = ("provider",)

    # 🔹 THINKBELL SCORE
    def thinkbell_score(self, obj):
        total = StudentAnswerRecord.objects.filter(
            student=obj,
            thinkbell_question__isnull=False
        ).aggregate(score=Sum("points_awarded"))["score"]
        return total or 0
    thinkbell_score.short_description = "ThinkBell"

    # 🔹 QUIZ CLUB SCORE
    def quizclub_score(self, obj):
        total = StudentAnswerRecord.objects.filter(
            student=obj,
            slide_question__isnull=False
        ).aggregate(score=Sum("points_awarded"))["score"]
        return total or 0
    quizclub_score.short_description = "QuizClub"

    # 🔹 NEWSBYTES SCORE
    def newsbytes_score(self, obj):
        total = StudentAnswerRecord.objects.filter(
            student=obj,
            news_question__isnull=False
        ).aggregate(score=Sum("points_awarded"))["score"]
        return total or 0
    newsbytes_score.short_description = "NewsBytes"

    # 🔹 DATE ONLY (NO TIME)
    def account_created_date(self, obj):
        if obj.created_at:
            return timezone.localtime(obj.created_at).date()
        return "-"
    account_created_date.short_description = "Account Created"

    def last_login_date(self, obj):
        if obj.last_login_time:
            return timezone.localtime(obj.last_login_time).date()
        return "-"
    last_login_date.short_description = "Last Sign In"





# ==============================
# 🔹 All MCQ + AI Score Records
# ==============================
@admin.register(StudentAnswerRecord)
class StudentAnswerRecordAdmin(admin.ModelAdmin):
    list_display = (
        "student",
        "slide_question",
        "question_slide",   # ✅ SHOW SLIDE LEVEL AI RECORD
        "news_question",
        "thinkbell_question",
        "is_correct",
        "ai_score",
        "points_awarded",
        "created_at",
    )
    list_filter = ("is_correct", "created_at")
    search_fields = ("student__email",)