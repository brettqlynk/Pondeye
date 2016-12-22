from django.shortcuts import render
from django.views.generic import View
from forms import social_forms
from models import (Notification, Follow, PictureSet, Picture, VoucheMilestone, SeenMilestone,
                    JournalPost, JournalComment, SeenProject, ProfilePictures, Pond)
from ..tasks.models import TikedgeUser, UserProject, Milestone
from django.http import HttpResponseRedirect, HttpResponse
from django.utils.decorators import method_decorator
from django.core.urlresolvers import reverse
from django.core.exceptions import ObjectDoesNotExist
import modules
from ..tasks import modules as task_modules
from friendship.models import Friend, FriendshipRequest
from tasks_feed import NotificationFeed
from friendship.exceptions import AlreadyExistsError, AlreadyFriendsError
from django.core.exceptions import ValidationError
import global_variables
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
import json
from django.contrib import messages
from django.db.models import Q
from search_module import find_everything
from braces.views import LoginRequiredMixin


class CSRFExemptView(View):
    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super(CSRFExemptView, self).dispatch(*args, **kwargs)


class CSRFEnsureCookiesView(View):
    @method_decorator(ensure_csrf_cookie)
    def dispatch(self, *args, **kwargs):
        return super(CSRFEnsureCookiesView, self).dispatch(*args, **kwargs)


class JournalEntriesView(LoginRequiredMixin, View):

    def get(self, request):
        tkdge = TikedgeUser.objects.get(user=request.user)
        list_of_journal_feeds = modules.get_user_journal_feed(tkdge)
        return render(request, 'social/journal.html', {'list_of_journal_feeds':list_of_journal_feeds})

    def post(self, request):
        comment = request.POST.get("comment")
        response = {}
        if comment is not "":
            journal_id = request.POST.get("journal_id")
            journal = JournalPost.objects.get(id=int(journal_id))
            new_comment = JournalComment(journal_post=journal, comment=comment)
            new_comment.save()
            response["status"] = True
        else:
            response["status"] = True
        return HttpResponse(json.dumps(response), status=201)


class JournalCommentListView(LoginRequiredMixin, View):

    def get(self, request, slug):
        journal_post = JournalPost.objects.get(slug=slug)
        comments = journal_post.journalcomment_set.all().filter(is_deleted=False)
        print "comment ", comments
        return render(request, 'social/journal_thoughts.html', {'journal_comments':comments,
                                                                'journal_post':journal_post
                                                                })


class MilestoneView(LoginRequiredMixin, View):

    def get(self, request, slug):
        milestone = Milestone.objects.get(slug=slug)
        project = milestone.project
        project_name = project.name_of_project
        feed_id = milestone.id
        modules.increment_milestone_view(request.user, milestone)
        try:
            vouch_count = VoucheMilestone.objects.get(tasks=milestone).users.count()
        except ObjectDoesNotExist:
            vouch_count = 0
        try:
            seen_count = SeenMilestone.objects.get(tasks=milestone).users.count()
            print "seen count ", seen_count
            print "seen count ", seen_count
        except ObjectDoesNotExist:
            seen_count = 0
        project_completed = task_modules.time_has_past(project.length_of_project)
        user_first_name = milestone.user.user.first_name
        pic_list = milestone.pictureset_set.all().filter(~Q(after_picture=None))
        percentage = modules.get_milestone_percentage(milestone)
        return render(request, 'social/milestone_view.html', {
            'milestone':milestone, 'project_name':project_name,
            'feed_id':feed_id, 'vouch_count':vouch_count, 'seen_count':seen_count,
            'project_completed':project_completed, 'user_first_name': user_first_name,
            'project_slug':project.slug, 'pic_list': pic_list,
            'percentage':percentage
        })


