import yfinance as yf
import pandas as pd
import streamlit as st
import plotly.graph_objs as go
import requests as res
import io
import folium
from streamlit_folium import folium_static
from geopy.geocoders import Nominatim

# 獲取公司基本資訊
def company_info(symbol):
    try:
        stock_info = yf.Ticker(symbol)
        com_info = stock_info.info
        return com_info
    except Exception as e:
        st.error(f"無法獲取公司基本資訊：{str(e)}")
        return None
     
def display_location(com_info):
    if 'city' in com_info and 'country' in com_info:
        city = com_info['city']
        country = com_info['country']

        # 使用 Nominatim 服务进行地理编码
        geolocator = Nominatim(user_agent="streamlit_app")
        location = geolocator.geocode(f"{city}, {country}")

        if location:
            # 使用 folium 创建地图，并将其定位到公司位置
            map = folium.Map(location=[location.latitude, location.longitude], zoom_start=10)
            # 添加标记
            folium.Marker([location.latitude, location.longitude], popup=f"{city}, {country}").add_to(map)
            # 使用 streamlit-folium 显示地图
            folium_static(map)
        else:
            st.error("無法找到公司位置")
    else:
        st.error("缺少城市或國家")

def display_info(com_info):
    if com_info:
        
        selected_indicators = ['longName', 'country', 'city', 'marketCap', 'totalRevenue', 'grossMargins', 'operatingMargins',
                               'profitMargins', 'trailingEps', 'pegRatio', 'dividendRate', 'payoutRatio', 'bookValue',
                               'operatingCashflow', 'freeCashflow', 'returnOnEquity']

        selected_info = {indicator: com_info.get(indicator, '') for indicator in selected_indicators}

        #建立字典翻譯
        translation = {
            'longName': '公司名稱',
            'country': '國家',
            'city': '城市',
            'marketCap': '市值',
            'totalRevenue': '總收入',
            'grossMargins': '毛利率',
            'operatingMargins': '營業利潤率', 
            'profitMargins': '净利率',
            'trailingEps': '每股收益',
            'pegRatio': 'PEG 比率',
            'dividendRate': '股息率',
            'payoutRatio': '股息支付比例',
            'bookValue': '每股淨資產',
            'operatingCashflow': '營運現金流',
            'freeCashflow': '自由現金流',
            'returnOnEquity': '股東權益報酬率'
        }

        #Pandas DataFrame
        company_info = pd.DataFrame.from_dict(selected_info,orient='index',columns=['Value'])
        company_info.rename(index=translation,inplace=True)

        #轉換成百分比
        percent_columns = ['毛利率', '營業利潤率', '净利率', '股息率', '股息支付比例', '股東權益報酬率']
        for col in percent_columns:
            if col in company_info.index:
                company_info.at[col, 'Value'] = pd.to_numeric(company_info.at[col, 'Value'], errors='coerce')  # 将非数字转换为 NaN
                company_info.at[col, 'Value'] = f"{company_info.at[col, 'Value']:.2%}" if pd.notna(company_info.at[col, 'Value']) else None

        #千分位表示
        company_info['Value'] = company_info['Value'].apply(lambda x: "{:,.0f}".format(x) if isinstance(x, (int, float)) and x >= 1000 else x)
        st.subheader("公司基本資訊:")
        st.table(company_info)
        st.subheader("公司位置資訊:")
        display_location(com_info)
    else:
        st.error(f" {symbol} 公司的基本訊息")


#獲取歷史交易數據
def stock_data(symbol,start_date,end_date):
    try:
        stock_data = yf.download(symbol,start=start_date,end=end_date)
        st.write("交易數據:", stock_data)
        return stock_data
    except Exception as e:
        st.error(f"無法獲取交易數據：{str(e)}")
        return None

