from django.contrib import admin

from .models import Attempt, AttemptAnswer, AttemptSection, WordMeaningItem


admin.site.register(Attempt)
admin.site.register(AttemptSection)
admin.site.register(AttemptAnswer)
admin.site.register(WordMeaningItem)
