# Create your views here.
import os, json,  time
from random import shuffle
from django.http import HttpResponse
from django.conf import settings
from django.core import serializers

from apps.teams.models import Team, TeamVideo
from apps.videos.models import Video, VideoUrl, SubtitleLanguage, SubtitleVersion, Subtitle
from videos.types import video_type_registrar
from django.contrib.admin.views.decorators import staff_member_required
from apps.auth.models import  CustomUser
from django.db import transaction


import logging
logger = logging.getLogger("test-fixture-loading")

from utils.decorators import never_in_prod

def _get_fixture_path(model_name):
    return os.path.join(settings.PROJECT_ROOT, "apps", "testhelpers", "fixtures", "%s-fixtures.json" % model_name)

def _get_fixture_file(model_name):
    return file(_get_fixture_path(model_name))
    

def _add_subtitles(sub_lang, num_subs, translated_from=None):
    version = SubtitleVersion(language=sub_lang, note="Automagically-created")
    version.save()
    for i in xrange(0, num_subs):
        subtitle = Subtitle(version=version,
                            subtitle_id="%s" % i,
                            subtitle_order=i,
             subtitle_text = "Sub %s for lang (%s)" % (i, sub_lang.language))
        if not translated_from:
             subtitle.start_time=i * 1.0
             subtitle.end_time =i + 0.8
             
        else:
            subtitle.subtitle_text += " translated from (%s)" % (translated_from)
        subtitle.save()
    return version    

def _copy_subtitles(fromlang, tolang, maxout=None):
    version = SubtitleVersion(language=tolang, note="Automagically-copied")
    version.save()
    i = 0
    for x in fromlang.version().subtitle_set.all():
        s = x.duplicate_for(version=version, draft=None)
        s.save()
        i += 1
        if maxout and maxout < i:
            break
    
def _add_lang_to_video(video, props,  translated_from=None):

    sub_lang = SubtitleLanguage(
        video=video,
        is_original = props.get('is_original', False),
        is_complete = props.get('is_complete', False),
        language = props.get('code'),
        has_version=True,
        had_version=True,
        is_forked=True,
    )
    sub_lang.save()
    num_subs = props.get("num_subs", 0)

    if not translated_from:
        _add_subtitles(sub_lang, num_subs)

    if translated_from:
        sub_lang.is_original = False
        sub_lang.is_forked = False
        sub_lang.standard_language = translated_from
        sub_lang.save()
        _copy_subtitles(translated_from ,sub_lang,  num_subs)

    for translation_prop in props.get("translations", []):
        _add_lang_to_video(video, translation_prop, translated_from=sub_lang)


    sub_lang.update_percent_done()
    print 'adding lang ', sub_lang
    sub_lang.save()
    return sub_lang    
            
def _add_langs_to_video(video, props):
    for prop in props:
        _add_lang_to_video(video, prop)
                            
    
def _create_videos(video_data, users):
    videos = []
    
    
    for x in video_data:
        shuffle(users)
        video = Video(title=x['title'])
        video.save()
        if len(users) > 0:
            video.user = users[0]
        url = x['url'] + "&blah=%s" % time.time()
        vt =  video_type_registrar.video_type_for_url(url)
        if vt is None:
            continue
        video_url, created  = VideoUrl.objects.get_or_create(video=video, type=vt.abbreviation, url=url)
        video_url.original = True
        video_url.primary = True
        video_url.video = video
        video_url.save()
         # now we loop over languages:
        _add_langs_to_video(video, x['langs'])
        if len(x['langs']) > 0:
            video.is_subtitled = True
        video.save()    
        videos.append(video)
       
   
    return videos

def _hydrate_users(users_data):
    users = []
    for x in serializers.deserialize('json', users_data):
        x.save()
        users.append(x.object)
    return users         
    
# create 30 videos
def _create_team_videos(team, videos, users):
    
    for video in videos:
        shuffle(users)
        team_video = TeamVideo(team=team, video=video)
        member, created = CustomUser.objects.get_or_create(user_ptr=users[0])
        team_video.added_by = member
        team_video.save()

@transaction.commit_on_success        
def _do_it(video_data_url=None):
    team, created = Team.objects.get_or_create(slug="unisubs-test-team")
    team.name = "Unisubs test"
    team.save()
    
    team.videos.all().delete()
    users = _hydrate_users(_get_fixture_file("users").read())
    if video_data_url:
        import httplib2
        h = httplib2.Http("/tmp/.httplibcache")
        resp, content = h.request("http://www.emptywhite.com/misc/videos-fixtures.json")
        video_data  = json.loads(content)
    else:
        video_data  = json.load(_get_fixture_file("videos"))

    videos = _create_videos(video_data, [])
    _create_team_videos(team, videos, users)
    
@staff_member_required
@never_in_prod
def load_team_fixtures(request ):
    load_from = request.GET.get("load_from", None)
    videos = _do_it(load_from)
    return HttpResponse( "created %s videos" % len(videos))
    
    
        