class ProjectView(LoginRequiredMixin, View):

    def get(self, request, slug):
        project = UserProject.objects.get(slug=slug)
        project_name = project.name_of_project
        motivations = project.tags.all()
        print "motivations ", motivations
        modules.increment_project_view(request.user, project)
        milestones = modules.milestone_tuple(project)
        try:
            seen_count = SeenProject.objects.get(tasks=project).users.count()
        except ObjectDoesNotExist:
            seen_count = 0
        try:
            follows = Follow.objects.get(tasks=project).users.count()
        except ObjectDoesNotExist:
            follows = 0
        return render(request, 'social/individual_project.html', {'project_name':project_name,
                                                                  'motivations':motivations,
                                                                   'milestones':milestones,
                                                                    'project_slug':slug,
                                                                    'seen_count':seen_count,
                                                                    'interest_count':follows,
                                                                    'project':project,
                                                                  })


class PictureUploadView(LoginRequiredMixin, View):

    def get(self, request):
        existing_milestones = task_modules.get_user_milestones(request.user)
        user_picture_form = social_forms.PictureUploadForm()

        return render(request, 'social/upload_picture.html', {'user_picture_form':user_picture_form,
                                                              'existing_milestones':existing_milestones})

    def post(self, request):
        user_picture_form = social_forms.PictureUploadForm(request.POST, request.FILES)

        if user_picture_form.is_valid() and 'picture' in request.POST:
            tkduser = TikedgeUser.objects.get(user=request.user)
            picture_file = request.FILES.get('picture', False)
            if not modules.file_is_picture(picture_file):
                messages.error(request, 'Hey visual must be either jpg, jpeg or png file!')
                existing_milestones = task_modules.get_user_milestones(request.user)
                return render(request, 'social/upload_picture.html', {'user_picture_form':user_picture_form,
                                                              'existing_milestones':existing_milestones})
            milestone_name = request.POST.get('milestone_name')
            milestone = Milestone.objects.get(id=milestone_name)
            if request.POST.get("type_of_picture") == global_variables.BEFORE_PICTURE:
                is_before = True
                # check that user is not creating concurrent before for current milestone
                try:
                    PictureSet.objects.get(milestone=milestone, after_picture=None)
                    messages.error(request, 'Sorry we first need an after picture for %s milestone' % milestone.name_of_milestone)
                    existing_milestones = task_modules.get_user_milestones(request.user)
                    return render(request, 'social/upload_picture.html', {'user_picture_form':user_picture_form,
                                                                          'existing_milestones':existing_milestones})
                except ObjectDoesNotExist:
                    pass
            else:
                is_before = False
            picture_file.file = modules.resize_image(picture_file)
            picture_mod = Picture(image_name=picture_file.name,
                                   milestone_pics=picture_file, tikedge_user=tkduser, is_before=is_before)
            picture_mod.save()
            if is_before:
                pic_set = PictureSet(before_picture=picture_mod, milestone=milestone, tikedge_user=tkduser)
                pic_set.save()
                day_entry = tkduser.journalpost_set.all().count()
                new_journal_entry = JournalPost(
                                                entry_blurb=modules.get_journal_message(global_variables.BEFORE_PICTURE,
                                                                                        milestone=milestone.blurb),
                                                                                        day_entry=day_entry + 1,
                                                                                        event_type=global_variables.BEFORE_PICTURE,
                                                                                        is_picture_set=True,
                                                                                        picture_set_entry=pic_set,
                                                                                        user=tkduser
                                                                                        )
                new_journal_entry.save()
                messages.success(request, 'Cool! the before visual entry added to %s milestone' % milestone.blurb)
            else:
                try:
                    pic_set = PictureSet.objects.get(milestone=milestone, after_picture=None, tikedge_user=tkduser)
                    pic_set.after_picture = picture_mod
                    pic_set.save()
                    day_entry = tkduser.journalpost_set.all().count()
                    new_journal_entry = JournalPost(
                                                entry_blurb=modules.get_journal_message(global_variables.AFTER_PICTURE,
                                                                                        milestone=milestone.blurb),
                                                day_entry=day_entry + 1,
                                                event_type=global_variables.AFTER_PICTURE,
                                                is_picture_set=True,
                                                 picture_set_entry=pic_set
                                                )
                    new_journal_entry.save()
                    messages.success(request, 'Great Job! the after visual entry added to %s milestone' % milestone.blurb)
                except ObjectDoesNotExist:
                    existing_milestones = task_modules.get_user_milestones(request.user)
                    messages.error(request, 'Hey we need a before visual entry before an after visual entry. This wow the crowd!')
                    return render(request, 'social/upload_picture.html', {'user_picture_form':user_picture_form,
                                                              'existing_milestones':existing_milestones})
            return HttpResponseRedirect(reverse('tasks:home'))
        existing_milestones = task_modules.get_user_milestones(request.user)
        messages.error(request, 'Oops, I think you forgot to upload a valid picture file')
        return render(request, 'social/upload_picture.html', {'user_picture_form':user_picture_form,
                                                              'existing_milestones':existing_milestones})


