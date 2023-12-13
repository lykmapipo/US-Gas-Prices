"""
Scrape state gas price daily averages from AAA Gas Prices website.

Usage::

    pip install selenium webdriver-manager pandas
    python scrape_state_daily_averages.py

"""

import datetime
import logging
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.common.by import By

from webdriver_manager.chrome import ChromeDriverManager

import pandas as pd


SOURCE_URL = "https://gasprices.aaa.com/state-gas-price-averages/"
HEADERS_CSS_SELECTOR = "#sortable > thead > tr > th"
ROWS_CSS_SELECTOR = "#sortable > tbody > tr"
DATASETS_BASE_PATH = Path("./data")

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# prepare chrome
logging.info("Start.")
logging.info("Preparing chrome ...")
chrome_options = webdriver.ChromeOptions()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--incognito")

chrome_driver_manager = ChromeDriverManager()
chrome_executable_path = chrome_driver_manager.install()
chrome_service = webdriver.ChromeService(executable_path=chrome_executable_path)

chrome_driver = webdriver.Chrome(service=chrome_service, options=chrome_options)
logging.info("Preparing chrome finished.")

# request page
logging.info("Requesting page ...")
chrome_driver.get(SOURCE_URL)
while chrome_driver.execute_script("return document.readyState") != "complete":
    logging.info("Waiting for document ready state ...")
logging.info("Requesting page finished.")

# parse data headers
logging.info("Parsing data ...")
headers = chrome_driver.find_elements(By.CSS_SELECTOR, HEADERS_CSS_SELECTOR)
headers = [header.text.strip() for header in headers]

# parse data rows
rows = chrome_driver.find_elements(By.CSS_SELECTOR, ROWS_CSS_SELECTOR)
rows = [[td.text.strip() for td in row.find_elements(By.TAG_NAME, "td")] for row in rows]
rows = [[row[0]] + [float(col.replace("$", "").strip()) for col in row[1:]] for row in rows]

# collect data
scrape_date = datetime.date.today()
data = [dict(zip(headers, row)) for row in rows]
df = pd.DataFrame(data)
df["Date"] = scrape_date
logging.info("Parsing data finished.")

# save data
data_pth = DATASETS_BASE_PATH / "state-daily-averages" / f"{scrape_date}.csv"
logging.info(f"Saving data at {data_pth}")
data_pth = data_pth.expanduser().resolve()
data_pth.parent.mkdir(parents=True, exist_ok=True)
df.to_csv(data_pth, index=False)
logging.info("Saving data finished.")

# close chrome
chrome_driver.close()
chrome_driver.quit()
logging.info("Done.")
