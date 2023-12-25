import yfinance as yf
import pandas as pd
import streamlit as st
import plotly.graph_objs as go
import requests as res
import io
from googletrans import Translator
from pytrends.request import TrendReq

# 獲取公司基本資訊
def get_company_fundamentals(symbol):
    try:
        stock_info = yf.Ticker(symbol)
        fundamentals = stock_info.info
        return fundamentals
    except Exception as e:
        st.error(f"無法獲取公司基本資訊：{str(e)}")
        return None

def display_fundamentals(fundamentals):
    if fundamentals:
        selected_indicators = ['longName', 'country', 'city', 'marketCap', 'totalRevenue', 'grossMargins', 'operatingMargins',
                               'profitMargins', 'trailingEps', 'pegRatio', 'dividendRate', 'payoutRatio', 'bookValue',
                               'operatingCashflow', 'freeCashflow', 'returnOnEquity']

        selected_info = {indicator: fundamentals.get(indicator, '') for indicator in selected_indicators}

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
        df_company_info = pd.DataFrame.from_dict(selected_info,orient='index',columns=['Value'])
        df_company_info.rename(index=translation,inplace=True)

        #轉換成百分比
        percent_columns = ['毛利率', '營業利潤率', '净利率', '股息率', '股息支付比例', '股東權益報酬率']
        for col in percent_columns:
            if col in df_company_info.index:
                df_company_info.at[col, 'Value'] = pd.to_numeric(df_company_info.at[col, 'Value'], errors='coerce')  # 将非数字转换为 NaN
                df_company_info.at[col, 'Value'] = f"{df_company_info.at[col, 'Value']:.2%}" if pd.notna(df_company_info.at[col, 'Value']) else None

        #千分位表示
        df_company_info['Value'] = df_company_info['Value'].apply(lambda x: "{:,.0f}".format(x) if isinstance(x, (int, float)) and x >= 1000 else x)
        st.subheader("公司基本資訊:")
        st.table(df_company_info)
    else:
        st.error(f" {symbol} 公司的基本訊息")


#獲取歷史交易數據
def get_stock_data_us(symbol,start_date,end_date):
    try:
        stock_data = yf.download(symbol,start=start_date,end=end_date)
        st.write("交易數據:", stock_data)
        return stock_data
    except Exception as e:
        st.error(f"無法獲取交易數據：{str(e)}")
        return None

#繪製k線圖
def plot_interactive_candlestick(stock_data):
    fig = go.Figure(data=[go.Candlestick(x=stock_data.index,
                                         open=stock_data['Open'],
                                         high=stock_data['High'],
                                         low=stock_data['Low'],
                                         close=stock_data['Close'])])

    #計算mav
    mav5 = stock_data['Close'].rolling(window=5).mean()  # 20日mav
    mav10 = stock_data['Close'].rolling(window=10).mean()  # 50日mav
    mav20 = stock_data['Close'].rolling(window=20).mean()  # 20日mav

    #添加mav
    fig.add_trace(go.Scatter(x=stock_data.index, y=mav5, mode='lines', name='MAV-5'))
    fig.add_trace(go.Scatter(x=stock_data.index, y=mav10, mode='lines', name='MAV-10'))
    fig.add_trace(go.Scatter(x=stock_data.index, y=mav20, mode='lines', name='MAV-20'))

    fig.update_layout(xaxis_rangeslider_visible=False, xaxis_title='日期', yaxis_title='價格',title='K線圖')
    st.plotly_chart(fig, use_container_width=True)  

#繪製趨勢圖
def plot_interactive_trend(stock_data):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=stock_data.index, y=stock_data['Close'], mode='lines', name='收盤價'))
    fig.update_layout(xaxis_title='日期', yaxis_title='', title='趨勢圖')
    st.plotly_chart(fig, use_container_width=True)

#繪製交易量柱狀圖
def plot_interactive_volume(stock_data):
    fig = go.Figure(data=[go.Bar(x=stock_data.index, y=stock_data['Volume'])])
    fig.update_layout(xaxis_title='日期', yaxis_title='交易量', title='交易量柱狀圖')
    st.plotly_chart(fig, use_container_width=True)
    