#繪製k線圖
def plot_candle(stock_data, mav_days):
    fig = go.Figure(data=[go.Candlestick(x=stock_data.index,
                                         open=stock_data['Open'],
                                         high=stock_data['High'],
                                         low=stock_data['Low'],
                                         close=stock_data['Close'])])
    # 計算mav
    mav5 = stock_data['Close'].rolling(window=5).mean()  # 5日mav
    mav10 = stock_data['Close'].rolling(window=10).mean()  # 10日mav
    mav15 = stock_data['Close'].rolling(window=15).mean()  # 10日mav
    mav = stock_data['Close'].rolling(window=mav_days).mean()  # mav_days日mav
    
    # 添加mav
    fig.add_trace(go.Scatter(x=stock_data.index, y=mav5, mode='lines', name='MAV-5'))
    fig.add_trace(go.Scatter(x=stock_data.index, y=mav10, mode='lines', name='MAV-10'))
    fig.add_trace(go.Scatter(x=stock_data.index, y=mav15, mode='lines', name='MAV-15'))
    fig.add_trace(go.Scatter(x=stock_data.index, y=mav, mode='lines', name=f'MAV-{mav_days}'))
    
    fig.update_layout(xaxis_rangeslider_visible=False, xaxis_title='日期', yaxis_title='價格',title='K線圖')
    st.plotly_chart(fig, use_container_width=True)

#繪製趨勢圖
def plot_trend(stock_data):
    fig = go.Figure()

    # 收盤價線
    fig.add_trace(go.Scatter(x=stock_data.index, y=stock_data['Close'], mode='lines', name='收盤價'))

    # 最高價線
    fig.add_trace(go.Scatter(x=stock_data.index, y=stock_data['High'], mode='lines', name='最高價'))

    # 最低價線
    fig.add_trace(go.Scatter(x=stock_data.index, y=stock_data['Low'], mode='lines', name='最低價'))

    # 更新佈局
    fig.update_layout(xaxis_title='日期', yaxis_title='', title='趨勢圖')

    # 顯示圖表
    st.plotly_chart(fig, use_container_width=True)

#繪製交易量柱狀圖
def plot_volume(stock_data):
    fig = go.Figure(data=[go.Bar(x=stock_data.index, y=stock_data['Volume'])])
    fig.update_layout(xaxis_title='日期', yaxis_title='交易量', title='交易量柱狀圖')
    st.plotly_chart(fig, use_container_width=True)

#財報
def financial_statements(symbol):
    try:
        stock_info = yf.Ticker(symbol)
        balance_sheet = stock_info.balance_sheet
        income_statement = stock_info.financials
        cash_flow = stock_info.cashflow

        return balance_sheet, income_statement, cash_flow
    except Exception as e:
        st.error(f"獲取財務報表發生錯誤：{str(e)}")
        return None, None, None

def balance(balance_sheet):
    if balance_sheet is not None:
        st.subheader("資產負債表")
        st.table(balance_sheet)

def income(income_statement):
    if income_statement is not None:
        st.subheader("綜合損益表")
        st.table(income_statement)

def cashflow(cash_flow):
    if cash_flow is not None:
        st.subheader("現金流量表")
        st.table(cash_flow)

#股票比較
def stock_data_vs(symbols,start_date,end_date):
    try:
        stock_data_us = yf.download(symbols, start=start_date, end=end_date)
        stock_data_us = stock_data_us.drop(['Open', 'High','Low','Adj Close'], axis=1)
        st.write("交易數據:", stock_data_us)
        return stock_data_us
    except Exception as e:
        st.error(f"無法獲取交易數據: {str(e)}")
        return None

def plot_trend_vs(stock_data,symbols):
    fig = go.Figure()
    for symbol in symbols:
        if symbol in stock_data.columns.get_level_values(1):
            df = stock_data.xs(symbol, level=1, axis=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['Close'], mode='lines', name=symbol))
    fig.update_layout(title='趨勢比較圖', xaxis_title='日期', yaxis_title='價格')
    st.plotly_chart(fig, use_container_width=True)

def plot_volume_chart(stock_data,symbols):
    fig = go.Figure()
    for symbol in symbols:
        if symbol in stock_data.columns.get_level_values(1):
            df = stock_data.xs(symbol, level=1, axis=1)
            fig.add_trace(go.Bar(x=df.index, y=df['Volume'], name=symbol))
    fig.update_layout(title='交易量比較直方圖', xaxis_title='日期', yaxis_title='交易量')
    st.plotly_chart(fig, use_container_width=True)

#今日熱門
def hot_stock():
    url = "https://finance.yahoo.com/most-active/"
    hot_stock = res.get(url)
    f = io.StringIO(hot_stock.text)
    hot_stock_df = pd.read_html(f)
    hot_stock_df = hot_stock_df[0]
    hot_stock_df = hot_stock_df.drop(columns=['PE Ratio (TTM)', '52 Week Range'])
    st.write(hot_stock_df)
    return hot_stock_df

