
from dateutil.relativedelta import relativedelta
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from pytz import timezone as pytz_timezone
from django.core import serializers
from django.conf import settings
from django.shortcuts import render, redirect, HttpResponse, get_object_or_404, HttpResponseRedirect, reverse

from community import models as commu_models
from community import forms as commu_forms

from core import models as core_models
from predict_geon import models as predict_models
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from users import models as users_models
from core.views_pc import get_client_ip
from web3 import Web3
from NuriAdmin import models as Admin_models
from django.contrib import messages
from point import models as point_models
from predict import models as test_models
import json


def predict(request):
    if request.method == 'GET':
        if request.GET.get('match'):
            match_id = request.GET.get('match')
            try:
                match = predict_models.Match.objects.get(
                    id=match_id
                )
            except Exception as e:
                return redirect('predict:main')
        else:
            match = predict_models.Match.objects.first()

        predict_games = predict_models.PredictGame.objects.filter(
            match=match
        ).order_by('game__game_date', "-game__id")
        context = dict()
        context['match'] = match
        context['predict_games'] = predict_games
        context['all_participants'] = match.participants + match.participants_plus

        if match.match_result_registration:
            return render(request, "PC_220112ST/predict/wallet/predict_result.html", context)


        return render(request, "PC_220112ST/predict/wallet/predict.html", context)
    if request.method == "POST" and request.POST.get('address') and "pChk" in request.POST:
        match = predict_models.Match.objects.first()
        connect_ip = get_client_ip(request)
        predict_games = predict_models.PredictGame.objects.filter(
            match=match
        ).order_by('game__game_date', "-game__id")
        context = dict()
        context['match'] = match
        context['predict_games'] = predict_games

        match_part_ip_count = predict_models.WalletPredictResultList.objects.filter(
            match=match,
            connect_ip=connect_ip
        ).count()

        if match_part_ip_count >= 200:
            messages.error(request, 'You already has predict history')
            return render(request, "PC_220112ST/predict/wallet/predict.html", context)

        address_text = request.POST.get('address')
        try:
            check_address = Web3.toChecksumAddress(address_text)
            address = Web3.isAddress(check_address)
            wallet_model,is_created = predict_models.WalletModel.objects.get_or_create(
                address=address_text
            )
        except:
            messages.warning(request, 'Invalid address')
            return render(request, "PC_220112ST/predict/wallet/predict.html", context)

        is_history = predict_models.WalletPredictResultList.objects.filter(
            match=match,
            predict_wallet=wallet_model
        ).exists()
        if is_history:
            messages.error(request, 'You already has predict history')
            return render(request, "PC_220112ST/predict/wallet/predict.html", context)

        if "pChk" in request.POST:
            try:
                match_predict = request.POST.getlist("pChk")
                wallet_history = predict_models.WalletPredictResultList.objects.create(
                    predict_wallet=wallet_model,
                    match=match,
                    connect_ip=connect_ip
                )
                with transaction.atomic():
                    for i, predict_game in enumerate(predict_games):
                        # match_predict = request.POST.getlist("pChk"+str(i+1))
                        game = predict_models.WalletPredict.objects.create(
                            predict_wallet=wallet_model,
                            game=predict_game,
                            predict_select=match_predict[i]
                        )
                        wallet_history.predict_games.add(game)

                    # 회차 참여자수
                    match.participants = match.participants + 1
                    match.save()
                    all_participants = match.participants + match.participants_plus
                    for predict_game in predict_games:
                        # 경기 별 승무패 예측확률 계산.
                        if all_participants != 0:
                            win = int(
                                (predict_models.WalletPredict.objects.filter(game=predict_game,
                                                                           predict_select="승").count() +
                                 predict_game.option_rate_win) / all_participants * 100)
                            lose = int(
                                (predict_models.WalletPredict.objects.filter(game=predict_game,
                                                                           predict_select="패").count() +
                                 predict_game.option_rate_lose) / all_participants * 100)
                            draw = int(
                                (predict_models.WalletPredict.objects.filter(game=predict_game,
                                                                           predict_select="무").count() +
                                 predict_game.option_rate_draw) / all_participants * 100)
                            if win:
                                predict_game.rate_win = win
                            else:
                                predict_game.rate_win = 0
                            if lose:
                                predict_game.rate_lose = lose
                            else:
                                predict_game.rate_lose = 0
                            if draw:
                                predict_game.rate_draw = draw
                            else:
                                predict_game.rate_draw = 0
                            predict_game.save()
                return redirect("predict:predict_history")
            except Exception as e:
                messages.warning(request, 'error has occurred Please try again or contact the administrator')
                return render(request, "PC_220112ST/predict/wallet/predict.html", context)

    else:
        messages.warning(request, 'error has occurred Please try again or contact the administrator')
        return redirect('core:error_admin')



