from django.contrib import admin
from models import Follow, SeenMilestone, ProfilePictures, Notification, PictureSet, VoucheMilestone, \
	Picture, JournalPost, JournalComment, Pond, PondRequest, PondMembership, PondSpecificProject, SeenProject, \
	LetDownMilestone, ProgressPicture, ProgressPictureSet, SeenProgress, SeenPictureSet, WorkEthicRank, LetDownProject, \
	VoucheProject, ProgressImpressedCount, PondProgressFeed, ShoutOutEmailAndNumber, ProgressVideo, ProgressVideoSet

# Register your models here.

admin.site.register(Follow)
admin.site.register(SeenMilestone)
admin.site.register(ProfilePictures)
admin.site.register(Notification)
admin.site.register(PictureSet)
admin.site.register(VoucheMilestone)
admin.site.register(Picture)
admin.site.register(JournalPost)
admin.site.register(JournalComment)
admin.site.register(Pond)
admin.site.register(PondRequest)
admin.site.register(PondMembership)
admin.site.register(PondSpecificProject)
admin.site.register(SeenProject)
admin.site.register(LetDownMilestone)
admin.site.register(ProgressPicture)
admin.site.register(ProgressPictureSet)
admin.site.register(SeenPictureSet)
admin.site.register(SeenProgress)
admin.site.register(LetDownProject)
admin.site.register(WorkEthicRank)
admin.site.register(VoucheProject)
admin.site.register(ProgressImpressedCount)
admin.site.register(PondProgressFeed)
admin.site.register(ShoutOutEmailAndNumber)
admin.site.register(ProgressVideo)
admin.site.register(ProgressVideoSet)