#今日上漲
def gainers_stock():
    url = "https://finance.yahoo.com/gainers"
    gainers_stock = res.get(url)
    f = io.StringIO(gainers_stock.text)
    gainers_stock_df = pd.read_html(f)
    gainers_stock_df = gainers_stock_df[0]
    gainers_stock_df = gainers_stock_df.drop(columns=['PE Ratio (TTM)', '52 Week Range'])
    st.write(gainers_stock_df)
    return gainers_stock_df

#今日下跌
def loser_stock():
    url = "https://finance.yahoo.com/losers/"
    loser_stock = res.get(url)
    f = io.StringIO(loser_stock.text)
    loser_stock_df = pd.read_html(f)
    loser_stock_df = loser_stock_df[0]
    loser_stock_df = loser_stock_df.drop(columns=['PE Ratio (TTM)', '52 Week Range'])
    st.write(loser_stock_df)
    return loser_stock_df


# Streamlit介面

st.header("使用說明", divider="rainbow")

st.markdown('''
    1. 財報使用 GOOGLE 翻譯，因此可能會有專有名詞出現翻譯錯誤        
    2. K 線圖請以美股角度來觀看      
        - 美股: 綠漲、紅跌        
        - 台股: 綠跌、紅漲           
    3. 本平台僅適用於數據搜尋，不建議任何投資行為                    
''')

            
#狀態列
st.sidebar.title('選單')
options = st.sidebar.selectbox('選擇功能:', ['公司基本資訊','公司財報查詢','交易數據','今日熱門'])

if options == '公司基本資訊':
    st.subheader('公司基本資訊')
    symbol = st.text_input('輸入股票').upper()
    if st.button('查詢'):
        com_info = company_info(symbol)
        display_info(com_info)
       
elif options == '公司財報查詢':
    st.header('公司財報查詢')
    symbol = st.text_input('輸入股票').upper()
    if st.button('查詢'):
        balance_sheet, income_statement, cash_flow = financial_statements(symbol)
        if balance_sheet is not None:
            balance(balance_sheet)
        if income_statement is not None:
            income(income_statement)
        if cash_flow is not None:
            cashflow(cash_flow)
        else:
            st.error("無法獲取財報")

elif options == '交易數據':
    st.subheader('交易數據查詢')
    symbol = st.text_input('輸入股票', key='single_stock').upper()
    start_date_single = st.date_input('開始日期', key='start_date_single')
    end_date_single = st.date_input('结束日期', key='end_date_single')
    mav_days = st.number_input('輸入MAV天數', min_value=1, max_value=50, value=5, step=1)  # 添加MAV天數的輸入
    if st.button('查詢'):
        stock_data = stock_data(symbol, start_date_single, end_date_single)
        if stock_data is not None:
            plot_candle(stock_data, mav_days)  # 將MAV天數傳遞給 plot_candle 函式
            plot_trend(stock_data)
            plot_volume(stock_data)
        else:
            st.error("無法獲取交易數據")
    st.subheader('個股比較')
    symbol1 = st.text_input('輸入股票 1', key='stock1')
    symbol2 = st.text_input('輸入股票 2', key='stock2')
    symbol3 = st.text_input('輸入股票 3', key='stock3')
    symbol4 = st.text_input('輸入股票 4', key='stock4')
    symbol5 = st.text_input('輸入股票 5', key='stock5')
    symbol6 = st.text_input('輸入股票 6', key='stock6')
    start_date_multi = st.date_input('開始日期', key='start_date_multi')
    end_date_multi = st.date_input('結束日期', key='end_date_multi')
    if st.button('比較'):
        symbols = [s.upper() for s in [symbol1, symbol2, symbol3, symbol4, symbol5, symbol6] if s]
        if symbols:
            stock_data = stock_data_vs(symbols, start_date_multi, end_date_multi)
            if stock_data is not None:
                plot_trend_vs(stock_data, symbols)
                plot_volume_chart(stock_data, symbols)
        else:
            st.error('請輸入至少一個股票')

elif options == '今日熱門':
    st.subheader("今日交易量最多前25名")
    hot_stock()
    st.subheader("今日上漲前25名")
    gainers_stock()
    st.subheader("今日下跌前25名")
    loser_stock()
