from collections import Counter

from django.conf import settings
from django.contrib.staticfiles.templatetags.staticfiles import static
from django.db import models
from django.db.models import Q

from accounts.models import RewardHistory

import datetime


class LikeMixinModel(models.Model):
    liker_set = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='liked_%(class)s_set',
        blank=True,
    )

    class Meta:
        abstract = True

    def count_liked(self):
        return self.liker_set.count()

    def is_liked_by(self, user):
        return self.liker_set.filter(pk=user.pk).exists()

    def toggle_like(self, user):
        liked_before = self.is_liked_by(user)
        if liked_before:
            self.liker_set.remove(user)
        else:
            self.liker_set.add(user)
        return not liked_before


class ThankMixinModel(models.Model):
    thanked_set = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='liked_%(class)s_set',
        blank=True,
    )

    class Meta:
        abstract = True

    def count_thanked(self):
        return self.thanked_set.count()

    def is_thanked_by(self, user):
        return self.thanked_set.filter(pk=user.pk).exists()

    def say_thank(self, user):
        thanked_before = self.is_thanked_by(user)
        if thanked_before:
            return thanked_before
        else:
            self.thanked_set.add(user)
            reward_history = RewardHistory.objects.create(
                user=self.ticket.user,
                reason='내 리뷰에 대한 {}님의 땡큐'.format(user),
                amount=0.5,
            )
            reward_history.status = 'complete'
            reward_history.save()
            return not thanked_before


class Category(models.Model):
    name = models.CharField(max_length=20)
    en_name = models.CharField(max_length=30)
    main_color = models.CharField(max_length=10, blank=True, null=True)
    color = models.CharField(max_length=10, blank=True, null=True)

    def __str__(self):
        return self.name


class Division(models.Model):
    category = models.ForeignKey(Category)
    name = models.CharField(max_length=20)
    en_name = models.CharField(max_length=30)
    main_color = models.CharField(max_length=10, blank=True, null=True)
    color = models.CharField(max_length=10, blank=True, null=True)

    def __str__(self):
        division_name = self.category.name + '-' + self.name
        return division_name


# ### 장소/좌석 관련 모델 ### #

class Place(models.Model):

    REGION_CHOICES = (
        ('Seoul', '서울'),
        ('Incheon', '인천'),
        ('Gyeonggi', '경기'),
        ('Busan', '부산'),
        ('Daejeon', '대전'),
        ('Daegu', '대구'),
        ('Gwangju', '광주'),
        ('Ulsan', '울산'),
        ('Gangwon', '강원'),
        ('ChungcheongN', '충북'),
        ('ChungcheongS', '충남'),
        ('GyeongsangN', '경북'),
        ('GyeongsangS', '경남'),
        ('JeonlaN', '전북'),
        ('JeonlaS', '전남'),
        ('Jeju', '제주'),
    )

    name = models.CharField(max_length=20)
    en_name = models.CharField(max_length=30)
    bg = models.ImageField(upload_to='Place/')
    division_set = models.ManyToManyField(Division)
    region = models.CharField(
        max_length=10,
        choices=REGION_CHOICES,
    )
    address = models.CharField(max_length=100)
    lat_lon = models.CharField(max_length=20)
    contact = models.CharField(max_length=20, blank=True, null=True)
    website = models.CharField(max_length=50, blank=True, null=True)
    explain = models.TextField(blank=True, null=True)

    # 날씨 관련 속성 --> 일단은 보류

    def __str__(self):
        return self.name

    def split_explain(self):
        return self.explain.split('&')


class Space(LikeMixinModel):
    place = models.ForeignKey(Place)
    name = models.CharField(max_length=20)
    en_name = models.CharField(max_length=30)
    division_set = models.ManyToManyField(Division)

    def __str__(self):
        space_name = self.place.name + '-' + self.name
        return space_name

    def get_space_view_count(self):
        return SeatImg.objects.filter(seat__block__section__space=self).count()

    def get_space_review(self):
        return SeatReview.objects.filter(seat__block__section__space=self)

    def get_space_view_star(self):
        avg_dict = SeatReview.objects.filter(seat__block__section__space=self).aggregate(models.Avg('view_star'))

        if avg_dict['view_star__avg'] is None:
            return 0.0
        else:
            return avg_dict['view_star__avg']

    def get_view_star_num(self):
        star_num_list = []
        for i in range(1, 6):
            star_num_list.append(SeatReview.objects.filter(seat__block__section__space=self, view_star=i).count())
        return star_num_list[::-1]

    def get_space_real_star(self):
        avg_dict = SeatReview.objects.filter(seat__block__section__space=self).aggregate(models.Avg('real_star'))

        if avg_dict['real_star__avg'] is None:
            return 0.0
        else:
            return avg_dict['real_star__avg']

    def get_real_star_num(self):
        star_num_list = []
        for i in range(1, 6):
            star_num_list.append(SeatReview.objects.filter(seat__block__section__space=self, real_star=i).count())
        return star_num_list[::-1]

    def get_close_series(self):
        now = datetime.datetime.now()

        if Series.objects.filter(Q(start__lte=now, end__gte=now, space=self)).exists():
            series = Series.objects.get(Q(start__lte=now, end__gte=now, space=self))
        elif Series.objects.filter(start__gte=now, space=self).exists():
            series = Series.objects.filter(start__gte=now, space=self).order_by('start').first()
        else:
            series = Series.objects.filter(end__lte=now, space=self).order_by('-end').first()

        return series


