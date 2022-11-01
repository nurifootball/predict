from logging import NullHandler
from re import T
import pytz
from pytz import timezone

from django.db import models
from django.conf import settings
from core import models as core_models
from datetime import datetime, timedelta
from users import models as users_models
from django.utils import translation
from django.utils import timezone as django_timezone


# Predict Open Status


class PredictError(core_models.TimeStampeModel):
    """ 승부예측 에러 모음 """
    error_user = models.ForeignKey(users_models.User, verbose_name="에러낸 유저", on_delete=models.CASCADE,
                                   null=True, blank=True)
    error_comment = models.TextField("승부예측 관련 에러", null=True, blank=True)


class PredictOpenStatusTest(core_models.TimeStampeModel):
    """
        경기 승부예측 오픈 설정
    """
    desc = models.CharField("설명 : ", null=True, blank=True, max_length=150)
    open_status = models.BooleanField(default=False)  # True : 경기오픈, False: 경기 대기

    class Meta:
        verbose_name_plural = "[Third] 승부예측 오픈 설정"
        ordering = ['-created']


class Country(core_models.TimeStampeModel):
    """
        API로 불러온 국가 모델
    """
    id = models.AutoField("Country_id", primary_key=True, null=False)
    country_name = models.CharField("국가", max_length=100,null=True,blank= True)
    country_code = models.CharField("국가코드", max_length=5, null=True, blank=True)
    flag = models.ImageField("국기", null=True,blank= True)

    def __str__(self):
        return self.country_name

    class Meta:
        verbose_name_plural = "국가"


class Team(core_models.TimeStampeModel):
    """
        API로 불러온 팀 모델
    """
    id = models.IntegerField("Team_id", primary_key=True, unique=True, default=None)
    team_name = models.CharField("팀명", max_length=100,null=True,blank= True)
    team_name_en = models.CharField("영문팀명", max_length=100, null=True, blank=True)
    team_emblem = models.ImageField("팀 엠블럼 on", null=True,blank= True)
    country = models.ForeignKey(Country, on_delete=models.CASCADE,null=True,blank= True)

    def __str__(self):
        lang = translation.get_language()
        if lang == "ko":
            return self.team_name[0:6]
        else:
            return self.team_name_en[0:20]

    class Meta:
        verbose_name_plural = "프로 팀"


class Leagues(core_models.TimeStampeModel):
    """
        API로 불러온 리그 모델
    """
    id = models.IntegerField("Leagues_id", primary_key=True, unique=True, default=None)
    leagues_name = models.CharField("리그 이름", max_length=100,null=True,blank= True)
    leagues_loge = models.ImageField("리그 로고", null=True,blank= True)
    country = models.ForeignKey(Country, on_delete=models.CASCADE,null=True,blank= True)
    season = models.CharField("시즌", max_length=6, null=True, blank=True)

    def __str__(self):
        return self.leagues_name

    class Meta:
        verbose_name_plural = "리그"


class Game(core_models.TimeStampeModel):
    """
        API에서 가져온 경기 내역 저장 모델
    """
    id = models.IntegerField("Game_id", primary_key=True, unique=True, default=None)
    League = models.ForeignKey(Leagues, on_delete=models.CASCADE,null=True,blank= True)
    home_team = models.ForeignKey(Team, related_name="home_team", on_delete=models.CASCADE,null=True,blank= True)
    away_team = models.ForeignKey(Team, related_name="away_team", on_delete=models.CASCADE,null=True,blank= True)
    home_team_score = models.IntegerField("홈팀 점수", null=True, blank=True)
    away_team_score = models.IntegerField("어웨이팀 점수", null=True, blank=True)
    home_win = models.BooleanField("홈팀 결과", null=True, blank=True)
    away_win = models.BooleanField("어웨이팀 결과", null=True, blank=True)
    game_date = models.DateTimeField("경기 시간",null=True, blank=True)
    game_state = models.CharField("경기 상태", null=True, blank=True, max_length=10)

    class Meta:
        ordering = ['-game_date']
        verbose_name_plural = "경기 목록"

    def __str__(self):
        KST = pytz.timezone('Asia/Seoul')
        game_date = self.game_date.astimezone(KST)
        game_date = str(game_date.year) + "년" + str(game_date.month) + "월" + str(game_date.day) + "일" + \
                    " " + str(game_date.hour) + "시" + str(game_date.minute) + "분"

        return str(self.League) + " - " + str(self.home_team) + " VS " + str(self.away_team) + " ||| " + game_date

    def get_game_date(self):
        lang = translation.get_language()
        if lang == "ko":
            game_date = self.game_date
        else:
            game_date = self.game_date + timedelta(hours=-9)

        return game_date


