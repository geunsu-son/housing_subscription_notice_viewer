import streamlit as st
import pandas as pd
import numpy as np
import openpyxl
import math
import os

st.set_page_config(
    page_title="청약 공고 뷰어",
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
### 청약 공고 뷰어
HUG, LH, SH에 올라온 청약 공고 중 확인했던 공고를 지도까지 손쉽게 확인하기 위해 제작했습니다.
""" 
)

st.divider()

@st.cache_data
def get_file_df():
    file_dict = os.listdir('source/')
    dataframe = pd.DataFrame(columns=['연도','주택공사','청약 공고','파일명'])
    for file in file_dict:
        year = file.split('.')[0]
        dataframe.loc[len(dataframe)] = [year, file.split(' ')[1], ' '.join(file.split(' ')[2:]), file]
    return dataframe

file_df = get_file_df()
page_col1, page_col2 = st.columns([0.25,0.75], gap='medium')
with page_col1:
    st.warning('##### 청약 공고 조회')
    year = st.selectbox('연도', options=file_df['연도'].unique().tolist())
    if file_df[file_df['연도'] == year].empty:
        st.error('해당 연도의 청약 공고가 없습니다.')
        st.stop()
    else:
        company_name = st.selectbox('주택공사', options=file_df[file_df['연도'] == year]['주택공사'].unique().tolist())
    notice_name = st.selectbox('청약 공고', options=file_df[(file_df['연도'] == year) & (file_df['주택공사'] == company_name)]['청약 공고'].unique().tolist())

    file_name = file_df[(file_df['연도'] == year) & (file_df['주택공사'] == company_name) & (file_df['청약 공고'] == notice_name)]['파일명'].values[0]


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
    if '월임대료' in df.columns:
        df['월임대료'] = df['월임대료'].astype(str).str.replace(',', '').str.replace('"', '').astype(np.int64)
    df['전용면적'] = df['전용면적'].astype(float)
    df['네이버지도'] = df['주소'].apply(lambda x: f'https://map.naver.com/p/search/{x}')

    if '공급계' in df.columns:
        show_cols = ['공급구분','시도','시군구','주소','단지명', '공급구분1','공급구분2','공급계','공급_우선','공급_일반','공급_예비']
        filter_cols = ['공급구분1','공급구분2']
    elif '매입유형' in df.columns:
        show_cols = [col for col in ['시도','시군구', '주택명','주소', '주택유형', '매입유형','안심전세포털'] if col in df.columns]
        filter_cols = ['주택유형','매입유형']
    else:
        show_cols = [col for col in ['시도','시군구','주택명','주택군','주소','주택유형', '주택구조(방수)'] if col in df.columns]
        filter_cols = ['주택유형','주택구조(방수)']
    
    show_cols = show_cols + [col for col in ['전용면적', '보증금', '월임대료', '네이버지도'] if col in df.columns]
    
    return df.sort_values(by=['시도','시군구','주소']), show_cols, filter_cols

df, show_cols, filter_cols = load_data(file_name)

with page_col2:
    st.error('##### 필터')
    col1, col2, col3 = st.columns(3, gap='medium')
    with col1:
        시도 = st.selectbox('시도', options=['전체']+sorted(df['시도'].unique().tolist()), index=0)
        시도 = df['시도'].unique() if 시도 == '전체' else [시도]
        시군구 = st.selectbox('시군구', options=['전체']+sorted(df[df['시도'].isin(시도)]['시군구'].unique().tolist()), index=0)
        시군구 = df[df['시도'].isin(시도)]['시군구'].unique() if 시군구 == '전체' else [시군구]

    with col2:
        filter_col1_list = df[filter_cols[0]].unique().tolist()
        if len(filter_col1_list) == 1:
            filter_col1 = filter_col1_list
        else:
            filter_col1 = st.multiselect(filter_cols[0], options=sorted(filter_col1_list), default=sorted(filter_col1_list))

        filter_col2_list = df[filter_cols[1]].unique().tolist()
        if len(filter_col2_list) == 1:
            filter_col2 = filter_col2_list
        else:
            filter_col2 = st.multiselect(filter_cols[1], options=sorted(filter_col2_list), default=sorted(filter_col2_list))

    with col3:
        min_area, max_area = float(math.floor(df['전용면적'].min())), float(math.ceil(df['전용면적'].max()))
        area_range = st.slider('전용면적 범위', min_value=min_area, max_value=max_area, value=(min_area, max_area), step=0.1)
        min_deposit, max_deposit = math.floor(int(df['보증금'].min())/10000000)*10000000, math.ceil(int(df['보증금'].max())/10000000)*10000000
        deposit_range = st.slider('보증금 범위(원)', min_value=min_deposit, max_value=max_deposit, value=(min_deposit, max_deposit), step=10000000)

st.divider()


filtered_df = df[
    df['시도'].isin(시도) &
    df['시군구'].isin(시군구) &
    df[filter_cols[0]].isin(filter_col1) &
    df[filter_cols[1]].isin(filter_col2) &
    (df['전용면적'] >= area_range[0]) & (df['전용면적'] <= area_range[1]) &
    (df['보증금'] >= deposit_range[0]) & (df['보증금'] <= deposit_range[1])
][show_cols]


filtered_df['전용면적(평)'] = filtered_df['전용면적'].apply(lambda x: f'{int(x/3.305785)}평' if x % 3.305785 == 0 else f'{x/3.305785:.1f}평')
filtered_df['보증금(억원)'] = filtered_df['보증금'].apply(lambda x: f'{str(int(x/100000000))+'억' if x >= 100000000 else ''}{' '+str(int(x/10000%10000))+'만원' if int(x/10000%10000) > 0 else '원'}') 
add_show_cols = ['전용면적(평)','보증금(억원)','월임대료(만원)','네이버지도'] if '월임대료' in filtered_df.columns else ['전용면적(평)','보증금(억원)','네이버지도']
if '월임대료' in filtered_df.columns:
    filtered_df['월임대료(만원)'] = filtered_df['월임대료'].apply(lambda x: f'{str(int(x/10000))+'만' if x >= 10000 else ''}{' '+str(int(x%10000))+'원' if int(x%10000) > 0 else '원'}') 
filtered_df = filtered_df[show_cols[:-1]+add_show_cols]

for col in show_cols:
    if len(filtered_df[col].unique()) == 1:
        filtered_df.drop(columns=[col], inplace=True)
        show_cols.remove(col)

filter_toggle = st.toggle('주소 중복제거')
if filter_toggle:
    filter_columns = [col for col in ['시도','시군구','주소','주택명']+filter_cols if col in filtered_df.columns]
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

config_dict = {
    '네이버지도': st.column_config.LinkColumn('네이버지도', display_text='지도로 보기'),
}
if '안심전세포털' in filtered_df.columns:
    config_dict['안심전세포털'] = st.column_config.LinkColumn('안심전세포털', display_text='안심전세포털로 보기')

st.data_editor(
    filtered_df,
    column_config=config_dict,
    hide_index=True,
    use_container_width=True,
)