def get_user_predict(request):
    if request.method == "GET":
        try:
            address = request.GET.get('address')
            address = Web3.toChecksumAddress(address)
        except:
            return JsonResponse({'result':None})

        match_id = request.GET.get('match_id')
        wallet_address = predict_models.WalletModel.objects.filter(
            address__iexact=address
        )
        if wallet_address.exists():
            wallet_address = wallet_address[0]
        else:
            return JsonResponse({'result': None})

        user_predict_result = predict_models.WalletPredictResultList.objects.filter(
            predict_wallet=wallet_address,
            match__id=match_id,
        )
        if user_predict_result.exists():
            user_predict_result = user_predict_result[0]
            predicted_games = user_predict_result.predict_games.all().values_list('predict_select').order_by('id')

        else:
            return JsonResponse({'result': None,
                                 'point': wallet_address.point})

        predict_result = {
            'get_created': user_predict_result.created,
            'result': user_predict_result.predict_result
        }
        return JsonResponse({
            "result": 'success',
            'wallet_select': list(predicted_games),
            'point': wallet_address.point,
            'predict_result':predict_result,
        })
    else:
        return JsonResponse({'result': "ERROR"})


def create_user_predict(request):
    if request.method == "POST":
        connect_ip = get_client_ip(request)

        now_match = predict_models.Match.objects.first()
        match_id = request.POST.get('match_id')

        match_part_ip_count = predict_models.WalletPredictResultList.objects.filter(
            match=now_match,
            connect_ip=connect_ip
        ).count()

        if match_part_ip_count >= 200:
            return JsonResponse({
                'result': False,
                'code': 'ip error'
            })
        if now_match.id != match_id:
            return JsonResponse({
                'code': 'Match Id not in progress'
            })

        predict_games = predict_models.PredictGame.objects.filter(
            match=now_match
        ).order_by('game__game_date', "-game__id")

        wallet_address = request.POST.get('address')

        user_predict = []
        for i, predict_game in enumerate(predict_games):
            home_check = request.POST.get(f'pChk{i}_1')
            draw_check = request.POST.get(f'pChk{i}_2')
            away_check = request.POST.get(f'pChk{i}_3')
            if home_check:
                predict_select = '승'
            elif draw_check:
                predict_select = '무'
            elif away_check:
                predict_select = '패'
            else:
                return JsonResponse({
                    'code': 'error'
                })

            temp = predict_models.WalletPredict(
                predict_wallet=wallet_address,
                game=predict_game.game,
                predict_select=predict_select
            )
            user_predict.append(temp)
        predict_games = predict_models.WalletPredict.objects.bulk_create(user_predict)
        wallet_predict_result = predict_models.WalletPredictResultList.objects.create(
            predict_wallet=wallet_address,
            connect_ip=connect_ip,
            match=now_match,
        )
        for predict_game in predict_games:
            wallet_predict_result.predict_games.add(predict_game)

        return JsonResponse({
            'result': 'success'
        })
    else:
        return HttpResponse(404)


def point_history_list(request):
    return render(request, 'PC_220112ST/predict/wallet/point_history.html')

