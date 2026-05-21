import streamlit as st
import pandas as pd
import re
import io
from datetime import date
from PIL import Image  # 💡 이미지를 불러오기 위한 부품 추가!

# ==========================================
# 0. 로고 및 페이지 기본 설정
# ==========================================
# 깃허브에 올린 이미지 파일 이름 (예: f45_logo.png)
logo_img = Image.open("C:/Users/Seongmin Kim/Downloads/F45 Project/F45_Logo.jpg")

# 1) 웹 브라우저 맨 위 '탭'에 뜨는 아이콘을 로고로 변경
st.set_page_config(page_title="F45 Trial Onboarding", page_icon=logo_img, layout="wide")

# 2) 메인 화면에 대문짝만하게 로고 띄우기 (width로 크기 조절 가능)
st.image(logo_img, width=150) 
st.title("F45 트라이얼 온보딩 대시보드")
st.markdown("트라이얼 관리 파일(엑셀/CSV)을 업로드하거나, 카톡 줄글을 복붙하세요.")
st.divider()

# ==========================================
# 1. 사이드바: 듀얼 입력 (파일 & 복붙)
# ==========================================
st.sidebar.header("📁 데이터 입력 (택 1)")
uploaded_file = st.sidebar.file_uploader("1. 파일 업로드 (XLSX, CSV)", type=['xlsx', 'csv'])

st.sidebar.markdown("**또는**")

pasted_text = st.sidebar.text_area("2. 내용 복붙하기 (Ctrl+V)", height=150, 
                                   placeholder="스프레드시트 표 내용이나 카톡 줄글을 여기에 붙여넣으세요.")

st.sidebar.divider()
st.sidebar.markdown("⚙️ **설정**")
reference_date = st.sidebar.date_input("현재 날짜(오늘) 설정", date.today())
st.sidebar.caption("※ 이 날짜를 기준으로 체험 경과일 및 '기간 만료' 여부를 계산합니다.")

# ==========================================
# 2. 데이터 처리 및 인공지능 파싱 로직
# ==========================================
df = None

try:
    if uploaded_file is not None:
        # 💡 [파일 업로드 모드]
        if uploaded_file.name.endswith('.xlsx'):
            df_temp = pd.read_excel(uploaded_file)
        else:
            df_temp = pd.read_csv(uploaded_file)
            
        if '이름' not in df_temp.columns:
            mask = df_temp.astype(str).apply(lambda x: (x.str.strip() == '이름').any(), axis=1)
            if mask.any():
                header_idx = mask.idxmax()
                df_temp.columns = df_temp.iloc[header_idx].values
                df_temp = df_temp.iloc[header_idx + 1:].reset_index(drop=True)
                
        df_temp.columns = df_temp.columns.astype(str).str.strip()
        df = df_temp

    elif pasted_text:
        # 💡 [복붙 모드: 표 형식 처리]
        if '\t' in pasted_text:
            df_temp = pd.read_csv(io.StringIO(pasted_text), sep='\t', header=None, dtype=str)
            df_temp = df_temp.dropna(how='all')
            
            mask = df_temp.astype(str).apply(lambda x: (x.str.strip() == '이름').any(), axis=1)
            if mask.any():
                header_idx = mask.idxmax()
                df_temp.columns = df_temp.iloc[header_idx].values
                df_temp = df_temp.iloc[header_idx + 1:].reset_index(drop=True)
            else:
                # 💡 핵심 해결: 날짜가 몇 번째 칸에 있는지 완벽하게 역추적
                standard_cols = ['이름', '전화번호', 'Trial 시작 일자', '종료 날짜', '멤버쉽등록', '유입트라이얼', '전환률(T-M)', '1', '2', '3', '4', '5', '6', '특이 사항', '인적 사항& 등록 여부']
                
                # '202X' 연도가 포함된 열 인덱스 찾기
                date_cols = [c for c in df_temp.columns if df_temp[c].astype(str).str.contains(r'202\d').any()]
                
                # 만약 날짜가 4번째 칸(index 3)부터 시작한다면 '프로모션' 칸이 맨 앞에 있는 것
                if date_cols and date_cols[0] == 3:
                    standard_cols = ['프로모션'] + standard_cols
                
                # 모자란 칸 채워넣기 (에러 방지)
                if df_temp.shape[1] > len(standard_cols):
                    for i in range(len(standard_cols), df_temp.shape[1]):
                        standard_cols.append(f"추가_{i}")
                        
                df_temp.columns = standard_cols[:df_temp.shape[1]]
            
            df_temp.columns = df_temp.columns.astype(str).str.strip()
            df = df_temp
            
        else:
            # 💡 [복붙 모드: 카톡 줄글 형식 처리] (띄어쓰기 파괴자 완벽 방어)
            raw_text = pasted_text.replace('\n', ' ')
            raw_text = re.sub(r'(\d)(202\d\s*[./-])', r'\1 \2', raw_text)
            
            anchor_pattern = r"((?:010|10)[-.\s]?\d{3,4}[-.\s]?\d{4})?\s*(202\d\s*[./-]\s*\d{1,2}\s*[./-]\s*\d{1,2})\s*(202\d\s*[./-]\s*\d{1,2}\s*[./-]\s*\d{1,2})"
            anchors = list(re.finditer(anchor_pattern, raw_text))
            
            extracted_data = []
            if anchors:
                for i in range(len(anchors)):
                    start_date = anchors[i].group(2)
                    end_date = anchors[i].group(3)
                    
                    if i == 0:
                        prev_text = raw_text[:anchors[0].start()].strip()
                    else:
                        prev_text = raw_text[anchors[i-1].end():anchors[i].start()].strip()
                        
                    name_match = re.search(r'([가-힣]+)$', prev_text)
                    if name_match:
                        name = name_match.group(1)[-3:] if len(name_match.group(1)) >= 3 else name_match.group(1)
                        if i > 0:
                            extracted_data[i-1]['특이 사항'] = prev_text[:-len(name)].strip()
                    else:
                        name = prev_text[-3:] if len(prev_text) >= 3 else prev_text
                        if i > 0:
                            extracted_data[i-1]['특이 사항'] = prev_text[:-len(name)].strip()
                            
                    def clean_date(d_str):
                        nums = re.findall(r'\d+', d_str)
                        if len(nums) >= 3:
                            return f"{nums[0]}-{nums[1]}-{nums[2]}"
                        return None
                        
                    extracted_data.append({
                        '이름': name,
                        'Trial 시작 일자': clean_date(start_date),
                        '종료 날짜': clean_date(end_date),
                        '특이 사항': '',
                        '인적 사항& 등록 여부': '없음',
                    })
                
                extracted_data[-1]['특이 사항'] = raw_text[anchors[-1].end():].strip()
                
                for i in range(len(extracted_data)):
                    notes = extracted_data[i]['특이 사항']
                    attendance_match = re.match(r'^([OXoxㅇ0\s]+)', notes)
                    checkins = 0
                    if attendance_match:
                        ox_str = attendance_match.group(1).upper()
                        checkins = ox_str.count('O') + ox_str.count('ㅇ') + ox_str.count('0')
                        notes = notes[len(attendance_match.group(1)):].strip()
                        
                    notes = re.sub(r'^[/,-]\s*', '', notes).strip()
                    extracted_data[i]['특이 사항'] = notes
                    
                    for j in range(1, 7):
                        extracted_data[i][str(j)] = 'O' if j <= checkins else ''
                        
                df = pd.DataFrame(extracted_data)
            else:
                st.sidebar.error("텍스트에서 회원 정보를 찾지 못했습니다.")

