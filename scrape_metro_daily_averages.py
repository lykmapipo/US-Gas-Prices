"""
Scrape state metro(s) gas price daily averages from AAA Gas Prices website.

Usage::

    mkdir -p data/metro-daily-averages
    pip install selenium webdriver-manager pandas
    python scrape_metro_daily_averages.py

"""

import datetime
import logging
import time
from pathlib import Path

import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

SOURCE_URL = "https://gasprices.aaa.com/state-gas-price-averages/"
DATE_CSS_SELECTOR = "div.average-price > span"

STATES_CSS_SELECTOR = "#sortable > tbody > tr"

METROS_ACCORDION_EXPAND_CSS_SELECTOR = "a.expand-all-js"
METROS_NAME_CSS_SELECTOR = "div.accordion-prices > h3.ui-accordion-header"
METROS_TABLE_CSS_SELECTOR = "div.accordion-prices > div.ui-accordion-content > div.tblwrap > table.table-mob"

DATASETS_BASE_PATH = Path("./data")

HEADERS_BASIC = ["State-Name", "State-Abbreviation", "Metro-Name"]
HEADERS_CURRENCY = "Currency"
HEADERS_UNIT = "Unit"
HEADERS_DATE = "Date"
CURRENCY = "U.S Dollar"
UNIT = "US Gallon"

DRIVER_WAIT_TIME_MAXIMUM = 10

NEXT_PAGE_WAIT_TIME = 2

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def wait_until_document_ready(driver=None, wait_time=10, *css_selectors):
    """Wait for document and elements to be available."""
    logging.info("Waiting for document to be ready to use JavaScript ...")
    while driver.execute_script("return document.readyState") != "complete":
        logging.info("Waiting for document ready state ...")

    logging.info("Waiting for document common elements to be present ...")
    driver_wait = WebDriverWait(driver, wait_time)
    css_selectors = set(["body", *css_selectors])
    expected_conditions = (
        EC.presence_of_all_elements_located((By.CSS_SELECTOR, css_selector)) for css_selector in css_selectors
    )
    elements = driver_wait.until(EC.all_of(*expected_conditions))
    return elements


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
css_selectors = [DATE_CSS_SELECTOR, STATES_CSS_SELECTOR]
wait_until_document_ready(chrome_driver, DRIVER_WAIT_TIME_MAXIMUM, *css_selectors)
logging.info("Requesting page finished.")

logging.info("Parsing data ...")
# parse gas price date
try:
    scrape_date = chrome_driver.find_element(By.CSS_SELECTOR, DATE_CSS_SELECTOR)
    scrape_date = scrape_date.text.strip().split()[-1].strip()
    scrape_date = datetime.datetime.strptime(scrape_date, "%m/%d/%y").date()
except:
    scrape_date = datetime.date.today()

# parse each state data (i.e state_name, state_abbreviation, state_url)
logging.info("Parsing states data ...")
states = chrome_driver.find_elements(By.CSS_SELECTOR, STATES_CSS_SELECTOR)


def parse_state_row(row):
    """Parse state name, abbreviation and url."""
    tds = row.find_elements(By.TAG_NAME, "td")
    state_td = tds[0].find_element(By.TAG_NAME, "a")
    state_name = state_td.text.strip()
    state_url = state_td.get_attribute("href").strip()
    state_abbreviation = state_url.split("=")[-1].strip().upper()
    return (state_name, state_abbreviation, state_url)


states = list(map(parse_state_row, states))
logging.info("Parsing state data finished.")

# parse each state metros data (i.e metro_name, and prices)
logging.info("Parsing metro data ...")
data = []
for state_name, state_abbreviation, state_url in states:
    logging.info(f"Parsing {state_name} metro data ...")

    # request state metros page
    chrome_driver.get(state_url)
    css_selectors = [METROS_ACCORDION_EXPAND_CSS_SELECTOR, METROS_NAME_CSS_SELECTOR, METROS_TABLE_CSS_SELECTOR]
    wait_until_document_ready(chrome_driver, DRIVER_WAIT_TIME_MAXIMUM, *css_selectors)

    # expand all metro accordions
    expand_accordion = chrome_driver.find_element(By.CSS_SELECTOR, METROS_ACCORDION_EXPAND_CSS_SELECTOR)
    expand_accordion.click()

    # state metro names
    metro_names = chrome_driver.find_elements(By.CSS_SELECTOR, METROS_NAME_CSS_SELECTOR)
    metro_names = [metro_name.text.strip() for metro_name in metro_names]

    # state metro tables
    metro_tables = chrome_driver.find_elements(By.CSS_SELECTOR, METROS_TABLE_CSS_SELECTOR)

    # state metros data
    for metro_name, metro_table in zip(metro_names, metro_tables):
        # parse data headers
        headers = metro_table.find_elements(By.CSS_SELECTOR, "thead > tr > th")[1:]
        headers = [header.text.strip() for header in headers]

        # parse data rows
        rows = metro_table.find_elements(By.CSS_SELECTOR, "tbody > tr:nth-child(1) > td")[1:]
        rows = [float(row.text.replace("$", "").strip()) for row in rows]

        # collect metro data
        headers = HEADERS_BASIC + headers
        rows = [state_name, state_abbreviation, metro_name] + rows
        metro = dict(zip(headers, rows))
        data.append(metro)

    logging.info(f"Parsing {state_name} metro finished.")

    # wait a bit before scrape next state page
    time.sleep(NEXT_PAGE_WAIT_TIME)

logging.info("Parsing metro data finished.")

# collect data
df = pd.DataFrame(data)
df[HEADERS_CURRENCY] = CURRENCY
df[HEADERS_UNIT] = UNIT
df[HEADERS_DATE] = scrape_date
df = df.rename(columns={"Mid": "Mid-Grade"})
logging.info("Parsing data finished.")

# save data
data_pth = DATASETS_BASE_PATH / "metro-daily-averages" / f"{scrape_date}.csv"
logging.info(f"Saving data at {data_pth}")
data_pth = data_pth.expanduser().resolve()
data_pth.parent.mkdir(parents=True, exist_ok=True)
df.to_csv(data_pth, index=False)
logging.info("Saving data finished.")

# close chrome
chrome_driver.close()
chrome_driver.quit()
logging.info("Done.")
