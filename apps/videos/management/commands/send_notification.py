from django.core.management.base import BaseCommand
from videos.models import VideoCaptionVersion, TranslationVersion
from django.conf import settings
from datetime import datetime, timedelta
from videos.utils import send_templated_email
from django.contrib.sites.models import Site

class Command(BaseCommand):
    domain = Site.objects.get_current().domain
    
    def handle(self, *args, **kwargs):
        max_save_time = datetime.now() - timedelta(seconds=settings.EDIT_END_THRESHOLD)
        
        qs = VideoCaptionVersion.objects \
            .filter(notification_sent=False) \
            .filter(datetime_started__lte=max_save_time)
        for version in qs:
            version.notification_sent = True
            version.update_changes()  #item is saved in update_changes
            if version.text_change or version.time_change:
                self.send_letter_caption(version)
        
        translation_qs = TranslationVersion.objects \
            .filter(notification_sent=False) \
            .filter(datetime_started__lte=max_save_time)
        for version in translation_qs:
            version.notification_sent = True
            version.update_changes()  #item is saved in update_changes            
            if version.version_no == 0:
                self.send_letter_translation_start(version)
            else:
                if version.text_change or version.time_change:
                    self.send_letter_translation(version)
    
    def _get_users(self, version):
        users = []
        owner = version.language.video.owner
        if not owner == version.user and owner.changes_notification:
            users.append(owner)
        qs = TranslationVersion.objects.filter(language=version.language) \
            .filter(version_no__lt=version.version_no).order_by('-version_no')
        for item in qs:
            user = item.user
            if not user == version.user and not user in users and user.changes_notification:
                users.append(user)
        return users
     
    def send_letter_translation_start(self, translation_version):
        video = translation_version.language.video
        for user in self._get_users(translation_version):
            context = {
                'version': translation_version,
                'domain': self.domain,
                'user': user,
                'language': translation_version.language,
                'video': video
            }
            send_templated_email(user.email, '', 'videos/email_start_notification.html',
                         context, fail_silently=not settings.DEBUG)
            
    def send_letter_translation(self, translation_version):
        qs = TranslationVersion.objects.filter(language=translation_version.language) \
            .filter(version_no__lt=translation_version.version_no).order_by('-version_no')
        context = {
            'version': translation_version,
            'domain': self.domain,
            'translation': True
        }
        users = []
        for item in qs:
            if not translation_version.user == item.user and item.user.changes_notification \
                                                    and not item.user in users:
                users.append(item.user)
                
                second_captions = dict([(c.caption_id, c) for c in item.captions()])
                captions = []
                for caption in translation_version.captions():
                    try:
                        scaption = second_captions[caption.caption_id]
                    except KeyError:
                        scaption = None
                    changed = scaption and not caption.translation_text == scaption.translation_text 
                    data = [caption, scaption, changed]
                    captions.append(data)
                
                context['captions'] = captions        
                context['user'] = item.user
                context['old_version'] = item
                send_templated_email(item.user.email, '', 'videos/email_notification.html',
                             context, fail_silently=not settings.DEBUG)            
            
    def send_letter_caption(self, caption_version):
        qs = VideoCaptionVersion.objects.filter(video=caption_version.video) \
            .filter(version_no__lt=caption_version.version_no).order_by('-version_no')
        context = {
            'version': caption_version,
            'domain': self.domain,
            'translation': False
        }
        users = []
        for item in qs:
            if not caption_version.user == item.user and item.user.changes_notification \
                                                    and not item.user in users:
                users.append(item.user)
                context['user'] = item.user
                context['old_version'] = item
                
                second_captions = dict([(c.caption_id, c) for c in item.captions()])
                captions = []
                for caption in caption_version.captions():
                    try:
                        scaption = second_captions[caption.caption_id]
                    except KeyError:
                        scaption = None
                        changed = True
                    else:
                        changed = not caption.caption_text == scaption.caption_text
                    data = [caption, scaption, changed]
                    captions.append(data)
                context['captions'] = captions
                        
                send_templated_email(item.user.email, '', 'videos/email_notification.html',
                             context, fail_silently=not settings.DEBUG)