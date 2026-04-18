import streamlit as st
import pandas as pd
from datetime import date, datetime

# 페이지 기본 설정
st.set_page_config(page_title="F45 Trial Onboarding", page_icon="🔴", layout="wide")

st.title("🔴 F45 트라이얼(무료체험) 온보딩 대시보드")
st.markdown("매일 아침 **Glofox 출석 리포트**를 업로드하여 오늘의 집중 케어 대상을 확인하세요.")
st.divider()

# ==========================================
# 1. 사이드바: 파일 업로드 기능 구현
# ==========================================
st.sidebar.header("📁 Glofox 데이터 업로드")
st.sidebar.markdown("Glofox에서 다운로드한 CSV 파일을 올려주세요.")

members_file = st.sidebar.file_uploader("1. 트라이얼 회원 명부 (CSV)", type=['csv'])
attendance_file = st.sidebar.file_uploader("2. 출석/예약 리포트 (CSV)", type=['csv'])

# ==========================================
# 2. 데이터 처리 및 대시보드 렌더링
# ==========================================
# 두 파일이 모두 업로드 되었을 때만 메인 화면을 보여줍니다.
if members_file is not None and attendance_file is not None:
    try:
        # CSV 파일 읽기
        df_members = pd.read_csv(members_file)
        df_attendance = pd.read_csv(attendance_file)
        
        # 💡 [핵심] 날짜 데이터를 문자열(String)에서 날짜형(Date)으로 변환
        # Glofox에서 엑셀을 받으면 날짜 형식이 다를 수 있으므로 표준화가 필요합니다.
        df_members['trial_start_date'] = pd.to_datetime(df_members['trial_start_date']).dt.date
        df_attendance['date'] = pd.to_datetime(df_attendance['date']).dt.date
        
        today = date.today()
        
        # 체험 N일차 계산
        df_members['days_since_start'] = (today - df_members['trial_start_date']).dt.days + 1
        
        # 누적 체크인(출석) 횟수 계산 (Glofox의 출석 상태값 기준)
        # 'Attended' 또는 한글로 '출석'으로 되어있을 경우를 모두 대비
        attended_mask = df_attendance['status'].isin(['Attended', '출석'])
        checkins = df_attendance[attended_mask].groupby('member_id').size().reset_index(name='cumulative_checkins')
        df_main = pd.merge(df_members, checkins, on='member_id', how='left').fillna({'cumulative_checkins': 0})
        
        # 오늘 날짜 기준 당일 취소(Canceled) 여부 확인
        canceled_mask = (df_attendance['date'] == today) & (df_attendance['status'].isin(['Canceled', '취소']))
        today_cancels = df_attendance[canceled_mask]['member_id'].tolist()
        df_main['canceled_today'] = df_main['member_id'].apply(lambda x: True if x in today_cancels else False)

        # ==========================================
        # 3. Streamlit 대시보드 UI 구현 (이전과 동일)
        # ==========================================
        st.success(f"데이터 연동 완료! (기준일: {today.strftime('%Y년 %m월 %d일')})")
        
        col1, col2 = st.columns([2, 1])

        with col1:
            st.subheader("🔥 오늘의 트라이얼 집중 케어 타겟")
            
            day1_members = df_main[df_main['cumulative_checkins'] == 1]
            with st.expander("🟢 [Day 1] 첫 방문 뉴비 (시스템 안내 및 부상 체크 필수)", expanded=True):
                if not day1_members.empty:
                    for _, row in day1_members.iterrows():
                        st.write(f"**{row['name']} 회원님** (체험 {row['days_since_start']}일차)")
                        st.caption("👉 Action: 인바디 측정 권유, 스크린 보는 법, 이동 동선 안내")
                else:
                    st.write("해당 회원이 없습니다.")

            day23_members = df_main[(df_main['cumulative_checkins'] >= 2) & (df_main['cumulative_checkins'] <= 3)]
            with st.expander("🟡 [Day 2~3] 적응기 (근육통 체크 및 난이도 조절)", expanded=True):
                if not day23_members.empty:
                    for _, row in day23_members.iterrows():
                        st.write(f"**{row['name']} 회원님** (누적 {int(row['cumulative_checkins'])}회 출석)")
                        st.caption("👉 Action: 어제 운동 부위 근육통 확인, 웜업 시 가벼운 무게 권장")
                else:
                    st.write("해당 회원이 없습니다.")

            day4_members = df_main[df_main['cumulative_checkins'] >= 4]
            with st.expander("💰 [골든 타임] 전환 임박 우수 출석자 (만족도 확인 및 세일즈)", expanded=True):
                if not day4_members.empty:
                    for _, row in day4_members.iterrows():
                        st.write(f"**{row['name']} 회원님** (누적 {int(row['cumulative_checkins'])}회 출석)")
                        st.caption("👉 Action: 수업 직후 운동 만족도 질문, 당일 등록 시 할인 혜택 안내 (매니저 인계)")
                else:
                    st.write("해당 회원이 없습니다.")

        with col2:
            st.subheader("🚨 이탈(Ghosting) 위험 알림")
            st.info("빠른 컨택으로 환불/이탈을 방어하세요.")
            
            canceled_members = df_main[df_main['canceled_today'] == True]
            if not canceled_members.empty:
                st.error("⚠️ 당일 예약 취소 발생")
                for _, row in canceled_members.iterrows():
                    st.write(f"- **{row['name']} 회원님** (누적 {int(row['cumulative_checkins'])}회 출석)")
                    st.caption("💌 Action: '오늘 못 오셔서 아쉬워요! 내일 예약 도와드릴까요?' 카톡 발송")
            else:
                st.write("오늘 발생한 취소 건이 없습니다. 👍")
                
    except Exception as e:
        # 파일 형식이 맞지 않거나 에러가 났을 때 처리
        st.error("데이터를 처리하는 중 오류가 발생했습니다. CSV 파일의 컬럼명을 확인해주세요.")
        st.write("발생한 에러:", e)

else:
    # 파일이 업로드되지 않았을 때 보여주는 안내 화면
    st.info("👈 왼쪽 사이드바에서 Glofox 회원 명부와 출석 리포트 CSV 파일을 업로드해주세요.")
    st.markdown("""
    **💡 필수 컬럼 안내**
    업로드할 CSV 파일은 반드시 아래 영문 컬럼명을 포함해야 합니다.
    * **회원 명부 (members.csv):** `member_id` (회원번호), `name` (이름), `trial_start_date` (체험시작일, YYYY-MM-DD)
    * **출석 리포트 (attendance.csv):** `member_id` (회원번호), `date` (수업일자, YYYY-MM-DD), `status` (출석상태: Attended, Canceled 등)
    """)