#翻譯
translator = Translator()

#財報翻譯
def get_financial_statements(symbol):
    try:
        stock_info = yf.Ticker(symbol)
        balance_sheet = stock_info.balance_sheet
        income_statement = stock_info.financials
        cash_flow = stock_info.cashflow

        return balance_sheet, income_statement, cash_flow
    except Exception as e:
        st.error(f"獲取財務報表發生錯誤：{str(e)}")
        return None, None, None

def translate_financial_statement(statement,translator):
    if statement is not None:
        #翻譯
        translated_index = [translator.translate(index, src='en', dest='zh-tw').text for index in statement.index]
        statement.index = translated_index

        #千分位表示
        statement = statement.applymap(lambda x: "{:,.0f}".format(x) if isinstance(x, (int, float)) and x >= 1000 else x)
        return statement
    else:
        return None

def display_balance_sheet(balance_sheet,translator):
    translated_sheet = translate_financial_statement(balance_sheet, translator)
    if translated_sheet is not None:
        st.subheader("資產負債表")
        st.table(translated_sheet)

def display_income_statement(income_statement,translator):
    translated_sheet = translate_financial_statement(income_statement, translator)
    if translated_sheet is not None:
        st.subheader("損益表")
        st.table(translated_sheet)

def display_cash_flow(cash_flow,translator):
    translated_sheet = translate_financial_statement(cash_flow, translator)
    if translated_sheet is not None:
        st.subheader("現金流量表")
        st.table(translated_sheet)
        
def get_financial_statements_en(symbol):
    try:
        stock_info = yf.Ticker(symbol)
        balance_sheet = stock_info.balance_sheet
        income_statement = stock_info.financials
        cash_flow = stock_info.cashflow

        return balance_sheet, income_statement, cash_flow
    except Exception as e:
        st.error(f"獲取財務報表發生錯誤：{str(e)}")
        return None, None, None

def translate_financial_statement_en(statement):
    if statement is not None:
        statement = statement.applymap(lambda x: "{:,.0f}".format(x) if isinstance(x, (int, float)) and x >= 1000 else x)
        return statement
    else:
        return None

def display_balance_sheet_en(balance_sheet):
    if balance_sheet is not None:
        st.subheader("資產負債表")
        st.table(balance_sheet)

def display_income_statement_en(income_statement):
    if income_statement is not None:
        st.subheader("損益表")
        st.table(income_statement)

def display_cash_flow_en(cash_flow):
    if cash_flow is not None:
        st.subheader("現金流量表")
        st.table(cash_flow)
 
#股票比較
def get_stock_data_us_vs(symbols,start_date,end_date):
    try:
        stock_data_us = yf.download(symbols, start=start_date, end=end_date)
        st.write("交易數據:", stock_data_us)
        return stock_data_us
    except Exception as e:
        st.error(f"無法獲取交易數據: {str(e)}")
        return None

def plot_stock_trend_comparison(stock_data,symbols):
    fig = go.Figure()
    for symbol in symbols:
        if symbol in stock_data.columns.get_level_values(1):
            df = stock_data.xs(symbol, level=1, axis=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['Close'], mode='lines', name=symbol))
    fig.update_layout(title='趨勢比較圖', xaxis_title='日期', yaxis_title='價格')
    st.plotly_chart(fig, use_container_width=True)

def plot_stock_volume_chart(stock_data,symbols):
    fig = go.Figure()
    for symbol in symbols:
        if symbol in stock_data.columns.get_level_values(1):
            df = stock_data.xs(symbol, level=1, axis=1)
            fig.add_trace(go.Bar(x=df.index, y=df['Volume'], name=symbol))
    fig.update_layout(title='交易量比較直方圖', xaxis_title='日期', yaxis_title='交易量')
    st.plotly_chart(fig, use_container_width=True)

#世界指數
def world_index():
    url = "https://finance.yahoo.com/world-indices/"
    world_index = res.get(url)
    f = io.StringIO(world_index.text)
    world_index_df = pd.read_html(f)
    world_index_df = world_index_df[0]
    world_index_df = world_index_df.drop(columns=['Intraday High/Low', '52 Week Range','Day Chart'])
    st.write(world_index_df)
    return world_index_df

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

