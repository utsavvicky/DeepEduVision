from django.shortcuts import render, get_object_or_404
from django.views.generic import TemplateView
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect, Http404
from django.contrib.auth.models import User
from .models import Faculty
from review.models import *
from google.cloud import vision
from PIL import Image, ImageFont, ImageDraw
import urllib.request
import io, random, copy
from .sentiment_analysis import *
from .vision_helpers import *

def get_vertices(faces):
	vertices = []
	for face in faces:
		vertices.append(face.fd_bounds.vertices)

	return vertices

def build_faces_border(vertex,dr):
	x1 = vertex[0].x_coordinate
	y1 = vertex[0].y_coordinate
	x2 = vertex[1].x_coordinate
	y2 = vertex[1].y_coordinate

	dr.rectangle([(x1,y1),(x2,y2)],outline='yellow')


def build_faces_border_all(vertices, path):
	im = Image.open("media/{}".format(path))
	dr = ImageDraw.Draw(im)

	for vertex in vertices:
		vertex = (vertex[0],vertex[2])
		build_faces_border(vertex, dr)

	im.save("media/mod{0}".format(path))

def save_uploaded_file(img):
	rndm = random.random()
	with open('media/temp{}.png'.format(rndm), 'wb+') as dest:
		for chunk in img.chunks():
			dest.write(chunk)

	return 'temp{}.png'.format(rndm)

def class_mood(request):
	template_name = 'analysis_upload.html'
	context = {}
	faces = []

	if request.method == 'POST':
		img, uri = '', ''

		if request.FILES:
			img = request.FILES['uploadImage']
			clone_img = copy.deepcopy(img)
			filename = save_uploaded_file(clone_img)
		else:
			uri = request.POST['link']
			rndm = random.random()
			filename = "temp{}.png".format(rndm)
			urllib.request.urlretrieve(uri, filename)


		client = vision.Client()

		if img:
			faces = detect_faces(img)
		else:
			faces = detect_faces_uri(uri)

		vertices = get_vertices(faces)

		build_faces_border_all(vertices, filename)

		context = {
			'faces' : faces,
			'head_count' : len(faces),
			'original_img': 'media/{}'.format(filename),
			'mod_img': 'media/mod{}'.format(filename)
		}

	return render(request, template_name, context)


def profile(request, user_id):
	template_name = '404.html'
	context = {}

	try:
		user = get_object_or_404(User, pk=user_id)
	except Http404:
		return render(request, template_name, context)

	faculty = Faculty.objects.get(user=user)

	is_editable = False
	
	reviews = Review.objects.filter(object_id=faculty.id)

	sentiment_scores = analyze(reviews)

	faculty.positive_reviews = sentiment_scores[1]
	faculty.neutral_reviews = sentiment_scores[2]
	faculty.negative_reviews = sentiment_scores[3]

	faculty.save()	

	if request.user.is_authenticated():
		if user == request.user:
			is_editable = True

	template_name = 'profile.html'
	context = {
		'faculty' : faculty,
		'reviews' : reviews,
		'is_editable' : is_editable
	}

	return render(request, template_name, context)

@login_required(login_url='/auth/login/')
def edit_profile(request, user_id):
	try:
		user = get_object_or_404(User, pk=user_id)
	except Http404:
		return render(request, template_name, context)

	faculty = Faculty.objects.get(user=user)

	if request.method=='POST':
		faculty.first_name = request.POST.get('first_name', faculty.first_name)
		faculty.last_name = request.POST.get('last_name', faculty.last_name)
		faculty.email = request.POST.get('email', faculty.user.email)
		faculty.about_me = request.POST.get('about_me', faculty.about_me)
		faculty.contact = request.POST.get('contact', 0)

		if request.FILES:
			faculty.profile_img = request.FILES.get('profile_img')

		faculty.save()

		return HttpResponseRedirect('/attendance/profiles/{}/'.format(user_id))


	template_name = 'edit_profile.html'
	context = {
		'faculty' : faculty
	}

	return render(request, template_name, context)