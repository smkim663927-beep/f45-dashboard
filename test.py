import streamlit as st
import pandas as pd
from datetime import date

# 페이지 기본 설정
st.set_page_config(page_title="F45 Trial Onboarding", page_icon="🔴", layout="wide")

st.title("🔴 F45 트라이얼 온보딩 대시보드")
st.markdown("매일 아침 트라이얼 통합 리포트(CSV 또는 엑셀)를 업로드하여 오늘의 집중 케어 대상을 확인하세요.")
st.divider()

# ==========================================
# 1. 사이드바: 데이터 업로드
# ==========================================
st.sidebar.header("📁 데이터 업로드")
uploaded_file = st.sidebar.file_uploader("트라이얼 회원 데이터 (CSV, XLSX)", type=['csv', 'xlsx'])

st.sidebar.divider()
st.sidebar.markdown("⚙️ **설정**")
reference_date = st.sidebar.date_input("현재 날짜(오늘) 설정", date.today())
st.sidebar.caption("※ 컴퓨터가 [현재 날짜 - 각 회원의 시작일]을 계산하기 위해 필요한 달력입니다.")

# ==========================================
# 2. 데이터 처리 및 로직 적용
# ==========================================
if uploaded_file is not None:
    try:
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)
            
        df.columns = df.columns.str.strip()
        checkin_cols = [str(i) for i in range(1, 7) if str(i) in df.columns]
        
        def calculate_attendance(row):
            cumulative = 0
            max_consecutive = 0
            current_streak = 0
            for col in checkin_cols:
                val = str(row[col]).strip()
                if val not in ['nan', 'None', '', 'NaN']:
                    cumulative += 1
                    current_streak += 1
                    if current_streak > max_consecutive:
                        max_consecutive = current_streak
                else:
                    current_streak = 0
            return pd.Series([cumulative, max_consecutive])
            
        df[['cumulative_checkins', 'max_consecutive']] = df.apply(calculate_attendance, axis=1)
        
        df['trial 시작일자'] = pd.to_datetime(df['trial 시작일자'], errors='coerce').dt.date
        df['체험_경과일'] = df['trial 시작일자'].apply(
            lambda x: (reference_date - x).days + 1 if pd.notnull(x) else 0
        )
        df['특이 사항'] = df['특이 사항'].fillna("없음")

        # ==========================================
        # 3. 대시보드 화면 구성
        # ==========================================
        st.success("데이터 연동 완료! 아래 명단은 '각 회원의 Trial 시작일'을 기준으로 자동 분류되었습니다.")
        
        col1, col2 = st.columns([2, 1])

        with col1:
            st.subheader("🔥 오늘의 트라이얼 집중 케어 타겟")
            
            # [Day 1] 뉴비
            is_newbie = (df['체험_경과일'] <= 1)
            day1_members = df[is_newbie]
            
            with st.expander("🟢 [Day 1] 뉴비 (첫 방문 환영 및 시스템 안내)", expanded=True):
                if not day1_members.empty:
                    for _, row in day1_members.iterrows():
                        시작일_표시 = row['trial 시작일자'].strftime("%m/%d") if pd.notnull(row['trial 시작일자']) else "알수없음"
                        
                        st.write(f"**{row['이름']} 회원님** (시작일: {시작일_표시} ➡️ **{int(row['체험_경과일'])}일 차**)")
                        st.write(f"🏃 출석 현황: 누적 {int(row['cumulative_checkins'])}회 / 연속 {int(row['max_consecutive'])}회")
                        
                        if row['특이 사항'] != "없음":
                            st.warning(f"⚠️ 특이사항(부상): {row['특이 사항']}")
                            
                        st.caption(f"👉 Action: 성함 부르며 인사, 첫 방문 시 인바디 및 시스템 안내")
                        st.divider()
                else:
                    st.write("해당 회원이 없습니다.")

            # [Day 2~4] 적응기
            is_adaptation = (df['체험_경과일'] >= 2) & (df['체험_경과일'] <= 4)
            day24_members = df[is_adaptation]
            
            with st.expander("🟡 [Day 2~4] 적응기 (근육통 케어)", expanded=True):
                if not day24_members.empty:
                    for _, row in day24_members.iterrows():
                        시작일_표시 = row['trial 시작일자'].strftime("%m/%d")
                        
                        st.write(f"**{row['이름']} 회원님** (시작일: {시작일_표시} ➡️ **{int(row['체험_경과일'])}일 차**)")
                        st.write(f"🏃 출석 현황: 누적 {int(row['cumulative_checkins'])}회 / 연속 {int(row['max_consecutive'])}회")
                        
                        if row['특이 사항'] != "없음":
                            st.warning(f"⚠️ 특이사항(부상): {row['특이 사항']}")
                            
                        st.caption("👉 Action: 근육통 안부 확인, 적절한 무게 설정 제안")
                        st.divider()
                else:
                    st.write("해당 회원이 없습니다.")

            # [Day 5~6] 골든 타임
            is_golden_time = (df['체험_경과일'] >= 5)
            day_golden_members = df[is_golden_time]
            
            with st.expander("💰 [Day 5~6] 전환 임박 (멤버십 상담)", expanded=True):
                if not day_golden_members.empty:
                    for _, row in day_golden_members.iterrows():
                        시작일_표시 = row['trial 시작일자'].strftime("%m/%d")
                        
                        st.success(f"**{row['이름']} 회원님** (시작일: {시작일_표시} ➡️ **{int(row['체험_경과일'])}일 차**)")
                        st.write(f"🏃 출석 현황: 누적 {int(row['cumulative_checkins'])}회 / 연속 {int(row['max_consecutive'])}회")
                        
                        # 💡 아까 빠졌던 핵심 코드 추가 완료!!
                        if row['특이 사항'] != "없음":
                            st.warning(f"⚠️ 특이사항(부상): {row['특이 사항']}")
                            
                        st.caption("👉 Action: 운동 만족도 질문 및 당일 등록 프로모션 안내")
                        st.divider()
                else:
                    st.write("해당 회원이 없습니다.")

        with col2:
            st.subheader("🚨 리스크 관리")
            
            # [리스크] 출석 1회 이하 + 3일 이상 지남
            risk_condition = (df['cumulative_checkins'] <= 1) & (df['체험_경과일'] >= 3)
            risk_members = df[risk_condition]
            
            if not risk_members.empty:
                st.error("⚠️ 장기 미출석 (이탈 위험)")
                for _, row in risk_members.iterrows():
                    st.write(f"- **{row['이름']} 회원님** (현재 {int(row['체험_경과일'])}일 차 / 출석 {int(row['cumulative_checkins'])}회)")
                    
                    # 💡 리스크 관리 탭에도 혹시 몰라 추가했습니다!
                    if row['특이 사항'] != "없음":
                        st.warning(f"⚠️ 특이사항(부상): {row['특이 사항']}")
                        
                    st.caption("💌 Action: '요즘 바쁘신가요? 기간 홀딩 도와드릴까요?' 연락")
                    st.divider()
            else:
                st.info("현재 파악된 이탈 위험군이 없습니다. 👍")

    except Exception as e:
        st.error("데이터 처리 중 오류가 발생했습니다. 파일 형식을 확인해주세요.")
        st.write("에러 내용:", e)
else:
    st.info("👈 왼쪽 사이드바에서 트라이얼 데이터를 업로드해주세요.")