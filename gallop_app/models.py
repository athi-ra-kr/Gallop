from django.db import models
from django.contrib.auth.models import User

class StudentProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    firebase_uid = models.CharField(max_length=128, unique=True, null=True, blank=True)
    email = models.EmailField(blank=True, null=True)
    provider = models.CharField(max_length=50, default='Email')

    phone_number = models.CharField(max_length=15, blank=True, null=True)

    created_at = models.DateTimeField(null=True, blank=True)
    last_login_time = models.DateTimeField(null=True, blank=True)

    total_score = models.IntegerField(default=0)

    # ✅ ADD THIS
    is_premium = models.BooleanField(default=False)

    def __str__(self):
        return self.email or self.firebase_uid
    
    
# --- Container Sections ---
class AppSection(models.Model):
    SECTION_TYPES = [('TB', 'ThinkBell'), ('NB', 'NewsBytes'), ('QC', 'Quiz Club')]
    name = models.CharField(max_length=100)
    # section_type identifies which module the section belongs to
    section_type = models.CharField(max_length=2, choices=SECTION_TYPES)
    is_premium = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.get_section_type_display()})"


# --- ThinkBell & Quiz Club (Slide Based with MCQ Assessment) ---
class SlideQuestion(models.Model):
    section = models.ForeignKey(AppSection, on_delete=models.CASCADE, related_name='questions')
    # title Fix: Ensures IntegrityError is avoided by making title a required field
    title = models.CharField(max_length=255)
    expected_answer_keywords = models.TextField(blank=True, null=True, help_text="Keywords for Gemini AI analysis")

    # Added Assessment Fields (MCQ): Prevents TypeError when saving modules with MCQ options
    option_a = models.CharField(max_length=255, blank=True, null=True)
    option_b = models.CharField(max_length=255, blank=True, null=True)
    option_c = models.CharField(max_length=255, blank=True, null=True)
    option_d = models.CharField(max_length=255, blank=True, null=True)
    correct_option = models.CharField(max_length=1, blank=True, null=True)

    def __str__(self):
        return self.title


class QuestionSlide(models.Model):
    question = models.ForeignKey(SlideQuestion, related_name='slides', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='slides/', null=True, blank=True)
    text_content = models.TextField()
    order = models.PositiveIntegerField(default=1)


# --- NewsBytes (Stand-alone MCQ Based) ---
class MCQQuestion(models.Model):
    # section linking for NewsBytes category
    section = models.ForeignKey(AppSection, on_delete=models.CASCADE, related_name="news_questions")
    content = models.TextField()
    image = models.ImageField(upload_to='news/', null=True, blank=True)
    option_a = models.CharField(max_length=200)
    option_b = models.CharField(max_length=200)
    option_c = models.CharField(max_length=200)
    option_d = models.CharField(max_length=200)
    correct_option = models.CharField(max_length=1)

    def __str__(self):
        return f"News MCQ: {self.content[:30]}..."


class Announcement(models.Model):
    title = models.CharField(max_length=200)
    # Changed to optional since they aren't in your new form
    content = models.TextField(blank=True, null=True) 
    target_audience = models.CharField(max_length=100, default="All Students", blank=True, null=True)
    image = models.ImageField(upload_to='announcements/', blank=True, null=True)
    date_posted = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
    

class QuizShow(models.Model):
    title = models.CharField(max_length=255)
    youtube_link = models.URLField() # Add this line if it's missing
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

class LiveEvent(models.Model):
    event_name = models.CharField(max_length=200)
    description = models.TextField()
    event_date = models.DateTimeField()
    location = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)



from django.db import models

class Question(models.Model):
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.text[:50]

class StudentAnswer(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    answer_text = models.TextField()
    ai_feedback = models.TextField(blank=True, null=True)
    submitted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Answer to: {self.question.text[:30]}"



class StudentAnswerRecord(models.Model):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE)

    slide_question = models.ForeignKey(SlideQuestion, on_delete=models.CASCADE, null=True, blank=True)
    question_slide = models.ForeignKey(QuestionSlide, on_delete=models.CASCADE, null=True, blank=True)  # ✅ ADD THIS
    news_question = models.ForeignKey(MCQQuestion, on_delete=models.CASCADE, null=True, blank=True)
    thinkbell_question = models.ForeignKey(Question, on_delete=models.CASCADE, null=True, blank=True)

    selected_option = models.CharField(max_length=1, null=True, blank=True)
    descriptive_answer = models.TextField(null=True, blank=True)

    is_correct = models.BooleanField(default=False)
    ai_score = models.IntegerField(default=0)
    points_awarded = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)