#熱門etf
def etf():
    url = "https://finance.yahoo.com/etfs/"
    etf = res.get(url)
    f = io.StringIO(etf.text)
    etf_df = pd.read_html(f)
    etf_df = etf_df[0]
    etf_df = etf_df.drop(columns=['52 Week Range'])
    st.write(etf_df)
    return etf_df
   
#貨幣市場
def coin():
    url = "https://finance.yahoo.com/currencies/"
    coin = res.get(url)
    f = io.StringIO(coin.text)
    coin_df = pd.read_html(f)
    coin_df = coin_df[0]
    coin_df = coin_df.drop(columns=['52 Week Range', 'Day Chart'])
    st.write(coin_df)
    return coin_df

# 初始化 Google Trends
pytrend = TrendReq()

# Set the maximum number of retries
max_retries = 3

#關鍵字熱搜
def fetch_google_trends(keywords, start_date, end_date, timezone):
    pytrend = TrendReq(hl='en-US' if timezone == 'New York' else 'zh-TW', tz=-300 if timezone == 'New York' else 480)
    pytrend.build_payload(kw_list=keywords, timeframe=f'{start_date} {end_date}')
    return pytrend.interest_over_time()

# Streamlit介面
st.title('金融數據平台')
st.header("歡迎使用金融數據平台", divider="rainbow")
st.subheader("功能介紹")

st.markdown('''
            1.公司基本資訊: 查詢公司基本資料          
            2.公司財報查詢(中文): 查詢公司三大財務報表(中文版)        
            3.公司財報查詢(英文): 查詢公司三大財務報表(英文版)        
            4.交易數據:查詢股票交易數據、比較股票交易數據      
            5.世界指數:查詢指數數據、比較指數數據        
            6.今日熱門:查看今日熱門、上漲、下跌股票數據、查詢股票交易數據、比較股票交易數據   
            7.熱門ETF:查看熱門ETF、查詢ETF交易數據、比較ETF交易數據     
            8.貨幣市場:查看貨幣市場、查詢貨幣交易數據、比較貨幣交易數據    
            9.熱搜趨勢:查看關鍵字熱搜趨勢      
            10.使用者意見反饋:使用者體驗感受回饋或需要改善地方、希望增加功能  
            備註1.財報使用GOOGLE翻譯，因此可能會有專有名詞出現翻譯錯誤          
            備註2.K線圖請以美股角度來觀看           
            美股:綠漲、紅跌        
            台股:綠跌、紅漲  
            備註3.由於Google Trends API 有請求上限因此在"熱搜趨勢"搜尋時，出現亂碼純屬正常現象    
            ''')
            
#狀態列
st.sidebar.title('選單')
options = st.sidebar.selectbox('選擇功能:', ['公司基本資訊','公司財報查詢(中文)','公司財報查詢(英文)', '交易數據','世界指數','今日熱門','熱門ETF','貨幣市場','熱搜趨勢','使用者意見反饋'])

if options == '公司基本資訊':
    st.subheader('公司基本資訊')
    symbol = st.text_input('輸入股票(台股請加上.tw)').upper()
    if st.button('查詢'):
        fundamentals = get_company_fundamentals(symbol)
        display_fundamentals(fundamentals)
       
elif options == '公司財報查詢(中文)':
    st.header('公司財報查詢(中文)')
    symbol = st.text_input('輸入股票(台股請加上.tw)').upper()
    translator = Translator()
    if st.button('查詢'):
        balance_sheet, income_statement, cash_flow = get_financial_statements(symbol)
        if balance_sheet is not None:
            display_balance_sheet(balance_sheet,translator)
        if income_statement is not None:
            display_income_statement(income_statement,translator)
        if cash_flow is not None:
            display_cash_flow(cash_flow,translator)
        else:
            st.error("無法獲取財報")
            
