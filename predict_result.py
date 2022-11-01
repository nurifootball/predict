from . import models
from .schedule import stop_game
from predict import models as predict_model
from point import models as point_models


def pay_point():
    match_obj = models.Match.objects.filter(match_result_registration=False)
    for match in match_obj:
        user_predict_result_list = models.WalletPredictResultList.objects.filter(match=match, predict_result="예측성공")
        for prediction_success_user in user_predict_result_list:
            user = prediction_success_user.predict_wallet
            try:
                point_models.WalletPointHistory.objects.get(predict_match=match, point_wallet=user)
            except Exception as e:
                point_models.WalletPointHistory.objects.create(
                    point_wallet=user,
                    type="승부예측",
                    existing_point=user.point,
                    point=match.point,
                    desc=str(match) + " 경기에 예측 성공하였습니다.",
                    predict_match=match
                )
                user.point = user.point + match.point
                user.save()
                print(e)
    return True


def match_the_prediction():
    match_obj = models.Match.objects.filter(match_result_registration=False)
    for match in match_obj:
        games = models.PredictGame.objects.filter(match=match).order_by('game__game_date', "-game__id")

        predict_results = models.WalletPredictResultList.objects.filter(match=match)

        for game in games:
            state = game.game.game_state
            try:
                if state in stop_game:
                    cancel = models.CancelGame.objects.get(id=game.game.id)
                    game.cancel_game = cancel
                    game.save()
            except:
                pass

        for predict_result in predict_results:
            user_predicts = predict_result.predict_games.all().order_by("-id")
            for i,game in enumerate(games):
                obj = user_predicts[i]
                print(user_predicts[i])
                if game.cancel_game:
                    obj.predict_result = "예측성공"
                    obj.save(update_fields=['predict_result'])
                elif (game.game.home_team_score is not None) and (
                        game.game.away_team_score is not None):
                    if game.game.home_win and user_predicts[i].predict_select == "승":
                        obj.predict_result = "예측성공"
                        obj.save(update_fields=['predict_result'])
                    elif game.game.away_win and user_predicts[i].predict_select == "패":
                        obj.predict_result = "예측성공"
                        obj.save(update_fields=['predict_result'])
                    elif game.game.away_win is None and user_predicts[i].predict_select == "무":
                        obj.predict_result = "예측성공"
                        obj.save(update_fields=['predict_result'])
                    else:
                        print('실패')
                        obj.predict_result = "예측실패"
                        obj.save(update_fields=['predict_result'])
                    print(obj.predict_result)
                else:
                    match.match_result_registration = False
                    return "not end games"
                print(user_predicts[i].predict_result)
            predict_result.save()
        round = int(match.match_count)
        number_of_winners = 0
        try:
            for user_predict_result in predict_results:
                success_count = user_predict_result.predict_games.filter(predict_result="예측성공").count()
                if success_count == round:
                    number_of_winners += 1
                    user_predict_result.predict_result = "예측성공"
                else:
                    user_predict_result.predict_result = "예측실패"
                user_predict_result.save()
            match.number_of_winners = number_of_winners
            match.save()
        except Exception as e:
            print(e, "에러")
            predict_model.Schedule.objects.create(
                title="승부예측 당첨자 확인 및 포인트 지급 실패하였습니다."
            )

        pay_point()

        match.match_result_registration = True
        match.save()
        predict_model.Schedule.objects.create(
            title="승부예측 당첨자 확인 및 포인트 지급이 완료되었습니다."
        )









