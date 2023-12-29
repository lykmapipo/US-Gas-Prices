"""
Scrape state gas price daily averages from AAA Gas Prices website.

Usage::

    mkdir -p data/state-daily-averages
    pip install selenium webdriver-manager pandas
    python scrape_state_daily_averages.py

"""

import datetime
import logging
from pathlib import Path

import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

SOURCE_URL = "https://gasprices.aaa.com/state-gas-price-averages/"
DATE_CSS_SELECTOR = "div.average-price > span"
HEADERS_CSS_SELECTOR = "#sortable > thead > tr > th"
ROWS_CSS_SELECTOR = "#sortable > tbody > tr"

DATASETS_BASE_PATH = Path("./data")

HEADERS_BASIC = ["State-Name", "State-Abbreviation"]
HEADERS_CURRENCY = "Currency"
HEADERS_UNIT = "Unit"
HEADERS_DATE = "Date"
CURRENCY = "U.S Dollar"
UNIT = "US Gallon"

DRIVER_WAIT_TIME_MAXIMUM = 10

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

# wait for document to be ready to use JavaScript
logging.info("Waiting for document to be ready to use JavaScript ...")
while chrome_driver.execute_script("return document.readyState") != "complete":
    logging.info("Waiting for document ready state ...")

# wait for common elements to be present on the page (i.e map, tables ...)
logging.info("Waiting for document common elements to be present ...")
chrome_driver_wait = WebDriverWait(chrome_driver, DRIVER_WAIT_TIME_MAXIMUM)
expected_conditions = (
    EC.presence_of_element_located((By.CSS_SELECTOR, DATE_CSS_SELECTOR)),  # price date
    EC.presence_of_all_elements_located((By.CSS_SELECTOR, HEADERS_CSS_SELECTOR)),  # table header
    EC.presence_of_all_elements_located((By.CSS_SELECTOR, ROWS_CSS_SELECTOR)),  # table rows
)
elements = chrome_driver_wait.until(EC.all_of(*expected_conditions))
logging.info("Requesting page finished.")

# parse gas price date
logging.info("Parsing data ...")
try:
    scrape_date = chrome_driver.find_element(By.CSS_SELECTOR, DATE_CSS_SELECTOR)
    scrape_date = scrape_date.text.strip().split()[-1].strip()
    scrape_date = datetime.datetime.strptime(scrape_date, "%m/%d/%y").date()
except:
    scrape_date = datetime.date.today()

# parse data headers
headers = chrome_driver.find_elements(By.CSS_SELECTOR, HEADERS_CSS_SELECTOR)
headers = HEADERS_BASIC + [header.text.strip() for header in headers[1:]]

# parse data rows
rows = chrome_driver.find_elements(By.CSS_SELECTOR, ROWS_CSS_SELECTOR)


def parse_row(row):
    tds = row.find_elements(By.TAG_NAME, "td")
    state_td = tds[0].find_element(By.TAG_NAME, "a")
    state_name = state_td.text.strip()
    state_abbreviation = state_td.get_attribute("href").split("=")[-1].strip().upper()
    prices = [float(price_td.text.replace("$", "").strip()) for price_td in tds[1:]]
    return [state_name, state_abbreviation] + prices


rows = map(parse_row, rows)

# collect data
data = [dict(zip(headers, row)) for row in rows]
df = pd.DataFrame(data)
df[HEADERS_CURRENCY] = CURRENCY
df[HEADERS_UNIT] = UNIT
df[HEADERS_DATE] = scrape_date
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