elif options == '公司財報查詢(英文)':
    st.header('公司財報查詢(英文)')
    symbol = st.text_input('輸入股票代碼(台股請加上.tw)').upper()
    if st.button('查詢'):
        balance_sheet, income_statement, cash_flow = get_financial_statements(symbol)
        if balance_sheet is not None:
            display_balance_sheet_en(balance_sheet)
        if income_statement is not None:
            display_income_statement_en(income_statement)
        if cash_flow is not None:
            display_cash_flow_en(cash_flow)
        else:
            st.error("無法獲取財報")

elif options == '交易數據':
    st.subheader('交易數據查詢')
    symbol = st.text_input('輸入股票(台股請加上.tw)', key='single_stock').upper()
    start_date_single = st.date_input('開始日期', key='start_date_single')
    end_date_single = st.date_input('结束日期', key='end_date_single')
    if st.button('查詢'):
        stock_data = get_stock_data_us(symbol, start_date_single, end_date_single)
        if stock_data is not None:
            plot_interactive_candlestick(stock_data)
            plot_interactive_trend(stock_data)
            plot_interactive_volume(stock_data)
        else:
            st.error("無法獲取交易數據")
    st.subheader('個股比較')
    symbol1 = st.text_input('輸入股票 1(台股請加上.tw)', key='stock1')
    symbol2 = st.text_input('輸入股票 2(台股請加上.tw)', key='stock2')
    symbol3 = st.text_input('輸入股票 3(台股請加上.tw)', key='stock3')
    symbol4 = st.text_input('輸入股票 4(台股請加上.tw)', key='stock4')
    symbol5 = st.text_input('輸入股票 5(台股請加上.tw)', key='stock5')
    symbol6 = st.text_input('輸入股票 6(台股請加上.tw)', key='stock6')
    start_date_multi = st.date_input('開始日期', key='start_date_multi')
    end_date_multi = st.date_input('結束日期', key='end_date_multi')
    if st.button('比較'):
        symbols = [s.upper() for s in [symbol1, symbol2, symbol3, symbol4, symbol5, symbol6] if s]
        if symbols:
            stock_data = get_stock_data_us_vs(symbols, start_date_multi, end_date_multi)
            if stock_data is not None:
                plot_stock_trend_comparison(stock_data, symbols)
                plot_stock_volume_chart(stock_data, symbols)
        else:
            st.error('請輸入至少一個股票')

elif options == '世界指數':
    st.subheader('世界指數')
    world_index()
    st.subheader('指數查詢')
    symbol = st.text_input('輸入指數 1(要跟上面symbol欄位一樣或複製上面表格symbol欄位上去)', key='single_stock').upper()
    start_date_single = st.date_input('開始日期', key='start_date_single')
    end_date_single = st.date_input('结束日期', key='end_date_single')
    if st.button('查詢'):
        stock_data = get_stock_data_us(symbol, start_date_single, end_date_single)
        if stock_data is not None:
            plot_interactive_candlestick(stock_data)
            plot_interactive_trend(stock_data)
            plot_interactive_volume(stock_data)
        else:
            st.error("無法獲取指數")
    st.subheader('指數比較')
    symbol1 = st.text_input('輸入指數 1(要跟上面symbol欄位一樣或複製上面表格symbol欄位上去)', key='stock1')
    symbol2 = st.text_input('輸入指數 2(要跟上面symbol欄位一樣或複製上面表格symbol欄位上去)', key='stock2')
    symbol3 = st.text_input('輸入指數 3(要跟上面symbol欄位一樣或複製上面表格symbol欄位上去)', key='stock3')
    symbol4 = st.text_input('輸入指數 4(要跟上面symbol欄位一樣或複製上面表格symbol欄位上去)', key='stock4')
    symbol5 = st.text_input('輸入指數 5(要跟上面symbol欄位一樣或複製上面表格symbol欄位上去)', key='stock5')
    symbol6 = st.text_input('輸入指數 6(要跟上面symbol欄位一樣或複製上面表格symbol欄位上去)', key='stock6')
    start_date_multi = st.date_input('開始日期', key='start_date_multi')
    end_date_multi = st.date_input('結束日期', key='end_date_multi')
    if st.button('比較'):
        symbols = [s.upper() for s in [symbol1, symbol2, symbol3, symbol4, symbol5, symbol6] if s]
        if symbols:
            stock_data = get_stock_data_us_vs(symbols, start_date_multi, end_date_multi)
            if stock_data is not None:
                plot_stock_trend_comparison(stock_data, symbols)
                plot_stock_volume_chart(stock_data, symbols)
        else:
            st.error('請輸入至少一個指數')
            
