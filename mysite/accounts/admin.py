from django.contrib import admin

# Register your models here.
from .models import Sequence
from .models import AlignmentTask

admin.site.register(Sequence)
admin.site.register(AlignmentTask)