class Match(core_models.TimeStampeModel):
    """
        회차 등록 모델
    """
    match_result_registration = models.BooleanField("경기결과 등록여부", default=False)
    # 년도
    year = models.CharField("년도(yyyy)", null=True, blank=False, max_length=100)
    # 회차
    round = models.CharField("회차", null=True, blank=False, max_length=100)
    # 회차 경기 수
    match_count = models.CharField("회차별 경기수 ", null=True, blank=False, max_length=100)
    # 적중시 포인트 지급량
    point = models.IntegerField("적중시 포인트", default=0)
    deadline = models.DateTimeField("마감시간", null=True, blank=False)

    participants = models.IntegerField("회차 참여자 수", default=0)

    number_of_winners = models.IntegerField("당첨자 수", default=0)

    @property
    def deadline_at_korean_time(self):
        korean_timezone = timezone(settings.TIME_ZONE)
        return self.deadline.astimezone(korean_timezone)

    # 생성시간 -> 한국시간으로 변경
    @property
    def created_at_korean_time(self):
        korean_timezone = timezone(settings.TIME_ZONE)
        return self.created.astimezone(korean_timezone)

    def get_deadline(self):
        lang = translation.get_language()
        if lang == "ko":
            deadline = self.deadline
        else:
            deadline = self.deadline + timedelta(hours=-9)
        return deadline

    def is_over_deadline(self):
        if self.deadline < django_timezone.now():
            return True
        else:
            return False


    def __str__(self):
        return str(self.year) + "년도" + str(self.round) + "회차"



    class Meta:
        verbose_name_plural = "[First]승부예측 회차"
        ordering = ['-created']


# 취소 또는 연기 등 경기에 문제가 발생한 경기 저장 모델
class CancelGame(core_models.TimeStampeModel):
    """
        문제가 발생한 경기를 저장하는 컬럼
    """
    id = models.IntegerField("cancel_Game_id", primary_key=True, unique=True, default=None)
    League = models.ForeignKey(Leagues, on_delete=models.CASCADE,null=True,blank= True)
    home_team = models.ForeignKey(Team, related_name="cancel_home_team", on_delete=models.CASCADE,null=True,blank= True)
    away_team = models.ForeignKey(Team, related_name="cancel_away_team", on_delete=models.CASCADE,null=True,blank= True)
    game_date = models.DateTimeField("경기 시간",null=True,blank= True)
    game_state = models.CharField("경기 상태", null=True, blank=True, max_length=10)

    def __str__(self):
        KST = pytz.timezone('Asia/Seoul')
        game_date = self.game_date.astimezone(KST)
        game_date = str(game_date.year) + "년" + str(game_date.month) + "월" + str(game_date.day) + "일" + \
                    " " + str(game_date.hour) + "시" + str(game_date.minute) + "분"

        return str(self.League) + " - " + str(self.home_team) + " VS " + str(self.away_team) + " ||| " + game_date

    class Meta:
        ordering = ['-game_date']
        verbose_name_plural = "취소 또는 연기된 승부예측 경기"


class PredictGame(core_models.TimeStampeModel):
    """
        각 회차별 등록된 경기 1개의 모델
    """
    game = models.ForeignKey(Game, on_delete=models.CASCADE,null=True,blank= True)
    match = models.ForeignKey(Match, on_delete=models.CASCADE,null=True,blank= True)
    cancel_game = models.ForeignKey(CancelGame, on_delete=models.CASCADE, null=True, blank=True)
    rate_win = models.IntegerField("승리 투표율", null=True, blank=True, default=0)
    rate_lose = models.IntegerField("패배 투표율", null=True, blank=True, default=0)
    rate_draw = models.IntegerField("무승부 투표율", null=True, blank=True, default=0)

    def __str__(self):
        return str(self.match) + " " + str(self.game)

    class Meta:
        verbose_name_plural = "[Second]승부예측 경기 팀 선정"
        ordering = ['-created']

    def get_game_result(self):
        if self.game.home_win:
            return 'home'
        elif self.game.away_win:
            return 'away'
        elif self.cancel_game:
            return 'cancel'
        else:
            return 'draw'


class UserPredictResultList(core_models.TimeStampeModel):
    """
        회차별 유저의 승부예측 결과 저장 모델
    """
    RESULT = (
        ("예측성공", "예측성공"),
        ("예측실패", "예측실패"),
        ("대기중", "대기중"),
    )

    predict_user = models.ForeignKey(users_models.User, on_delete=models.CASCADE,null=True,blank= True)
    match = models.ForeignKey(Match, on_delete=models.CASCADE,null=True,blank= True)
    predict_result = models.CharField("예측 결과", max_length=10, choices=RESULT, default="대기중")

    def get_created(self):
        lang = translation.get_language()
        if lang == "ko":
            deadline = self.created
        else:
            deadline = self.created + timedelta(hours=-9)
        return deadline

    class Meta:
        verbose_name_plural = "[User]유저 승부예측 회차별 결과"
        ordering = ['-created']


class UserPredict(core_models.TimeStampeModel):
    """
        회차에 등록된 경기 별 유저의 예측을 저장할 모델
    """
    MATCH = (
        ("승", "승"),
        ("무", "무"),
        ("패", "패"),
    )
    RESULT = (
        ("예측성공", "예측성공"),
        ("예측실패", "예측실패"),
        ("대기중", "대기중"),
    )
    predict_user = models.ForeignKey(users_models.User, on_delete=models.CASCADE,null=True,blank= True)
    game = models.ForeignKey(PredictGame, on_delete=models.CASCADE,null=True,blank= True)
    predict_result = models.CharField("예측 결과", max_length=10, choices=RESULT, default="대기중")
    predict_select = models.CharField("게임 예측", max_length=10, choices=MATCH, default="")

    class Meta:
        verbose_name_plural = "[User]유저 승부예측 기록"
        ordering = ['-created']