class Section(models.Model):
    space = models.ForeignKey(Space)
    name = models.CharField(max_length=20)

    def __str__(self):
        section_name = self.space.name + '-' + self.name
        return section_name


class Block(models.Model):
    section = models.ForeignKey(Section)
    name = models.CharField(max_length=20)
    coordinate = models.CharField(max_length=120)

    def __str__(self):
        block_name = self.section.space.name + '-' + self.name
        return block_name

    def get_block_main_level(self):
        series = self.section.space.get_close_series()
        all_seat = Seat.objects.none()

        for level in series.seatlevel_set.all():
            all_seat |= level.seat_set.all()

        level_list = all_seat.filter(block=self).values_list('level__pk', flat=True)

        if len(level_list) == 0:
            main_level = SeatLevel.objects.filter(name='미사용').first()

        else:
            main_level_pk = Counter(level_list).most_common(1)[0][0]
            main_level = SeatLevel.objects.get(pk=main_level_pk)

        return main_level

    def get_text_x_coordinate(self):
        all_coor = self.coordinate.split(' ')
        x_coor = []

        for coor in all_coor:
            x_coor.append(float(coor.split(',')[0]))

        return sum(x_coor) / float(len(x_coor))

    def get_text_y_coordinate(self):
        all_coor = self.coordinate.split(' ')
        y_coor = []

        for coor in all_coor:
            y_coor.append(float(coor.split(',')[1]))

        return sum(y_coor) / float(len(y_coor))

    def get_block_view(self):
        return SeatImg.objects.filter(seat__block=self)

    def get_block_review(self):
        return SeatReview.objects.filter(seat__block=self)

    def get_block_view_star(self):
        avg_dict = SeatReview.objects.filter(seat__block=self).aggregate(models.Avg('view_star'))

        if avg_dict['view_star__avg'] is None:
            return 0.0
        else:
            return avg_dict['view_star__avg']

    def get_view_star_num(self):
        star_num_list = []
        for i in range(1, 6):
            star_num_list.append(SeatReview.objects.filter(seat__block=self, view_star=i).count())
        return star_num_list[::-1]

    def get_block_real_star(self):
        avg_dict = SeatReview.objects.filter(seat__block=self).aggregate(models.Avg('real_star'))

        if avg_dict['real_star__avg'] is None:
            return 0.0
        else:
            return avg_dict['real_star__avg']

    def get_real_star_num(self):
        star_num_list = []
        for i in range(1, 6):
            star_num_list.append(SeatReview.objects.filter(seat__block=self, real_star=i).count())
        return star_num_list[::-1]

    def get_cavas_viewbox(self):
        max_col = Seat.objects.filter(block=self).aggregate(models.Max('col'))
        max_x = max_col['col__max'] * 24
        x_size = max(max_x, 696)-8

        max_row = Seat.objects.filter(block=self).aggregate(models.Max('row'))
        max_y = max_row['row__max'] * 24
        y_size = max(max_y, 704)

        viewbox_size = "0 0 {} {}".format(x_size, y_size)

        return viewbox_size


class SeatLevel(models.Model):
    space = models.ForeignKey(Space)
    name = models.CharField(max_length=20)
    explain = models.CharField(max_length=200, blank=True, null=True)
    note = models.CharField(max_length=100, blank=True, null=True)  # 어드민용
    price = models.PositiveIntegerField(default=0)
    color = models.CharField(max_length=10)
    hover_color = models.CharField(max_length=10, blank=True, null=True)

    def __str__(self):
        level_name = self.space.name + '-' + self.name
        return level_name

    class Meta:
        ordering = ('pk', )


