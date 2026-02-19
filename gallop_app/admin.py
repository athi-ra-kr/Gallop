from django.contrib import admin
from django.utils import timezone

from .models import (
    AppSection,
    MCQQuestion,
    SlideQuestion,
    QuestionSlide,
    Question,
    StudentAnswer,
    StudentProfile,
    StudentAnswerRecord,   # ⭐ NEW
)

# ==============================
# 🔹 Slide Inline for Modules
# ==============================
class SlideInline(admin.TabularInline):
    model = QuestionSlide
    extra = 1


# ==============================
# 🔹 ThinkBell / QuizClub Modules
# ==============================
@admin.register(SlideQuestion)
class SlideQuestionAdmin(admin.ModelAdmin):
    list_display = ("title", "section", "correct_option")
    list_filter = ("section",)
    search_fields = ("title",)
    inlines = [SlideInline]


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
from django.contrib import admin
from django.utils import timezone
from django.db.models import Sum
from .models import StudentProfile, StudentAnswerRecord

from django.contrib import admin
from django.utils import timezone
from django.db.models import Sum
from .models import StudentProfile, StudentAnswerRecord


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = (
        "email",
        "firebase_uid",
        "phone_number",   # ✅ show phone
        "provider",
        "total_score",
        "created_at",
        "last_login_time",
    )

    search_fields = ("email", "firebase_uid", "phone_number")
    list_filter = ("provider",)
    # ✅ THINKBELL → AI marks sum
    def thinkbell_score(self, obj):
        total = StudentAnswerRecord.objects.filter(
            student=obj,
            thinkbell_question__isnull=False
        ).aggregate(score=Sum("points_awarded"))["score"]
        return total or 0
    thinkbell_score.short_description = "ThinkBell"

    # ✅ QUIZ CLUB → 1 per correct (stored in points_awarded)
    def quizclub_score(self, obj):
        total = StudentAnswerRecord.objects.filter(
            student=obj,
            slide_question__isnull=False
        ).aggregate(score=Sum("points_awarded"))["score"]
        return total or 0
    quizclub_score.short_description = "QuizClub"

    # ✅ NEWSBYTES → 1 per correct
    def newsbytes_score(self, obj):
        total = StudentAnswerRecord.objects.filter(
            student=obj,
            news_question__isnull=False
        ).aggregate(score=Sum("points_awarded"))["score"]
        return total or 0
    newsbytes_score.short_description = "NewsBytes"

    # ✅ DATE ONLY (NO TIME)
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
# 🔹 Exam Questions (ThinkBell Descriptive)
# ==============================
@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("text", "created_at")
    search_fields = ("text",)


# ==============================
# 🔹 Old AI Answers (keep if needed)
# ==============================
@admin.register(StudentAnswer)
class StudentAnswerAdmin(admin.ModelAdmin):
    list_display = ("question", "submitted_at")
    search_fields = ("answer_text", "ai_feedback")
    list_filter = ("submitted_at",)


# ==============================
# 🔹 NEW: All MCQ + AI Score Records
# ==============================
@admin.register(StudentAnswerRecord)
class StudentAnswerRecordAdmin(admin.ModelAdmin):
    list_display = (
        "student",
        "slide_question",
        "news_question",
        "thinkbell_question",
        "is_correct",
        "ai_score",
        "points_awarded",
        "created_at",
    )
    list_filter = ("is_correct", "created_at")
    search_fields = ("student__email",)