def get_point_history(request):
    if request.method == "GET" and request.GET.get('address'):
        month_list = ['1', '2', '3', '6', '12']
        context = {}

        address_text = request.GET.get('address')
        month_text = request.GET.get('month')
        try:
            check_address = Web3.toChecksumAddress(address_text)
            address = Web3.isAddress(check_address)
            wallet_model,is_created = predict_models.WalletModel.objects.get_or_create(
                address=address_text
            )
        except Exception as e:
            messages.warning(request, 'Invalid address')
            return render(request, 'PC_220112ST/predict/wallet/ajax/get_user_predict_list.html')

        q = Q(point_wallet=wallet_model)
        if month_text and month_text in month_list:
            month = relativedelta(months=int(month_text))
            now = timezone.now()
            q |= Q(predict_match__deadline__range=(now, now - month))
        else:
            month_text = "All"
        point_history = point_models.WalletPointHistory.objects.filter(q)
        if not point_history.exists():
            return render(request, 'PC_220112ST/predict/wallet/ajax/get_point_history.html')
        context['history_count'] = point_history.count()
        paginator = Paginator(point_history, 10)
        page_num = request.GET.get('page')

        try:
            point_history = paginator.page(page_num)
        except PageNotAnInteger:
            point_history = paginator.page(1)
        except EmptyPage:
            point_history = paginator.page(paginator.num_pages)

        index = point_history.number - 1
        max_index = len(paginator.page_range)
        start_index = index - 4 if index >= 4 else 0
        if index < 4:
            end_index = 7 - start_index
        else:
            end_index = index + 5 if index <= max_index - 5 else max_index
        page_range = list(paginator.page_range[start_index:end_index])


        context['point_history'] = point_history
        context['page_range'] = page_range
        context['result'] = 'success'
        context['month_text'] = month_text
        return render(request, 'PC_220112ST/predict/wallet/ajax/get_point_history.html',context)
    else:
        return render(request, 'PC_220112ST/predict/wallet/ajax/get_point_history.html')


def get_point_history_detail(request):
    if request.method == "GET":
        pk = request.GET.get('pk')
        history_detail = point_models.WalletPointHistory.objects.filter(
            id = int(pk)
        )
        if history_detail.exists():
            return render(request, 'PC_220112ST/predict/wallet/ajax/get_point_detail.html',{'history_detail':history_detail[0]})
        else:
            messages.warning(request,'invalid request')
            return render(request, 'PC_220112ST/predict/wallet/ajax/get_point_detail.html')
    else:
        messages.warning(request, 'invalid request')
        return render(request, 'PC_220112ST/predict/wallet/ajax/get_point_detail.html')

def predict_history_list(request):
    return render(request, 'PC_220112ST/predict/wallet/my_predict_history.html')


def get_user_predict_history_list(request):
    if request.method == "GET" and request.GET.get('address'):
        month_list = ['1', '2', '3', '6', '12']
        context = {}

        address_text = request.GET.get('address')
        month_text = request.GET.get('month')
        try:
            check_address = Web3.toChecksumAddress(address_text)
            address = Web3.isAddress(check_address)
            wallet_model,is_created = predict_models.WalletModel.objects.get_or_create(
                address=address_text
            )
        except Exception as e:
            messages.warning(request, 'Invalid address')
            return render(request, 'PC_220112ST/predict/wallet/ajax/get_user_predict_list.html')

        q = Q(predict_wallet=wallet_model)
        if month_text and month_text in month_list:
            month = relativedelta(months=int(month_text))
            now = timezone.now()
            q |= Q(match__deadline__range=(now, now - month))
        else:
            month_text = "All"
        user_match_list = predict_models.WalletPredictResultList.objects.filter(q)
        if not user_match_list.exists():
            return render(request, 'PC_220112ST/predict/wallet/ajax/get_user_predict_list.html')

        paginator = Paginator(user_match_list, 10)
        page_num = request.GET.get('page')

        try:
            history_objs = paginator.page(page_num)
        except PageNotAnInteger:
            history_objs = paginator.page(1)
        except EmptyPage:
            history_objs = paginator.page(paginator.num_pages)

        index = history_objs.number - 1
        max_index = len(paginator.page_range)
        start_index = index - 4 if index >= 4 else 0
        if index < 4:
            end_index = 7 - start_index
        else:
            end_index = index + 5 if index <= max_index - 5 else max_index
        page_range = list(paginator.page_range[start_index:end_index])



        context['match_count'] = user_match_list.count()

        context['user_match_list'] = user_match_list
        context['history_objs'] = history_objs
        context['page_range'] = page_range
        context['result'] = 'success'
        context['month_text'] = month_text
        return render(request, 'PC_220112ST/predict/wallet/ajax/get_user_predict_list.html',context)
    else:
        return render(request, 'PC_220112ST/predict/wallet/ajax/get_user_predict_list.html')
