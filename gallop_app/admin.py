from django.contrib import admin
from django.utils import timezone
from django.db.models import Sum
from datetime import datetime

from .models import (
    AppSection,
    MCQQuestion,
    SlideQuestion,
    QuestionSlide,
    StudentProfile,
    StudentAnswerRecord,
    Announcement,
    QuizShow,
    LiveEvent
)

from .firebase_helper import get_firebase_users

# ==============================
# 🔹 Inlines for Modules
# ==============================
class SlideInline(admin.StackedInline):
    model = QuestionSlide
    extra = 0
    fields = ("order", "text_content", "image")
    ordering = ("order",)

# ==============================
# 🔹 Announcement Admin
# ==============================
@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ('title', 'date_posted')
    search_fields = ('title',)
    list_filter = ('date_posted',)

# ==============================
# 🔹 QuizShow Admin
# ==============================
@admin.register(QuizShow)
class QuizShowAdmin(admin.ModelAdmin):
    list_display = ('title', 'youtube_link', 'created_at')
    search_fields = ('title',)

# ==============================
# 🔹 ThinkBell / QuizClub Modules
# ==============================
@admin.register(SlideQuestion)
class SlideQuestionAdmin(admin.ModelAdmin):
    list_display = ("title", "section", "slide_count", "correct_option")
    list_filter = ("section", "section__section_type")
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
# 🔹 Firebase Students + Score Sync
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

    def get_queryset(self, request):
        """Auto-sync Firebase data when viewing the list."""
        firebase_users = get_firebase_users()
        for user in firebase_users:
            email = user.get("email")
            uid = user.get("uid")
            if not email:
                continue

            student, created = StudentProfile.objects.get_or_create(
                email=email,
                defaults={
                    "firebase_uid": uid,
                    "provider": user.get("provider"),
                }
            )

            # Sync Updates
            student.firebase_uid = uid
            student.provider = user.get("provider")

            # Date Parsing Helpers
            try:
                if user.get("created"):
                    student.created_at = datetime.strptime(user.get("created"), "%b %d, %Y")
                
                signed_in = user.get("signed_in")
                if signed_in and signed_in != "Never":
                    student.last_login_time = datetime.strptime(signed_in, "%b %d, %Y")
            except Exception:
                pass

            student.save()
        return super().get_queryset(request)

    # --- Score Calculation Methods ---
    def thinkbell_score(self, obj):
        total = StudentAnswerRecord.objects.filter(
            student=obj, thinkbell_question__isnull=False
        ).aggregate(score=Sum("points_awarded"))["score"]
        return total or 0
    thinkbell_score.short_description = "Score (TB)"

    def quizclub_score(self, obj):
        total = StudentAnswerRecord.objects.filter(
            student=obj, slide_question__isnull=False
        ).aggregate(score=Sum("points_awarded"))["score"]
        return total or 0
    quizclub_score.short_description = "Score (QC)"

    def newsbytes_score(self, obj):
        total = StudentAnswerRecord.objects.filter(
            student=obj, news_question__isnull=False
        ).aggregate(score=Sum("points_awarded"))["score"]
        return total or 0
    newsbytes_score.short_description = "Score (NB)"

    # --- Formatting Methods ---
    def account_created_date(self, obj):
        return timezone.localtime(obj.created_at).date() if obj.created_at else "-"
    account_created_date.short_description = "Created"

    def last_login_date(self, obj):
        return timezone.localtime(obj.last_login_time).date() if obj.last_login_time else "-"
    last_login_date.short_description = "Last Sign In"

# ==============================
# 🔹 Answer Records
# ==============================
@admin.register(StudentAnswerRecord)
class StudentAnswerRecordAdmin(admin.ModelAdmin):
    list_display = (
        "student",
        "get_section_type",
        "points_awarded",
        "is_correct",
        "ai_score",
        "created_at",
    )
    list_filter = ("is_correct", "created_at")
    search_fields = ("student__email", "descriptive_answer")

    def get_section_type(self, obj):
        if obj.thinkbell_question: return "ThinkBell"
        if obj.slide_question: return "QuizClub"
        if obj.news_question: return "NewsBytes"
        return "Unknown"
    get_section_type.short_description = "Category"