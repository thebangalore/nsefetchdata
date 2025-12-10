import streamlit as st
import pandas as pd
import requests
import io
import time

# 1. Set up the title of the web page
st.title("NSE Data Downloader 📈")
st.write("Enter the NSE Symbols you want to fetch (separated by commas).")

# 2. Create a text box for user input
user_input = st.text_area("Enter Symbols (e.g., RELIANCE, TCS, INFY)", "RELIANCE, TCS")

# 3. The 'Fetch Data' Button
if st.button("Fetch Data"):
    symbols_list = [s.strip().upper() for s in user_input.split(',')]
    
    st.write(f"Fetching data for: {symbols_list}...")
    
    # Create an empty list to store data
    all_data = []
    
    # Headers to mimic a real browser visit (Crucial for NSE)
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br'
    }

    # Create a session to handle cookies
    session = requests.Session()
    session.headers.update(headers)

    # Visit the homepage first to get cookies
    try:
        session.get("https://www.nseindia.com", timeout=10)
    except Exception as e:
        st.error(f"Error connecting to NSE: {e}")

    # Progress bar
    progress_bar = st.progress(0)
    
    for i, symbol in enumerate(symbols_list):
        try:
            url = f"https://www.nseindia.com/api/quote-equity?symbol={symbol}"
            response = session.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                # Extract relevant data (customize this based on what you need)
                info = data.get('priceInfo', {})
                meta = data.get('metadata', {})
                
                row = {
                    'Symbol': symbol,
                    'Last Price': info.get('lastPrice'),
                    'Change': info.get('change'),
                    'pChange': info.get('pChange'),
                    'Open': info.get('open'),
                    'High': info.get('intraDayHighLow', {}).get('max'),
                    'Low': info.get('intraDayHighLow', {}).get('min'),
                    'Previous Close': info.get('previousClose')
                }
                all_data.append(row)
            else:
                st.warning(f"Could not fetch data for {symbol}")
                
        except Exception as e:
            st.error(f"Error for {symbol}: {e}")
            
        # Update progress bar
        progress_bar.progress((i + 1) / len(symbols_list))
        time.sleep(1) # Be polite to the server

    # 4. Show Data and Create Download Link
    if all_data:
        df = pd.DataFrame(all_data)
        st.success("Data Fetched Successfully!")
        st.dataframe(df) # Show the table on the screen

        # Convert dataframe to Excel in memory
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Sheet1')
        
        # Create a download button
        st.download_button(
            label="Download Excel File",
            data=output.getvalue(),
            file_name="NSE_Data.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )