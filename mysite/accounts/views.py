# accounts/views.py

from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from .forms import RegisterForm, SequenceForm
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from .models import Sequence
from .models import AlignmentTask
from .tasks import run_alignment_task
from .forms import AlignmentTaskForm
import xml.etree.ElementTree as ET
from Bio.Blast import NCBIXML
from django.shortcuts import render

def register_view(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('home')
    else:
        form = RegisterForm()
    return render(request, 'accounts/register.html', {'form': form})

def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('home')
    else:
        form = AuthenticationForm()
    return render(request, 'accounts/login.html', {'form': form})

def logout_view(request):
    logout(request)
    return redirect('home')

@login_required
def profile_view(request):
    sequences = Sequence.objects.filter(user=request.user)
    return render(request, 'accounts/profile.html', {'sequences': sequences})
def upload_sequence(request):
    if request.method == 'POST':
        form = SequenceForm(request.POST, request.FILES)
        if form.is_valid():
            sequence = form.save(commit=False)
            sequence.user = request.user
            sequence.save()
            return redirect('profile')
    else:
        form = SequenceForm()
    return render(request, 'accounts/upload_sequence.html', {'form': form})
def create_alignment_task(request):
    if request.method == 'POST':
        form = AlignmentTaskForm(request.POST)
        if form.is_valid():
            alignment_task = form.save(commit=False)
            alignment_task.user = request.user
            alignment_task.save()

            # 调用Celery任务
            task = run_alignment_task.delay(alignment_task.id)
            alignment_task.task_id = task.id
            alignment_task.save()

            return redirect('alignment_task_list')
    else:
        form = AlignmentTaskForm()
        form.fields['sequence'].queryset = Sequence.objects.filter(user=request.user)
    return render(request, 'accounts/create_alignment_task.html', {'form': form})
def alignment_task_list(request):
    tasks = AlignmentTask.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'accounts/alignment_task_list.html', {'tasks': tasks})
def alignment_task_detail(request, task_id):
    task = AlignmentTask.objects.get(id=task_id, user=request.user)
    blast_records = None
    if task.status == 'SUCCESS' and task.result_file:
        result_file_path = task.result_file.path
        with open(result_file_path, 'r') as result_file:
            blast_records = NCBIXML.read(result_file)
    return render(request, 'accounts/alignment_task_detail.html', {'task': task, 'blast_records': blast_records})
def genome_browser(request):
    return render(request, 'genome_browser.html')