# 승부예측 댓글
class PredictComment(core_models.TimeStampeModel):
    """
        회차별 댓글을 저장하는 모델
    """

    match = models.ForeignKey(Match, verbose_name="해당 승부예측", on_delete=models.CASCADE,null=True,blank= True)
    writer = models.ForeignKey(users_models.User, verbose_name="작성자", on_delete=models.CASCADE, null=True,blank= True)
    writer_name = models.CharField("댓글 등록 유저", null=True, max_length=150,blank= True)
    comment_report = models.BooleanField("신고여부", default=False)
    content = models.TextField('댓글 내용', null=True, blank=True)
    comment_blind = models.BooleanField("숨김여부", default=False)

    class Meta:
        verbose_name_plural = "댓글"
        ordering = ['-created']

    def __str__(self):
        return self.content[:10] + '/' + self.writer.username

    @property
    def date(self):
        date = self.created + timedelta(hours=9)
        return date.strftime('%y.%m.%d %H:%M:%S')

    @property
    def user_name(self):
        return self.writer.username

    @property
    def write_content(self):
        return self.content


class Predict_Point_History(core_models.TimeStampeModel):
    """

    """
    TYPE = (
        ("승부예측", "승부예측"),
        ("리워드", "리워드"),
    )

    # 당첨유저
    point_user = models.ForeignKey(settings.AUTH_USER_MODEL,related_name='prdict_point', null=True, on_delete=models.CASCADE)
    point_user_str = models.CharField("포인트획득유저", null=True, max_length=150)

    # 획득방법
    type = models.CharField("획득방법", null=True, blank=True, max_length=150, choices=TYPE)

    # 기존 포인트
    existing_point = models.IntegerField("기존포인트", null=True, blank=True)

    # 획득 보상 포인트
    point = models.IntegerField("획득포인트", default=0)

    # 획득한 내역 설명
    desc = models.TextField("획득설명", null=True,blank= True)

    # 승부예측 모델
    predict_match = models.ForeignKey(Match, null=True, on_delete=models.CASCADE,blank= True)

    # 생성시간 -> 한국시간으로 변경
    @property
    def created_at_korean_time(self):
        korean_timezone = timezone(settings.TIME_ZONE)
        return self.created.astimezone(korean_timezone)

    class Meta:
        verbose_name_plural = "포인트 지급 내역"
        ordering = ['-created']


class MainMatch(core_models.TimeStampeModel):
    main_match = models.OneToOneField(Game, related_name="Main_Match", on_delete=models.CASCADE, null=True,blank= True)
    match = models.OneToOneField(Match, related_name="for_Match", on_delete=models.CASCADE, null= True, blank= True)


    class Meta:
        verbose_name_plural = "메인 경기"


class WalletModel(core_models.TimeStampeModel):
    address = models.CharField(max_length=60, null=False, blank=False)
    point = models.BigIntegerField('포인트',default=0)


class WalletPredict(core_models.TimeStampeModel):
    """
        회차에 등록된 경기 별 유저의 예측을 저장할 모델
    """
    MATCH = (
        ("승", "승"),
        ("무", "무"),
        ("패", "패"),
    )
    RESULT = (
        ("예측성공", "예측성공"),
        ("예측실패", "예측실패"),
        ("대기중", "대기중"),
    )
    predict_wallet = models.ForeignKey(WalletModel, on_delete=models.CASCADE,null=True,blank= True)
    game = models.ForeignKey(PredictGame, on_delete=models.CASCADE,null=True,blank= True)
    predict_result = models.CharField("예측 결과", max_length=10, choices=RESULT, default="대기중")
    predict_select = models.CharField("게임 예측", max_length=10, choices=MATCH, default="")

    class Meta:
        verbose_name_plural = "[Wallet]유저 승부예측 기록"
        ordering = ['-created']


class WalletPredictResultList(core_models.TimeStampeModel):
    """
        회차별 유저의 승부예측 결과 저장 모델
    """
    RESULT = (
        ("예측성공", "예측성공"),
        ("예측실패", "예측실패"),
        ("대기중", "대기중"),
    )

    predict_wallet = models.ForeignKey(WalletModel, on_delete=models.CASCADE,null=True,blank= True)
    match = models.ForeignKey(Match, on_delete=models.CASCADE,null=True,blank= True)
    predict_result = models.CharField("예측 결과", max_length=10, choices=RESULT, default="대기중")
    connect_ip = models.CharField(max_length=20, null=False)
    predict_games = models.ManyToManyField(WalletPredict)

    @property
    def get_created(self):
        lang = translation.get_language()
        if lang == "ko":
            return self.created
        else:
            return self.created + timedelta(hours=-9)

    class Meta:
        verbose_name_plural = "[wallet] predict_result"
        ordering = ['-created']