class Seat(models.Model):
    # space = models.ForeignKey(Space)
    block = models.ForeignKey(Block)
    level = models.ForeignKey(SeatLevel)
    name = models.CharField(max_length=20)
    row_real = models.CharField(max_length=20)

    # 왼쪽/위 모서리 기준
    row = models.PositiveSmallIntegerField(default=0)
    col = models.PositiveSmallIntegerField(default=0)
    width = models.PositiveSmallIntegerField(default=1)
    height = models.PositiveSmallIntegerField(default=1)

    def __str__(self):
        seat_name = self.row_real + '-' + self.name
        return seat_name

    def get_coordinate(self):
        up_left_x = 24*(self.col-1)
        up_left_y = 24*(self.row-1)

        coordinate = str(up_left_x) + ',' + str(up_left_y) + ' ' + str(up_left_x+(16*self.width)+(8*(self.width-1))) + ',' + str(up_left_y) + ' ' + str(up_left_x+(16*self.width)+(8*(self.width-1))) + ',' + str(up_left_y+(16*self.height)+(8*(self.height-1))) + ' ' + str(up_left_x) + ',' + str(up_left_y+(16*self.height)+(8*(self.height-1)))
        return coordinate

    def get_seat_view(self):
        return SeatImg.objects.filter(seat=self)

    def get_seat_review(self):
        return SeatReview.objects.filter(seat=self)

    def get_seat_view_star(self):
        avg_dict = SeatReview.objects.filter(seat=self).aggregate(models.Avg('view_star'))

        if avg_dict['view_star__avg'] is None:
            return 0.0
        else:
            return avg_dict['view_star__avg']

    def get_space_real_star(self):
        avg_dict = SeatReview.objects.filter(seat__block__section__space=self).aggregate(models.Avg('real_star'))

        if avg_dict['real_star__avg'] is None:
            return 0.0
        else:
            return avg_dict['real_star__avg']

    class Meta:
        ordering = ('row', 'name')


def seat_img_name(instance, filename):
    return '/'.join(['Seat/img', instance.seat.block.section.space.place.name, instance.seat.block.section.space.name, instance.seat.block.section.name, instance.seat.block.name, instance.seat.name, filename])


class SeatImg(models.Model):

    ZOOM_CHOICES = (
        ('normalize', '가이드준수'),
        ('nozoom', 'zoom안함'),
        ('none', '해당사항없음'),
    )

    seat = models.ForeignKey(
        Seat,
        related_name='image_set',
        blank=True,
        null=True,
    )
    user = models.ForeignKey(settings.AUTH_USER_MODEL)
    history = models.OneToOneField(RewardHistory, blank=True, null=True)
    review = models.ForeignKey('SeatReview', blank=True, null=True)  # 좀 고민됨
    img = models.ImageField(upload_to=seat_img_name)

    status = models.CharField(
        max_length=10,
        choices=ZOOM_CHOICES,
        default='none',
    )  # no zoom이면 노줌 뱃지 / # normalize이면 가이드준수 뱃지

    badge_set = models.ManyToManyField(
        'SeatImgBadge',
        blank=True,
    )  # 등록시 자동지급

    is_confirmed = models.BooleanField(default=False)  # True이면 공개

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.is_confirmed:
            super().save(*args, **kwargs)
            if self.history:
                self.history.status = 'complete'
                self.history.save()

    def delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)
        if self.history:
            self.history.delete()

    class Meta:
        ordering = ('pk', )


class SeatImgBadge(models.Model):
    name = models.CharField(max_length=10)
    color = models.CharField(max_length=10)

    def __str__(self):
        return self.name


class Structure(models.Model):
    # space = models.ForeignKey(Space)
    block = models.ForeignKey(Block)
    name = models.CharField(max_length=20)

    # 왼쪽/위 모서리 기준
    row = models.PositiveSmallIntegerField(default=0)
    col = models.PositiveSmallIntegerField(default=0)
    width = models.PositiveSmallIntegerField(default=1)
    height = models.PositiveSmallIntegerField(default=1)

    def __str__(self):
        structure_name = self.block.name + '-' + self.name
        return structure_name

    def get_coordinate(self):
        up_left_x = 24*(self.col-1)
        up_left_y = 24*(self.row-1)

        coordinate = str(up_left_x) + ',' + str(up_left_y) + ' ' + str(up_left_x+(16*self.width)+(8*(self.width-1))) + ',' + str(up_left_y) + ' ' + str(up_left_x+(16*self.width)+(8*(self.width-1))) + ',' + str(up_left_y+(16*self.height)+(8*(self.height-1))) + ' ' + str(up_left_x) + ',' + str(up_left_y+(16*self.height)+(8*(self.height-1)))
        return coordinate