except Exception as e:
    st.sidebar.error(f"데이터를 읽는 중 오류가 발생했습니다. (에러: {e})")

# ==========================================
# 3. 데이터 가공 및 화면 구성
# ==========================================
if df is not None and not df.empty:
    try:
        cols = df.columns.tolist()
        start_col = next((c for c in cols if '시작' in c), 'Trial 시작 일자')
        end_col = next((c for c in cols if '종료' in c), '종료 날짜')
        note_col = next((c for c in cols if '특이' in c), '특이 사항')
        info_col = next((c for c in cols if '인적' in c or '등록 여부' in c), '인적 사항& 등록 여부')
        
        # [출석 계산]
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
            
        if checkin_cols:
            df[['cumulative_checkins', 'max_consecutive']] = df.apply(calculate_attendance, axis=1)
        else:
            df['cumulative_checkins'] = 0
            df['max_consecutive'] = 0
            
        # 💡 [비교 오류 차단 및 공백 무시]
        def parse_robust_date(val):
            if pd.isna(val): return pd.NaT
            if isinstance(val, (pd.Timestamp, date)): return pd.to_datetime(val)
            val_str = str(val).strip()
            match = re.search(r'(202\d)[-.\s]+(\d{1,2})[-.\s]+(\d{1,2})', val_str)
            if match:
                return pd.to_datetime(f"{match.group(1)}-{match.group(2)}-{match.group(3)}")
            return pd.to_datetime(val_str, errors='coerce')
        
        df[start_col] = df[start_col].apply(parse_robust_date)
        df[end_col] = df[end_col].apply(parse_robust_date)
        
        ref_dt = pd.to_datetime(reference_date)
        
        initial_count = len(df)
        df = df.dropna(subset=[start_col, end_col])
        missing_date_count = initial_count - len(df)
        
        current_count = len(df)
        df = df[df[end_col] >= ref_dt]
        expired_count = current_count - len(df)
        
        df['체험_경과일'] = (ref_dt - df[start_col]).dt.days + 1
        
        df[note_col] = df[note_col].fillna("없음")
        if info_col in df.columns:
            df[info_col] = df[info_col].fillna("없음")
        else:
            df[info_col] = "없음"

        st.success(f"🎉 데이터 분석 완료! 총 **{len(df)}명**의 타겟 회원을 찾았습니다.\n\n"
                   f"*(날짜 누락자 {missing_date_count}명, 기간 만료자 {expired_count}명 제외됨)*")
        
        col1, col2 = st.columns([2, 1])

        with col1:
            st.subheader("🔥 오늘의 트라이얼 집중 케어 타겟")
            
            is_newbie = (df['체험_경과일'] <= 1)
            day1_members = df[is_newbie]
            
            with st.expander("🟢 [Day 1] 뉴비", expanded=True):
                if not day1_members.empty:
                    for _, row in day1_members.iterrows():
                        시작일_표시 = row[start_col].strftime("%m/%d") if pd.notnull(row[start_col]) else "알수없음"
                        st.write(f"**{row['이름']} 회원님** (시작일: {시작일_표시} ➡️ **{int(row['체험_경과일'])}일 차**)")
                        st.write(f"🏃 출석 현황: 누적 {int(row['cumulative_checkins'])}회 / 연속 {int(row['max_consecutive'])}회")
                        
                        if row[note_col] and str(row[note_col]).strip() not in ["없음", "nan", ""]:
                            st.warning(f"⚠️ 코치 메모: {row[note_col]}")
                            
                        if row[info_col] and str(row[info_col]).strip() not in ["없음", "nan", ""]:
                            st.caption(f"📝 인적 사항: {row[info_col]}")
                        st.divider()
                else:
                    st.write("해당 회원이 없습니다.")

            is_adaptation = (df['체험_경과일'] >= 2) & (df['체험_경과일'] <= 4)
            day24_members = df[is_adaptation]
            
            with st.expander("🟡 [Day 2~4] 적응기", expanded=True):
                if not day24_members.empty:
                    for _, row in day24_members.iterrows():
                        시작일_표시 = row[start_col].strftime("%m/%d") if pd.notnull(row[start_col]) else "알수없음"
                        st.write(f"**{row['이름']} 회원님** (시작일: {시작일_표시} ➡️ **{int(row['체험_경과일'])}일 차**)")
                        st.write(f"🏃 출석 현황: 누적 {int(row['cumulative_checkins'])}회 / 연속 {int(row['max_consecutive'])}회")
                        
                        if row[note_col] and str(row[note_col]).strip() not in ["없음", "nan", ""]:
                            st.warning(f"⚠️ 코치 메모: {row[note_col]}")
                            
                        if row[info_col] and str(row[info_col]).strip() not in ["없음", "nan", ""]:
                            st.caption(f"📝 인적 사항: {row[info_col]}")
                        st.divider()
                else:
                    st.write("해당 회원이 없습니다.")

            is_golden_time = (df['체험_경과일'] >= 5)
            day_golden_members = df[is_golden_time]
            
            with st.expander("💰 [Day 5~6] 전환 임박", expanded=True):
                if not day_golden_members.empty:
                    for _, row in day_golden_members.iterrows():
                        시작일_표시 = row[start_col].strftime("%m/%d") if pd.notnull(row[start_col]) else "알수없음"
                        st.success(f"**{row['이름']} 회원님** (시작일: {시작일_표시} ➡️ **{int(row['체험_경과일'])}일 차**)")
                        st.write(f"🏃 출석 현황: 누적 {int(row['cumulative_checkins'])}회 / 연속 {int(row['max_consecutive'])}회")
                        
                        if row[note_col] and str(row[note_col]).strip() not in ["없음", "nan", ""]:
                            st.warning(f"⚠️ 코치 메모: {row[note_col]}")
                            
                        if row[info_col] and str(row[info_col]).strip() not in ["없음", "nan", ""]:
                            st.caption(f"📝 인적 사항: {row[info_col]}")
                        st.divider()
                else:
                    st.write("해당 회원이 없습니다.")

        with col2:
            st.subheader("🚨 리스크 관리")
            risk_condition = (df['cumulative_checkins'] <= 1) & (df['체험_경과일'] >= 3)
            risk_members = df[risk_condition]
            
            if not risk_members.empty:
                st.error("⚠️ 장기 미출석 (이탈 위험)")
                for _, row in risk_members.iterrows():
                    st.write(f"- **{row['이름']} 회원님** (현재 {int(row['체험_경과일'])}일 차 / 출석 {int(row['cumulative_checkins'])}회)")
                    
                    if row[note_col] and str(row[note_col]).strip() not in ["없음", "nan", ""]:
                        st.warning(f"⚠️ 코치 메모: {row[note_col]}")
                    
                    if row[info_col] and str(row[info_col]).strip() not in ["없음", "nan", ""]:
                        st.caption(f"📝 인적 사항: {row[info_col]}")
                        
                    st.divider()
            else:
                st.info("현재 파악된 이탈 위험군이 없습니다. 👍")

    except Exception as e:
        st.error(f"데이터를 표시하는 중 오류가 발생했습니다: {e}")
else:
    if uploaded_file is None and not pasted_text:
        st.info("👈 왼쪽 사이드바에 엑셀/CSV 파일을 업로드하거나 줄글을 복붙해주세요.")
