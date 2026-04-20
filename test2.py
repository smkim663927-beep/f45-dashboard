import streamlit as st
import pandas as pd
from datetime import date

# 페이지 기본 설정
st.set_page_config(page_title="F45 Trial Onboarding", page_icon="🔴", layout="wide")

st.title("🔴 F45 트라이얼 온보딩 대시보드")
st.markdown("매일 아침 **트라이얼 통합 리포트(CSV 또는 엑셀)**를 업로드하세요.")
st.divider()

# ==========================================
# 1. 사이드바: 데이터 업로드 (엑셀, CSV 모두 지원)
# ==========================================
st.sidebar.header("📁 데이터 업로드")
uploaded_file = st.sidebar.file_uploader("트라이얼 회원 데이터 (CSV, XLSX)", type=['csv', 'xlsx'])

st.sidebar.divider()
st.sidebar.markdown("⚙️ **설정**")
reference_date = st.sidebar.date_input("오늘 날짜(기준일) 설정", date.today())
st.sidebar.caption("※ 이 날짜를 기준으로 '체험 N일차'를 판정합니다.")

# ==========================================
# 2. 데이터 처리 및 출석 계산
# ==========================================
if uploaded_file is not None:
    try:
        # 파일 형식에 따라 다르게 읽기
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
        df['days_since_start'] = df['trial 시작일자'].apply(
            lambda x: (reference_date - x).days + 1 if pd.notnull(x) else 0
        )
        df['특이 사항'] = df['특이 사항'].fillna("없음")

        # ==========================================
        # 3. 대시보드 화면 구성 (올려주신 코드 부분 적용!)
        # ==========================================
        st.success(f"데이터 연동 완료! ({uploaded_file.name})")
        
        col1, col2 = st.columns([2, 1])

        with col1:
            st.subheader("🔥 오늘의 트라이얼 집중 케어 타겟")
            
            # [뉴비 조건]
            is_newbie = (df['cumulative_checkins'] == 0) | \
                        ((df['cumulative_checkins'] == 1) & (df['days_since_start'] < 3)) | \
                        (df['trial 시작일자'] == reference_date)
            
            day1_members = df[is_newbie]
            
            with st.expander("🟢 [Newbie] 첫 방문 및 대기자", expanded=True):
                if not day1_members.empty:
                    for _, row in day1_members.iterrows():
                        if row['cumulative_checkins'] == 0:
                            status_tag = "⏳ 첫 출석 대기 중"
                        elif row['trial 시작일자'] == reference_date:
                            status_tag = "🆕 오늘 시작!"
                        else:
                            status_tag = "🏃 첫 출석 완료"
                            
                        st.write(f"**{row['이름']} 회원님** ({status_tag})")
                        if row['특이 사항'] != "없음":
                            st.warning(f"⚠️ 특이사항: {row['특이 사항']}")
                        st.caption(f"👉 체험 {row['days_since_start']}일차 | Action: 첫 방문 시 인바디 및 시스템 안내")
                else:
                    st.write("대상 회원이 없습니다.")

            # [적응기] 누적 2~3회
            day23_members = df[(df['cumulative_checkins'] >= 2) & (df['cumulative_checkins'] <= 3)]
            with st.expander("🟡 [Day 2~3] 적응기", expanded=True):
                if not day23_members.empty:
                    for _, row in day23_members.iterrows():
                        st.write(f"**{row['이름']} 회원님** (누적 {int(row['cumulative_checkins'])}회 / 연속 {int(row['max_consecutive'])}회)")
                        if row['특이 사항'] != "없음":
                            st.warning(f"⚠️ 부상 주의: {row['특이 사항']}")
                        st.caption("👉 Action: 근육통 안부 확인, 적절한 무게 설정 제안")
                else:
                    st.write("대상 회원이 없습니다.")

            # [골든 타임] 누적 4회 이상
            day4_members = df[df['cumulative_checkins'] >= 4]
            with st.expander("💰 전환 임박 (멤버십 상담)", expanded=True):
                if not day4_members.empty:
                    for _, row in day4_members.iterrows():
                        st.success(f"**{row['이름']} 회원님** (누적 {int(row['cumulative_checkins'])}회 / 연속 {int(row['max_consecutive'])}회)")
                        st.caption("👉 Action: 운동 만족도 질문 및 당일 등록 프로모션 안내")
                else:
                    st.write("대상 회원이 없습니다.")

        with col2:
            st.subheader("🚨 리스크 관리")
            
            # [리스크 조건: 딱 1회 오고 3일 이상 안 온 사람]
            risk_condition = (df['cumulative_checkins'] == 1) & (df['days_since_start'] >= 3)
            risk_members = df[risk_condition]
            
            if not risk_members.empty:
                st.error("⚠️ 1회 출석 후 장기 미출석 (이탈 위험)")
                for _, row in risk_members.iterrows():
                    st.write(f"- **{row['이름']} 회원님** (체험 {row['days_since_start']}일차)")
                    st.caption("💌 Action: '운동 너무 힘들지 않으셨나요? 내일 예약 도와드릴까요?' 카톡 발송")
            else:
                st.info("현재 파악된 이탈 위험군이 없습니다. 👍")

    except Exception as e:
        st.error("데이터 처리 중 오류가 발생했습니다. 엑셀/CSV 형식을 확인해주세요.")
        st.write("에러 내용:", e)
else:
    st.info("👈 왼쪽 사이드바에서 트라이얼 데이터를 업로드해주세요.")