# ### 이벤트/공연/경기 관련 모델 ### #

class Series(LikeMixinModel):
    division = models.ForeignKey(Division)
    name = models.CharField(max_length=20)
    en_name = models.CharField(max_length=100)
    start = models.DateField()
    end = models.DateField()
    space = models.ForeignKey(Space)
    seatlevel_set = models.ManyToManyField(SeatLevel)

    intro_title = models.CharField(max_length=100)
    intro_content = models.TextField(blank=True, null=True)
    announce = models.TextField(blank=True, null=True)
    appear_link = models.URLField(blank=True, null=True)

    def __str__(self):
        return self.name

    def get_series_review(self):
        return EventReview.objects.filter(event__series=self)

    def get_series_star(self):
        avg_dict = EventReview.objects.filter(event__series=self).aggregate(models.Avg('total_star'))

        if avg_dict['total_star__avg'] is None:
            return 0.0
        else:
            return avg_dict['total_star__avg']

    def get_star_num(self):
        star_num_list = []
        for i in range(1, 6):
            star_num_list.append(EventReview.objects.filter(event__series=self, total_star=i).count())

        return star_num_list[::-1]

    def get_series_appear(self):
        events = self.event_set.values_list('pk', flat=True)
        appears = Appear.objects.none()
        for event in events:
            appears |= Event.objects.get(pk=event).appear_set.all()

        return appears.distinct()

    # TODO:
    def get_emotion_set(self):
        series_event_pk = self.event_set.values_list('pk', flat=True)
        all_emotions = Emotion.objects.all()
        result = dict()

        for emotion in all_emotions:
            if emotion.eventreview_set.exists():
                emotion_event_pk = emotion.eventreview_set.values_list('event__pk', flat=True)
                emotion_dict = Counter(emotion_event_pk)

                for pk in series_event_pk:
                    if pk in emotion_dict.keys():
                        result[emotion] = result.get(emotion, 0) + emotion_dict[pk]

        return sorted(result.items(), key=lambda kv: kv[1], reverse=True)[:10]

    def split_intro_content(self):
        return self.intro_content.split('&')

    def split_announce(self):
        return self.announce.split('&')


class SeriesImg(models.Model):
    series = models.ForeignKey(
        Series,
        related_name='image_set',
        blank=True,
        null=True,
    )
    img = models.ImageField(upload_to='Series/', blank=True, null=True)


class Event(models.Model):
    series = models.ForeignKey(Series)
    name = models.CharField(max_length=20, blank=True, null=True)
    start = models.DateTimeField()
    end = models.DateTimeField(blank=True, null=True)
    appear_set = models.ManyToManyField('Appear')

    def __str__(self):
        event_name = self.series.name + '-' + str(self.start.strftime("%Y.%m.%d."))
        return event_name

    def get_event_star(self):
        avg_dict = self.eventreview_set.all().aggregate(models.Avg('total_star'))
        return avg_dict['total_star__avg']


class Appear(LikeMixinModel):
    name = models.CharField(max_length=20)
    division_set = models.ManyToManyField(Division)
    is_team = models.BooleanField(default=False)
    role = models.CharField(max_length=20, blank=True, null=True)
    img = models.ImageField(upload_to='Appear/', blank=True, null=True)

    def __str__(self):
        return self.name


# ### 티켓/리뷰 관련 모델 ### #
# TODO : 블럭/좌석/이벤트별 뷰/리뷰 갯수 뽑아올 수 있는 함수