elif options == '今日熱門':
    st.subheader('今日熱門')
    hot_stock()
    st.subheader('今日上漲')
    gainers_stock()
    st.subheader('今日下跌')
    loser_stock()   
    st.subheader('股票查詢')
    symbol = st.text_input('輸入股票(台股請加上.tw)', key='single_stock').upper()
    start_date_single = st.date_input('開始日期', key='start_date_single')
    end_date_single = st.date_input('结束日期', key='end_date_single')
    if st.button('查詢'):
        stock_data = get_stock_data_us(symbol,start_date_single,end_date_single)
        if stock_data is not None:
            plot_interactive_candlestick(stock_data)
            plot_interactive_trend(stock_data)
            plot_interactive_volume(stock_data)
        else:
            st.error("無法獲取交易數據")
    st.subheader('個股比較')
    symbol1 = st.text_input('輸入股票 1(台股請加上.tw)', key='stock1')
    symbol2 = st.text_input('輸入股票 2(台股請加上.tw)', key='stock2')
    symbol3 = st.text_input('輸入股票 3(台股請加上.tw)', key='stock3')
    symbol4 = st.text_input('輸入股票 4(台股請加上.tw)', key='stock4')
    symbol5 = st.text_input('輸入股票 5(台股請加上.tw)', key='stock5')
    symbol6 = st.text_input('輸入股票 6(台股請加上.tw)', key='stock6')
    start_date_multi = st.date_input('開始日期', key='start_date_multi')
    end_date_multi = st.date_input('結束日期', key='end_date_multi')
    if st.button('比較'):
        symbols = [s.upper() for s in [symbol1, symbol2, symbol3, symbol4, symbol5, symbol6] if s]
        if symbols:
            stock_data = get_stock_data_us_vs(symbols,start_date_multi,end_date_multi)
            if stock_data is not None:
                plot_stock_trend_comparison(stock_data,symbols)
                plot_stock_volume_chart(stock_data,symbols)
        else:
            st.error('請輸入至少一個股票')
            
elif options == '熱門ETF':
    st.subheader('熱門ETF')
    etf()
    st.subheader('ETF查詢')
    symbol = st.text_input('輸入ETF (台股請加上.tw)', key='single_stock').upper()
    start_date_single = st.date_input('開始日期', key='start_date_single')
    end_date_single = st.date_input('结束日期', key='end_date_single')
    if st.button('查詢'):
        stock_data = get_stock_data_us(symbol,start_date_single,end_date_single)
        if stock_data is not None:
            plot_interactive_candlestick(stock_data)
            plot_interactive_trend(stock_data)
            plot_interactive_volume(stock_data)
        else:
            st.error("無法獲取ETF")
    st.subheader('ETF比較')
    symbol1 = st.text_input('輸入ETF 1(台股請加上.tw)', key='stock1')
    symbol2 = st.text_input('輸入ETF 2(台股請加上.tw)', key='stock2')
    symbol3 = st.text_input('輸入ETF 3(台股請加上.tw)', key='stock3')
    symbol4 = st.text_input('輸入ETF 4(台股請加上.tw)', key='stock4')
    symbol5 = st.text_input('輸入ETF 5(台股請加上.tw)', key='stock5')
    symbol6 = st.text_input('輸入ETF 6(台股請加上.tw)', key='stock6')
    start_date_multi = st.date_input('開始日期', key='start_date_multi')
    end_date_multi = st.date_input('結束日期', key='end_date_multi')
    if st.button('比較'):
        symbols = [s.upper() for s in [symbol1, symbol2, symbol3, symbol4, symbol5, symbol6] if s]
        if symbols:
            stock_data = get_stock_data_us_vs(symbols,start_date_multi,end_date_multi)
            if stock_data is not None:
                plot_stock_trend_comparison(stock_data,symbols)
                plot_stock_volume_chart(stock_data,symbols)
        else:
            st.error('請輸入至少一個ETF')

