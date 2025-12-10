import streamlit as st
import pandas as pd
import requests
import time
import random
import io

# --- 1. COPY YOUR ORIGINAL FUNCTIONS HERE ---
# (I have kept your logic exactly the same, just removed the file saving parts)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nseindia.com/get-quotes/equity?symbol=RELIANCE",
    "Connection": "keep-alive"
}

def get_session():
    """Initialize session and visit homepage to set cookies."""
    session = requests.Session()
    session.headers.update(HEADERS)
    try:
        session.get("https://www.nseindia.com", timeout=10)
        session.get("https://www.nseindia.com/get-quotes/equity?symbol=RELIANCE", timeout=10)
    except Exception:
        pass
    return session

def clean_value(val):
    if val is None or val == "-":
        return 0
    if isinstance(val, (int, float)):
        return val
    try:
        return float(str(val).replace(",", ""))
    except:
        return 0

def fetch_stock_data(session, symbol):
    url_symbol = symbol.replace('&', '%26')
    main_url = f"https://www.nseindia.com/api/quote-equity?symbol={url_symbol}"
    trade_url = f"https://www.nseindia.com/api/quote-equity?symbol={url_symbol}&section=trade_info"

    try:
        r1 = session.get(main_url, timeout=10)
        if r1.status_code == 401:
            return "SESSION_EXPIRED"
        main_data = r1.json() if r1.status_code == 200 else {}
        
        time.sleep(0.2)
        
        r2 = session.get(trade_url, timeout=10)
        trade_data = r2.json() if r2.status_code == 200 else {}
        
        return combine_data(symbol, main_data, trade_data)

    except Exception as e:
        return None

def combine_data(symbol, main_js, trade_js):
    if not main_js:
        return None

    info = main_js.get('info', {})
    price = main_js.get('priceInfo', {})
    meta = main_js.get('metadata', {})
    industry = main_js.get('industryInfo', {})
    
    security_wise = trade_js.get('securityWiseDP', {}) 
    if not security_wise:
        security_wise = main_js.get('securityWiseDP', {})

    vol = price.get('totalTradedVolume')
    if not vol:
        vol = main_js.get('preOpenMarket', {}).get('totalTradedVolume')
    if not vol:
        vol = trade_js.get('marketDeptOrderBook', {}).get('tradeInfo', {}).get('totalTradedVolume')
    if not vol:
        vol = security_wise.get('quantityTraded')

    try:
        mcap_val = trade_js.get('marketDeptOrderBook', {}).get('tradeInfo', {}).get('totalMarketCap')
        if not mcap_val:
            issued = clean_value(main_js.get('securityInfo', {}).get('issuedSize'))
            last_price = clean_value(price.get('lastPrice'))
            mcap_val = (issued * last_price) / 10000000 
    except:
        mcap_val = 0

    row = {
        "SYMBOL": info.get('symbol', symbol),
        "Date": meta.get('lastUpdateTime'),
        "Open": price.get('open'),
        "High": price.get('intraDayHighLow', {}).get('max'),
        "Low": price.get('intraDayHighLow', {}).get('min'),
        "Close": price.get('lastPrice'),
        "Change": price.get('change'),
        "% Change": price.get('pChange'),
        "Traded Volume": clean_value(vol),
        "Total Market Cap (Cr)": mcap_val,
        "Free Float Market Cap": "Restricted (Calc Req)", 
        "Quantity Traded": security_wise.get('quantityTraded'),
        "Deliverable Quantity (gross across client level)": security_wise.get('deliveryQuantity'),
        "% of Deliverable / Traded Quantity": security_wise.get('deliveryToTradedQuantity'),
        "Price Band (%)": f"{price.get('lowerCP', 0)} - {price.get('upperCP', 0)}",
        "Index": meta.get('pdSectorInd'),
        "Macro-Economic Sector": industry.get('macro'),
        "Sector": industry.get('sector'),
        "Industry": industry.get('industry'),
        "Basic Industry": industry.get('basicIndustry')
    }
    return row

# --- 2. STREAMLIT INTERFACE ---

st.title("NSE Advanced Data Fetcher 📊")
st.markdown("Fetch detailed **Delivery Data**, **Market Cap**, and **Sector Info** directly from NSE.")

# Input area
default_symbols = "RELIANCE, TCS, INFY, HDFCBANK"
user_input = st.text_area("Enter Symbols (comma separated):", default_symbols, height=100)

if st.button("Fetch Data", type="primary"):
    # Process symbols
    symbols = [s.strip().upper() for s in user_input.split(',') if s.strip()]
    
    if not symbols:
        st.error("Please enter at least one symbol.")
    else:
        st.write(f"Initializing session and fetching data for {len(symbols)} symbols...")
        
        # Initialize
        session = get_session()
        all_rows = []
        progress_bar = st.progress(0)
        status_text = st.empty()

        for i, sym in enumerate(symbols):
            status_text.text(f"Fetching {sym}...")
            
            result = fetch_stock_data(session, sym)
            
            # Handle session expiry logic from your original code
            if result == "SESSION_EXPIRED":
                status_text.text("Session Expired. Refreshing...")
                session = get_session()
                result = fetch_stock_data(session, sym)
            
            if result:
                all_rows.append(result)
            
            # Update progress
            progress_bar.progress((i + 1) / len(symbols))
            
            # Your original random sleep
            time.sleep(random.uniform(0.5, 1.0))

        status_text.text("Done!")
        
        # Show and Download Data
        if all_rows:
            df = pd.DataFrame(all_rows)
            
            # Use your specific column ordering
            cols = ["SYMBOL", "Date", "Open", "High", "Low", "Close", "Change", "% Change", 
                    "Traded Volume", "Total Market Cap (Cr)", "Free Float Market Cap", 
                    "Quantity Traded", "Deliverable Quantity (gross across client level)", 
                    "% of Deliverable / Traded Quantity", "Price Band (%)", "Index", 
                    "Macro-Economic Sector", "Sector", "Industry", "Basic Industry"]
            
            # Filter existing columns
            cols = [c for c in cols if c in df.columns]
            df = df[cols]

            st.success(f"Successfully fetched data for {len(all_rows)} stocks.")
            st.dataframe(df)

            # Excel Download Button
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False)
            
            st.download_button(
                label="📥 Download Excel File",
                data=output.getvalue(),
                file_name=f"NSE_Data_{time.strftime('%Y%m%d_%H%M')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.error("Failed to fetch data. Please check the symbols or try again later.")
