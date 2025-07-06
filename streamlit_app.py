import streamlit as st
import pandas as pd
import numpy as np
import openpyxl
import math
import os

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
## 임대주택 공고 뷰어
* HUG, LH, SH에 올라온 공고 중 확인했던 공고를 지도까지 손쉽게 확인하기 위해 제작했습니다.
""" 
)

st.divider()

@st.cache_data
def get_file_list():
    file_list = os.listdir('source/')
    return file_list

file_list = get_file_list()
file_name = st.selectbox('파일 선택', options=file_list)


# 파일 컬럼: 시도, 시군구, 주소, 전용면적, 주택유형, 주택구조(방수), 
@st.cache_data
def load_data(file_name):
    if '.csv' in file_name:
        df = pd.read_csv(f'source/{file_name}')
    elif '.xls' in file_name or '.xlsx' in file_name:
        df = pd.read_excel(f'source/{file_name}')
    else:
        st.error('지원하지 않는 파일 형식입니다.')
        return None

    df['주소'] = df['주소'].astype(str).str.strip()
    df['보증금'] = df['보증금'].astype(str).str.replace(',', '').str.replace('"', '').astype(np.int64)
    df['월임대료'] = df['월임대료'].astype(str).str.replace(',', '').str.replace('"', '').astype(np.int64)
    df['전용면적'] = df['전용면적'].astype(float)
    df['네이버지도'] = df['주소'].apply(lambda x: f'https://map.naver.com/p/search/{x}')
    return df.sort_values(by=['시도','시군구','주소'])

df = load_data(file_name)

st.header('필터')
col1, col2, col3 = st.columns(3, gap='medium')
with col1:
    시도 = st.selectbox('시도', options=['전체']+sorted(df['시도'].unique().tolist()), index=0)
    시도 = df['시도'].unique() if 시도 == '전체' else [시도]
    시군구 = st.selectbox('시군구', options=['전체']+sorted(df[df['시도'].isin(시도)]['시군구'].unique().tolist()), index=0)
    시군구 = df[df['시도'].isin(시도)]['시군구'].unique() if 시군구 == '전체' else [시군구]

with col2:
    주택유형_list = df['주택유형'].unique().tolist()
    if len(주택유형_list) == 1:
        주택유형 = 주택유형_list
    else:
        주택유형 = st.multiselect('주택유형', options=sorted(주택유형_list), default=sorted(주택유형_list))

    주택구조_list = df['주택구조(방수)'].unique().tolist()
    if len(주택구조_list) == 1:
        주택구조 = 주택구조_list
    else:
        주택구조 = st.multiselect('주택구조(방수)', options=sorted(주택구조_list), default=sorted(주택구조_list))

with col3:
    min_area, max_area = float(math.floor(df['전용면적'].min())), float(math.ceil(df['전용면적'].max()))
    area_range = st.slider('전용면적 범위', min_value=min_area, max_value=max_area, value=(min_area, max_area), step=0.1)
    min_deposit, max_deposit = math.floor(int(df['보증금'].min())/10000000)*10000000, math.ceil(int(df['보증금'].max())/10000000)*10000000
    deposit_range = st.slider('보증금 범위(원)', min_value=min_deposit, max_value=max_deposit, value=(min_deposit, max_deposit), step=10000000)

st.divider()

show_cols = [
    '시도', '시군구', '주소', '주택유형', '주택구조(방수)',
    '전용면적', '보증금', '월임대료', '네이버지도'
]
filtered_df = df[
    df['시도'].isin(시도) &
    df['시군구'].isin(시군구) &
    df['주택유형'].isin(주택유형) &
    df['주택구조(방수)'].isin(주택구조) &
    (df['전용면적'] >= area_range[0]) & (df['전용면적'] <= area_range[1]) &
    (df['보증금'] >= deposit_range[0]) & (df['보증금'] <= deposit_range[1])
][show_cols]

for col in show_cols:
    if len(filtered_df[col].unique()) == 1:
        filtered_df.drop(columns=[col], inplace=True)
        show_cols.remove(col)

filter_toggle = st.toggle('주소 중복제거')
if filter_toggle:
    filter_columns = [col for col in ['시도','시군구','주소','주택유형','주택구조(방수)'] if col in filtered_df.columns]
    filter_values = [col for col in ['전용면적','보증금','월임대료'] if col in filtered_df.columns]

    filtered_df_grouped_count = filtered_df.groupby(filter_columns).agg({filter_values[0]: 'count'}).reset_index()
    filtered_df_grouped_count.rename(columns={filter_values[0]: '주택수'}, inplace=True)

    filtered_df_grouped_min = filtered_df.groupby(filter_columns).agg({col: 'min' for col in filter_values}).reset_index()
    filtered_df_grouped_max = filtered_df.groupby(filter_columns).agg({col: 'max' for col in filter_values}).reset_index()
    filtered_df_grouped_merged = filtered_df_grouped_count.merge(filtered_df_grouped_min, on=filter_columns, how='left').merge(filtered_df_grouped_max, on=filter_columns, how='left')

    for value in filter_values:
        filtered_df_grouped_merged[value] = filtered_df_grouped_merged.apply(lambda x: f'{x[f"{value}_x"]} ~ {x[f"{value}_y"]}' if x[f"{value}_x"] != x[f"{value}_y"] else f'{x[f"{value}_x"]}', axis=1)
        filtered_df_grouped_merged.drop(columns={f'{value}_x',f'{value}_y'}, inplace=True)
    filtered_df_grouped_merged['네이버지도'] = filtered_df_grouped_merged['주소'].apply(lambda x: f'https://map.naver.com/p/search/{x}')

    filtered_df = filtered_df_grouped_merged.copy()

st.write('### 주택 리스트 조회 (총 {}건)'.format(len(filtered_df)))
st.data_editor(
    filtered_df,
    column_config={
        '네이버지도': st.column_config.LinkColumn('네이버지도', display_text='지도로 보기'),
    },
    hide_index=True,
    use_container_width=True,
)