class HomeActivityView(LoginRequiredMixin, View):

    def get(self, request):
        activities = modules.get_user_activities(request.user)
        return render(request, 'social/home_activity_view.html', {'activities':activities})


class TodoFeed(LoginRequiredMixin, View):

    def get(self, request):
        all_feeds = modules.get_users_feed(request.user)
        notification = Notification.objects.filter(user=request.user)
        notification = NotificationFeed(notifications=notification, user=request.user)
        unread_list = notification.get_unread_notification()
        tikedge_user = task_modules.get_tikedge_user(request.user)
        try:
            has_prof_pic = ProfilePictures.objects.get(tikedge_user=tikedge_user)
            user_pic_url = has_prof_pic.profile_pics.url
        except ObjectDoesNotExist:
            user_pic_url = None
        return render(request, 'social/news_feed.html', {'all_feeds':all_feeds,
                                                         'notifications':unread_list,
                                                         'user_pic_url': user_pic_url,
                                                         'user':request.user
                                                         })


class SendFriendRequestView(View):

    def get(self, request):
        pass

    def post(self, request):
        user_id = request.POST.get("user_id")
        other_user = TikedgeUser.objects.get(id=int(user_id))
        print other_user.user.username, other_user.user.first_name, other_user.user.last_name
        message = "Hi %s %s username: %s would like to add you to his pond" % (request.user.first_name,
                  request.user.last_name, request.user.username)
        try:
            Friend.objects.add_friend(request.user, other_user.user, message=message)
            friend_request = FriendshipRequest.objects.get(pk=other_user.user.pk)
            notification = Notification(friend_request=friend_request, user=other_user.user,
                                        type_of_notification=global_variables.FRIEND_REQUEST)
            notification.save()
        except (AlreadyFriendsError, AlreadyExistsError, ValidationError):
            pass
        return HttpResponse('')


class AcceptFriendRequestView(View):

    def get(self, request):
        pass

    def post(self, request):
        request_id = request.POST.get("pk")
        print "Request ID %s", request_id
        try:
            friend_request = FriendshipRequest.objects.get(pk=int(request_id))
            friend_request.accept()
            # create notification
        except (AlreadyFriendsError, AlreadyExistsError, ValidationError):
            pass
        return HttpResponse('')


class RejectFriendRequestView(View):

    def get(self, request):
        pass

    def post(self, request):
        request_id = request.POST.get("pk")
        print "Request ID %s", request_id
        friend_request = FriendshipRequest.objects.get(pk=int(request_id))
        friend_request.reject()

        return HttpResponse('')


class FriendRequestView(View):

    def get(self, request):
        friend_request = Friend.objects.unread_requests(user=request.user)
        return render(request, 'social/friend_request.html', {'friend_request':friend_request})


class CreateVouch(View):

    def post(self, request, *args, **kwargs):
        response = {}
        milestone_id = request.POST.get("mil_id")
        milestone = Milestone.objects.get(id=int(milestone_id))
        user = TikedgeUser.objects.get(user=request.user)
        try:
            vouch_obj = VoucheMilestone.objects.get(tasks=milestone)
        except ObjectDoesNotExist:
            vouch_obj = VoucheMilestone(tasks=milestone)
            vouch_obj.save()
        if user not in vouch_obj.users.all():
            vouch_obj.users.add(user)
            vouch_obj.save()
            try:
                view = SeenMilestone.objects.get(tasks=milestone)
            except ObjectDoesNotExist:
                view = SeenMilestone(tasks=milestone)
                view.save()
            if user not in view.users.all():
                view.users.add(user)
                view.save()
            response["status"] = True
        else:
            response["status"] = False
        print "Tried to print vouch!!!!!!\n"
        return HttpResponse(json.dumps(response), status=201)