elif options == '貨幣市場':
    st.subheader('貨幣市場')
    coin()
    st.subheader('貨幣查詢')
    symbol = st.text_input('輸入貨幣 (輸入格式:貨幣=x(美元/其他) 或 貨幣貨幣=x)', key='single_stock').upper()
    start_date_single = st.date_input('開始日期', key='start_date_single')
    end_date_single = st.date_input('结束日期', key='end_date_single')
    if st.button('查詢'):
        stock_data = get_stock_data_us(symbol,start_date_single,end_date_single)
        if stock_data is not None:
            plot_interactive_candlestick(stock_data)
            plot_interactive_trend(stock_data)
        else:
            st.error("無法獲取ETF")
    st.subheader('貨幣比較')
    symbol1 = st.text_input('輸入貨幣 1(輸入格式:貨幣=x(美元/其他) 或 貨幣貨幣=x)', key='stock1')
    symbol2 = st.text_input('輸入貨幣 2(輸入格式:貨幣=x(美元/其他) 或 貨幣貨幣=x)', key='stock2')
    symbol3 = st.text_input('輸入貨幣 3(輸入格式:貨幣=x(美元/其他) 或 貨幣貨幣=x)', key='stock3')
    symbol4 = st.text_input('輸入貨幣 4(輸入格式:貨幣=x(美元/其他) 或 貨幣貨幣=x)', key='stock4')
    symbol5 = st.text_input('輸入貨幣 5(輸入格式:貨幣=x(美元/其他) 或 貨幣貨幣=x)', key='stock5')
    symbol6 = st.text_input('輸入貨幣 6(輸入格式:貨幣=x(美元/其他) 或 貨幣貨幣=x)', key='stock6')
    start_date_multi = st.date_input('開始日期', key='start_date_multi')
    end_date_multi = st.date_input('結束日期', key='end_date_multi')
    if st.button('比較'):
        symbols = [s.upper() for s in [symbol1, symbol2, symbol3, symbol4, symbol5, symbol6] if s]
        if symbols:
            stock_data = get_stock_data_us_vs(symbols,start_date_multi,end_date_multi)
            if stock_data is not None:
                plot_stock_trend_comparison(stock_data,symbols)
        else:
            st.error('請輸入至少一個貨幣')

elif options == '熱搜趨勢':
    st.subheader('熱搜趨勢')
    
    timezone = st.selectbox("選擇時區", ["台北", "紐約"])
    keywords = st.text_input('請輸入關鍵詞，用逗號分隔')
    start_date = st.date_input('開始日期')
    end_date = st.date_input('結束日期')
    
    if st.button('獲取數據'):
        kw_list = keywords.split(',')
        data = fetch_google_trends(kw_list, start_date, end_date, timezone)
        
        if not data.empty:
            # 轉換為 DataFrame 並顯示
            df = pd.DataFrame(data)
            st.write(df)
            
            # 創建並顯示折線圖
            fig_line = go.Figure()
            for keyword in kw_list:
                fig_line.add_trace(go.Scatter(x=df.index, y=df[keyword], mode='lines', name=keyword))
            fig_line.update_layout(title='Google Trends 折線圖', xaxis_title='日期', yaxis_title='關鍵字')
            st.plotly_chart(fig_line)
            
            # 創建並顯示柱狀圖
            fig_bar = go.Figure()
            for keyword in kw_list:
                fig_bar.add_trace(go.Bar(x=df.index, y=df[keyword], name=keyword))
            fig_bar.update_layout(title='Google Trends 柱狀圖', xaxis_title='日期', yaxis_title='關鍵字')
            st.plotly_chart(fig_bar)
        else:
            st.write("無數據可用")

elif options == '使用者意見反饋':
    st.subheader('使用者意見反饋')
    st.text('如有使用疑問或需要改善、希望增加功能地方請至下方連結填寫')
    st.write("https://forms.gle/RXJo9YX7UtkCvt9bA")
    