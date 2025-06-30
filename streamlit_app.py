import streamlit as st
import pandas as pd
import numpy as np
import requests
import math

st.set_page_config(
    page_title="HUG 든든전세주택 뷰어",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="collapsed",
)

with st.sidebar:
    st.write(
        """
    ### 연락처
    📞 Tel. 010-4430-2279  
    📩 E-mail. [gnsu0705@gmail.com](gnsu0705@gmail.com)  
    💻 Blog. [Super-Son](https://super-son.tistory.com)  
    """
    )

st.write(
    """
## HUG 든든전세주택 뷰어
HUG 든든전세주택 리스트를 확인하는게 불편해서 직접 만들었습니다.
* 데이터 출처: [안심전세포털](https://www.khug.or.kr/jeonse/web/s07/s070102.jsp)
* 신청자 수 업데이트는 아직 미구현
* 협의매입형은 '소유자와의 협의를 통해 매입하는' 유형입니다. (임대의무기간(최초 임대개시일로부터 5년) 이후 임대인이 변경될 수 있음)
""" 
)

st.divider()

@st.cache_data
def load_data():
    df = pd.read_csv('rent_house_list.csv')
    df['임대보증금액'] = df['임대보증금액'].astype(str).str.replace(',', '').str.replace('"', '').astype(np.int64)
    df['전용면적(m2)'] = df['전용면적(m2)'].astype(float)
    return df

df = load_data()


st.header('필터')
col1, col2, col3 = st.columns(3, gap='medium')
with col1:
    시도 = st.selectbox('시도', options=['전체']+sorted(df['시도'].unique().tolist()), index=0)
    시도 = df['시도'].unique() if 시도 == '전체' else [시도]
    시군구 = st.selectbox('시군구', options=['전체']+sorted(df[df['시도'].isin(시도)]['시군구'].unique().tolist()), index=0)
    시군구 = df[df['시도'].isin(시도)]['시군구'].unique() if 시군구 == '전체' else [시군구]

with col2:
    주택유형 = st.multiselect('주택유형', options=sorted(df['주택유형'].unique().tolist()), default=sorted(df['주택유형'].unique().tolist()))
    매입유형 = st.multiselect('매입유형', options=sorted(df['매입유형'].unique().tolist()), default=sorted(df['매입유형'].unique().tolist()))

with col3:
    min_area, max_area = float(math.floor(df['전용면적(m2)'].min())), float(math.ceil(df['전용면적(m2)'].max()))
    area_range = st.slider('전용면적(m2) 범위', min_value=min_area, max_value=max_area, value=(min_area, max_area), step=0.1)
    min_deposit, max_deposit = math.floor(int(df['임대보증금액'].min())/10000000)*10000000, math.ceil(int(df['임대보증금액'].max())/10000000)*10000000
    deposit_range = st.slider('임대보증금액 범위(원)', min_value=min_deposit, max_value=max_deposit, value=(min_deposit, max_deposit), step=10000000)

st.divider()

filtered_df = df[
    df['시도'].isin(시도) &
    df['시군구'].isin(시군구) &
    df['주택유형'].isin(주택유형) &
    df['매입유형'].isin(매입유형) &
    (df['전용면적(m2)'] >= area_range[0]) & (df['전용면적(m2)'] <= area_range[1]) &
    (df['임대보증금액'] >= deposit_range[0]) & (df['임대보증금액'] <= deposit_range[1])
]

# 표에 하이퍼링크 컬럼 추가 및 숫자 포맷 컬럼 생성
filtered_df = filtered_df.copy()
filtered_df['전용면적(㎡)'] = filtered_df['전용면적(m2)'].apply(lambda x: f"{x:.1f} ㎡")
filtered_df['안심전세포털'] = filtered_df['안심전세포털']
filtered_df['네이버지도'] = filtered_df['네이버지도']

show_cols = [
    '시도', '시군구', '주소', '주택유형', '매입유형',
    '전용면적(㎡)', '임대보증금액', '안심전세포털', '네이버지도'
]

st.write('### 주택 리스트 조회 (총 {}건)'.format(len(filtered_df)))
st.data_editor(
    filtered_df[show_cols],
    column_config={
        '안심전세포털': st.column_config.LinkColumn('안심전세포털', display_text='공고 바로가기'),
        '네이버지도': st.column_config.LinkColumn('네이버지도', display_text='지도로 보기'),
    },
    hide_index=True,
    use_container_width=True,
)

