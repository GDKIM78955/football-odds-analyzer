# database.py 내부의 save_match_data_to_sheets 함수 수정 예시

def save_match_data_to_sheets(match_info, odds_dict, stats_dict):
    client = get_gspread_client()
    if not client:
        return False, "구글 시트 연동 실패: Secrets 설정을 확인하세요."

    try:
        spreadsheet = client.open_by_key(SPREADSHEET_ID)

        season = match_info["season"]
        league = match_info["league"]
        match_date = match_info["date"]
        home_team = match_info["home"]
        away_team = match_info["away"]

        b_h, b_d, b_a = odds_dict.get("배트맨", (0.0, 0.0, 0.0))
        if b_h > 0 and b_d > 0 and b_a > 0:
            b_inv = (1/b_h) + (1/b_d) + (1/b_a)
            b_payout = 1 / b_inv
            b_prob_h = (1/b_h) / b_inv
            b_prob_d = (1/b_d) / b_inv
            b_prob_a = (1/b_a) / b_inv
        else:
            b_payout, b_prob_h, b_prob_d, b_prob_a = 0.0, 0.0, 0.0, 0.0

        home_score = stats_dict["home_1h"] + stats_dict["home_2h"]
        away_score = stats_dict["away_1h"] + stats_dict["away_2h"]

        if home_score > away_score:
            match_res = "홈승"
        elif home_score == away_score:
            match_res = "무승부"
        else:
            match_res = "원정승"

        score_total = home_score + away_score
        score_diff = home_score - away_score
        score_diff_abs = abs(score_diff)

        saved_count = 0
        failed_bookmakers = []

        # 1. 대상 북메이커 시트 일괄 저장
        for bm_name in BOOKMAKERS:
            if bm_name not in odds_dict:
                continue
            h, d, a = odds_dict[bm_name]
            if h <= 0 or d <= 0 or a <= 0:
                continue

            bm_inv = (1/h) + (1/d) + (1/a)
            bm_payout = 1 / bm_inv
            bm_prob_h = (1/h) / bm_inv
            bm_prob_d = (1/d) / bm_inv
            bm_prob_a = (1/a) / bm_inv

            diff_h = round(b_h - h, 2) if b_h > 0 else 0.0
            diff_d = round(b_d - d, 2) if d > 0 else 0.0
            diff_a = round(b_a - a, 2) if b_a > 0 else 0.0

            fair_h = round(b_payout / bm_prob_h, 6) if (b_payout > 0 and bm_prob_h > 0) else 0.0
            fair_d = round(b_payout / bm_prob_d, 6) if (b_payout > 0 and bm_prob_d > 0) else 0.0
            fair_a = round(b_payout / bm_prob_a, 6) if (b_payout > 0 and bm_prob_a > 0) else 0.0

            loss_h = round(((b_h - fair_h) / fair_h) * 100, 5) if fair_h > 0 else 0.0
            loss_d = round(((b_d - fair_d) / fair_d) * 100, 5) if fair_d > 0 else 0.0
            loss_a = round(((b_a - fair_a) / fair_a) * 100, 5) if fair_a > 0 else 0.0

            min_odd, max_odd = min(h, d, a), max(h, d, a)
            win_odd = h if match_res == "홈승" else (d if match_res == "무승부" else a)
            odd_type = "정배" if win_odd == min_odd else ("역배" if win_odd == max_odd else "중배")

            row_data_odds = [
                season, league, match_date, home_team, away_team,
                b_h, b_d, b_a,
                f"{round(b_payout * 100, 2)}%",
                f"{round(b_prob_h * 100, 2)}%", f"{round(b_prob_d * 100, 2)}%", f"{round(b_prob_a * 100, 2)}%",
                h, d, a,
                f"{round(bm_payout * 100, 2)}%",
                f"{round(bm_prob_h * 100, 2)}%", f"{round(bm_prob_d * 100, 2)}%", f"{round(bm_prob_a * 100, 2)}%",
                diff_h, diff_d, diff_a,
                loss_h, loss_d, loss_a,
                fair_h, fair_d, fair_a,
                home_score, away_score, score_total, score_diff, score_diff_abs,
                odd_type, match_res, win_odd
            ]

            success_flag = False
            # 429 에러 방지를 위한 재시도(Retry) 로직 추가
            for attempt in range(3):
                try:
                    ws = spreadsheet.worksheet(bm_name)
                    ws.append_row(row_data_odds, value_input_option="USER_ENTERED")
                    saved_count += 1
                    success_flag = True
                    time.sleep(0.3)  # API 호출 간격 확보 (429 방지)
                    break
                except Exception as e:
                    if "429" in str(e):
                        time.sleep(1.5 * (attempt + 1)) # 429 발생 시 대기 시간 연장
                    else:
                        time.sleep(0.5)
            
            if not success_flag:
                failed_bookmakers.append(bm_name.upper())

        # 2. '경기내용' 시트 저장
        h_1h = stats_dict["home_1h"]
        h_2h = stats_dict["home_2h"]
        a_1h = stats_dict["away_1h"]
        a_2h = stats_dict["away_2h"]
        h_shots = stats_dict["home_shots"]
        a_shots = stats_dict["away_shots"]
        h_sot = stats_dict["home_sot"]
        a_sot = stats_dict["away_sot"]

        h_1h_ratio = round((h_1h / home_score) * 100, 2) if home_score > 0 else 0.0
        h_2h_ratio = round((h_2h / home_score) * 100, 2) if home_score > 0 else 0.0
        a_1h_ratio = round((a_1h / away_score) * 100, 2) if away_score > 0 else 0.0
        a_2h_ratio = round((a_2h / away_score) * 100, 2) if away_score > 0 else 0.0

        h_sot_ratio = round((h_sot / h_shots) * 100, 2) if h_shots > 0 else 0.0
        a_sot_ratio = round((a_sot / a_shots) * 100, 2) if a_shots > 0 else 0.0

        home_tac_safe = f"'{stats_dict['home_tac'].strip()}" if stats_dict['home_tac'].strip() else ""
        away_tac_safe = f"'{stats_dict['away_tac'].strip()}" if stats_dict['away_tac'].strip() else ""

        row_data_stats = [
            season, league, match_date, home_team, away_team,
            h_1h, h_2h, a_1h, a_2h,
            f"{h_1h_ratio}%", f"{h_2h_ratio}%", f"{a_1h_ratio}%", f"{a_2h_ratio}%",
            home_tac_safe, away_tac_safe,
            h_shots, a_shots, h_sot, a_sot,
            f"{h_sot_ratio}%", f"{a_sot_ratio}%",
            f"{stats_dict['home_poss']}%", f"{stats_dict['away_poss']}%",
            f"{stats_dict['home_pass']}%", f"{stats_dict['away_pass']}%",
            stats_dict['home_yc'], stats_dict['away_yc'], stats_dict['home_rc'], stats_dict['away_rc'],
            stats_dict['home_xg'], stats_dict['away_xg']
        ]

        stats_saved = False
        for attempt in range(3):
            try:
                ws_stats = spreadsheet.worksheet(STATS_SHEET_NAME)
                ws_stats.append_row(row_data_stats, value_input_option="USER_ENTERED")
                stats_saved = True
                time.sleep(0.3)
                break
            except Exception as e:
                if "429" in str(e):
                    time.sleep(1.5 * (attempt + 1))
                else:
                    time.sleep(0.5)

        if not stats_saved:
            failed_bookmakers.append(STATS_SHEET_NAME)

        # 3. 실패한 시트가 하나라도 존재하면 에러 반환 (대기열 안 넘어가도록 방지)
        if failed_bookmakers:
            return False, f"⚠️ 다음 시트 저장 실패 (429 과부하 또는 네트워크 오류): {', '.join(failed_bookmakers)}. 다시 시도해 주세요."

        return True, f"배당 {saved_count}개사 탭 및 '{STATS_SHEET_NAME}' 탭 저장 완료"

    except Exception as e:
        return False, f"시스템 오류 발생: {str(e)}"