class Ticket(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        ticket_name = self.user.username + ' -' + str(self.pk)
        return ticket_name

    def is_complete(self):
        if self.event_review.content and self.seat_review.content:
            return True
        else:
            return False


class TicketImg(models.Model):
    ticket = models.ForeignKey(
        Ticket,
        related_name='image_set',
        blank=True,
        null=True,
    )
    img = models.ImageField(upload_to='TicketImg/%Y/%m/%d', blank=True, null=True)

    def __str__(self):
        img_name = self.ticket.user.username + ' -' + str(self.ticket.pk)
        return img_name


class TicketDetail(models.Model):
    ticket = models.ForeignKey(Ticket)
    index = models.CharField(max_length=20)
    content = models.TextField()

    def __str__(self):
        detail_name = self.ticket.user.username + ' -' + str(self.ticket.pk) + ' : ' + self.index
        return detail_name


class Emotion(models.Model):
    name = models.CharField(max_length=20)

    def __str__(self):
        return self.name

    @property
    def get_quote_count(self, series):
        return self.eventreview_set.filter(event__series=series).count()  # 작동 여부 점검 필요


class EventReview(ThankMixinModel):
    ticket = models.OneToOneField(Ticket, related_name='event_review')
    history = models.OneToOneField(RewardHistory, blank=True, null=True)
    event = models.ForeignKey(Event)
    total_star = models.PositiveSmallIntegerField(default=0)
    content = models.TextField(blank=True, null=True)
    emotion_set = models.ManyToManyField(
        Emotion,
        blank=True,
    )
    badge_set = models.ManyToManyField(
        'EventReviewBadge',
        blank=True,
    )
    anony_name = models.CharField(max_length=10, blank=True, null=True)

    is_confirmed = models.BooleanField(default=False)  # True이면 공개

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        review_name = self.event.series.name
        return review_name

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.is_confirmed:
            super().save(*args, **kwargs)
            if self.history:
                self.history.status = 'complete'
                self.history.save()

    def delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)
        if self.history:
            self.history.delete()


class EventReviewBadge(models.Model):
    name = models.CharField(max_length=10)
    color = models.CharField(max_length=10)

    def __str__(self):
        return self.name


class SeatReview(ThankMixinModel):
    ticket = models.OneToOneField(Ticket, related_name='seat_review')
    history = models.OneToOneField(RewardHistory, blank=True, null=True)
    seat = models.ForeignKey(Seat)
    real_seat_name = models.CharField(max_length=100)
    view_star = models.PositiveSmallIntegerField(default=0)
    real_star = models.PositiveSmallIntegerField(default=0)
    content = models.TextField(blank=True, null=True)
    badge_set = models.ManyToManyField(
        'SeatReviewBadge',
        blank=True,
    )
    anony_name = models.CharField(max_length=10, blank=True, null=True)

    is_confirmed = models.BooleanField(default=False)  # True이면 공개

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        review_name = self.seat.block.section.space.name + ' ' + self.seat.block.name + '블럭 ' + self.seat.name
        return review_name

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.is_confirmed:
            super().save(*args, **kwargs)
            if self.history:
                self.history.status = 'complete'
                self.history.save()

    def delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)
        if self.history:
            self.history.delete()


class SeatReviewBadge(models.Model):
    name = models.CharField(max_length=10)
    color = models.CharField(max_length=10)

    def __str__(self):
        return self.name


# ### 장소 > 정보공유 관련 모델 ### #

class ShareInfoCategory(models.Model):
    name = models.CharField(max_length=10)
    en_name = models.CharField(max_length=20)

    def __str__(self):
        return self.name


class ShareInfo(LikeMixinModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        blank=True,
        null=True,
    )
    place = models.ForeignKey(Place)
    category = models.ForeignKey(ShareInfoCategory)

    name = models.CharField(max_length=30)
    address = models.CharField(max_length=100, blank=True, null=True)
    lat_lon = models.CharField(max_length=20, blank=True, null=True)
    content = models.TextField()

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        info_name = self.place.name + ' - ' + self.name
        return info_name


class ShareInfoImg(models.Model):
    info = models.ForeignKey(
        ShareInfo,
        related_name='image_set',
    )
    img = models.ImageField(upload_to='ShareInfo/%Y/%m/%d', blank=True, null=True)


class ShareInfoComment(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL)
    anony_name = models.CharField(max_length=10, blank=True, null=True)
    share_info = models.ForeignKey(ShareInfo)
    content = models.TextField()

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.content

    class Meta:
        ordering = ('pk', )


# ### 이벤트 > 딥톡 관련 모델 ### #

class TalkTopic(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL)
    series = models.ForeignKey(Series)
    content = models.CharField(max_length=100)
    explain = models.CharField(max_length=200, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        topic_name = self.series.name + ' - ' + self.content
        return topic_name

    @property
    def is_joined(self, user):
        result = Talk.objects.filter(user=user, topic=self).exists()
        return result


class Talk(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL)
    # design = models.ForeignKey('TalkDesign', blank=True, null=True)
    anony_name = models.CharField(max_length=10, blank=True, null=True)
    topic = models.ForeignKey(TalkTopic)
    content = models.TextField()

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.content


# 톡톡 말풍선 디자인 -> 좀더 기획이 나온 뒤에 추가

# class TalkDesign(models.Model):
#     name = models.CharField(max_length=20)
#     img = models.ImageField(upload_to='TalkDesign/', blank=True, null=True)
#     explain = models.CharField(max_length=200)

#     def __str__(self):
#         return self.name