class CreateFollowView(CSRFExemptView):

    def get(self, request, *args, **kwargs):
        return HttpResponse('')

    def post(self, request, *args, **kwargs):
        response = {}
        proj_id = request.POST.get("proj_id")
        project = UserProject.objects.get(id=int(proj_id))
        tikedge_user = TikedgeUser.objects.get(user=request.user)
        try:
            follow_obj = Follow.objects.get(tasks=project)
        except ObjectDoesNotExist:
            follow_obj = Follow(tasks=project)
            follow_obj.save()
        if not tikedge_user in follow_obj.users.all():
            response["status"] = True
            follow_obj.users.add(tikedge_user)
            follow_obj.save()
        else:
            response["status"] = False
        response["count"] = follow_obj.users.all().count()
        return HttpResponse(json.dumps(response), status=201)


class TagSearchView(View):
    def get(self, request, word):
        return render(request, 'social/tag_search_results.html')


class NotificationsViews(LoginRequiredMixin, View):

    def get(self, request):
        return render(request, 'social/notification_view.html')


class NewFriendNotificationsView(LoginRequiredMixin, View):

    def get(self, request):
        ponders = modules.get_pond(request.user)
        return render(request, 'social/new_ponders.html', {'ponders':ponders})


class ProjectNotificationsView(LoginRequiredMixin, View):

    def get(self, request):
        tikegde_user = TikedgeUser.objects.get(user=request.user)
        all_project = tikegde_user.userproject_set.all()
        interest_feed = modules.get_interest_notification(all_project)
        return render(request, 'social/project_interest_view.html', {'interest_feed':interest_feed})


class LetDownsNotificationsView(LoginRequiredMixin, View):
    def get(self, request):
        let_down_results = modules.get_let_down_notifications(request.user)
        return render(request, 'social/let_down_view.html', {'let_down_results':let_down_results})


class VouchedNotificationsView(LoginRequiredMixin, View):

    def get(self, request):
        mil_down_results = modules.get_milestone_vouch_notifications(request.user)
        return render(request, 'social/milestone_vouches.html', {'mil_down_results':mil_down_results})


class SearchResultsView(LoginRequiredMixin, View):

    def get(self, request):
        query_word = request.GET["query_word"]
        results = find_everything(request.user, query_word)
        return render(request, 'social/search_results.html', {'results':results})


class PondView(LoginRequiredMixin, View):
    def get(self, request):
        ponds = modules.get_pond(request.user)
        return render('social/pond.html', {'ponds':ponds})


class AddToPond(LoginRequiredMixin, View):

    def post(self, request):
        data = {}
        pond_id = request.POST.get("pond_id")
        pond = Pond.objects.get(id=int(pond_id))
        user_id = request.POST.get("user_id")
        other_user = TikedgeUser.objects.get(id=int(user_id))
        pond.add(other_user)
        pond.save()
        try:
            notification = Notification(pond=pond, user=other_user.user,
                                        type_of_notification=global_variables.ADD_TO_POND)
            notification.save()
            data['status'] = True
        except ():
            data['status'] = False
            pass
        return HttpResponse(json.dumps(data))


class PondRequest(LoginRequiredMixin, View):

    def post(self, request):
        data = {}
        pond_id = request.POST.get("pond_id")
        pond = Pond.objects.get(id=int(pond_id))
        modules.send_pond_request(pond, request.user)
        try:
            notification = Notification(pond=pond, user=request.user,
                                        type_of_notification=global_variables.POND_REQUEST)
            notification.save()
            data['status'] = True
        except ():
            data['status'] = False
            pass
        return HttpResponse(json.dumps(data))

















