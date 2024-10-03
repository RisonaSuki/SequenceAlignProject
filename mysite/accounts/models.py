from django.db import models
from django.contrib.auth.models import User

# Create your models here.
class Sequence(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    file = models.FileField(upload_to='sequences/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class AlignmentTask(models.Model):
    TASK_STATUS = (
        ('PENDING', '等待中'),
        ('STARTED', '进行中'),
        ('SUCCESS', '成功'),
        ('FAILURE', '失败'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    sequence = models.ForeignKey(Sequence, on_delete=models.CASCADE)
    task_id = models.CharField(max_length=255, null=True, blank=True)
    status = models.CharField(max_length=10, choices=TASK_STATUS, default='PENDING')
    result_file = models.FileField(upload_to='alignment_results/', null=True, blank=True)
    plot_file = models.ImageField(upload_to='alignment_results/', null=True, blank=True)  # 新增字段
    created_at = models.DateTimeField(auto_now_add=True)
    tree_file = models.ImageField(upload_to='alignment_results/', null=True, blank=True)  # 新增字段

    def __str__(self):
        return f'Task {self.id} - {self.get_status_display()}'
