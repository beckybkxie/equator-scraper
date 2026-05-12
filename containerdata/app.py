import time
import pandas as pd
import streamlit as st

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    StaleElementReferenceException
)

chrome_options.add_argument("--headless=new")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--window-size=1920,1080")

driver = webdriver.Chrome(options=chrome_options)


from urllib.parse import urljoin
from bs4 import BeautifulSoup

# =========================================
# CONFIG
# =========================================

BASE_URL = "https://equator.freightoa.com"

USERNAME = "BK"
PASSWORD = "14235ramona@"


# =========================================
# LOGIN
# =========================================

def login(driver):

    driver.get(f"{BASE_URL}/eCommerceOcean/MBL/List.aspx")

    time.sleep(2)

    username_input = WebDriverWait(driver, 20).until(
        EC.element_to_be_clickable((By.ID, "TxtUserID"))
    )

    username_input.clear()
    username_input.send_keys(USERNAME)

    password_input = WebDriverWait(driver, 20).until(
        EC.element_to_be_clickable((By.ID, "TxtPwd"))
    )

    password_input.clear()
    password_input.send_keys(PASSWORD)

    login_button = WebDriverWait(driver, 20).until(
        EC.element_to_be_clickable((By.ID, "BtnLogin"))
    )

    login_button.click()

    WebDriverWait(driver, 30).until(
        lambda d: "Home" in d.current_url or "Home" in d.title
    )

    st.success("✅ 登录成功")


# =========================================
# EXTRACT DETAIL
# =========================================

def extract_detail_from_iframe(driver):

    try:

        iframe = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "iframe#FramePopwin")
            )
        )

        driver.switch_to.frame(iframe)

    except TimeoutException:

        driver.switch_to.default_content()

    soup = BeautifulSoup(driver.page_source, "html.parser")

    # Delivery Address
    delivery_address_element = soup.find(
        "textarea",
        id="c_delivery_address"
    )

    if delivery_address_element:

        delivery_address = delivery_address_element.get_text(
            separator=' ',
            strip=True
        )

    else:

        delivery_address = ""

    # CBM
    cbm_element = soup.find("input", id="c_cbm")

    if cbm_element and 'value' in cbm_element.attrs:

        cbm = cbm_element['value'].strip()

    else:

        cbm = ""

    # CTN
    ctn_element = soup.find("input", id="c_pkgs")

    if ctn_element and 'value' in ctn_element.attrs:

        ctn = ctn_element['value'].strip()

    else:

        ctn = ""

    driver.switch_to.default_content()

    return delivery_address, cbm, ctn


# =========================================
# MAIN SCRAPER
# =========================================

def run_scraper():

    all_data = []

    chrome_options = Options()

    # 本地调试不要 headless
    # chrome_options.add_argument("--headless")

    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=chrome_options
    )

    try:

        # =========================================
        # LOGIN
        # =========================================

        login(driver)

        # =========================================
        # OPEN PAGE
        # =========================================

        driver.get(f"{BASE_URL}/eCommerceOcean/MBL/List.aspx")

        st.info("请在 Chrome 中手动选择日期并点击 Search")

        # =========================================
        # WAIT USER SEARCH
        # =========================================

        # 获取 Search 按钮
        search_btn = driver.find_element(
            By.ID,
            "MainContent_BtnSearch"
        )

        # 等待 Search 按钮失效（页面刷新）
        WebDriverWait(driver, 300).until(
            EC.staleness_of(search_btn)
        )

        # 等待新页面加载完成
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "table")
            )
        )

        st.success("✅ 检测到 Search 完成，开始抓取")

        time.sleep(2)

        # =========================================
        # GET MAIN TABLE
        # =========================================

        main_table_rows = driver.find_elements(
            By.CSS_SELECTOR,
            "table tr:not(:first-child)"
        )

        st.write(f"主列表找到 {len(main_table_rows)} 行")

        detail_links = []
        container_nos = []

        for row in main_table_rows:

            try:

                link_element = row.find_element(
                    By.CSS_SELECTOR,
                    "a[href*='Detail.aspx?Current_DataId']"
                )

                href = link_element.get_attribute("href")

                container_no = row.find_element(
                    By.CSS_SELECTOR,
                    "td:nth-child(5)"
                ).text.strip()

                detail_links.append(href)

                container_nos.append(container_no)

            except Exception:

                continue

        st.write(f"找到 {len(detail_links)} 个 Container")

        progress_bar = st.progress(0)

        # =========================================
        # LOOP CONTAINERS
        # =========================================

        for idx, url in enumerate(detail_links):

            progress_bar.progress((idx + 1) / len(detail_links))

            container_no = container_nos[idx]

            st.write(
                f"正在处理 Container: {container_no} "
                f"({idx + 1}/{len(detail_links)})"
            )

            driver.get(url)

            time.sleep(2)

            # =========================================
            # OPEN ORDER LIST
            # =========================================

            try:

                order_link = WebDriverWait(driver, 20).until(
                    EC.element_to_be_clickable(
                        (By.PARTIAL_LINK_TEXT, "Order List")
                    )
                )

                order_href = order_link.get_attribute("href")

                driver.get(order_href)

                time.sleep(2)

            except Exception as e:

                st.error(
                    f"Container {container_no} "
                    f"打开 Order List 失败: {e}"
                )

                continue

            # =========================================
            # GET ORDERS
            # =========================================

            try:

                order_rows = driver.find_elements(
                    By.CSS_SELECTOR,
                    "table tr:not(:first-child)"
                )

                st.write(f"发现 {len(order_rows)} 行订单")

                target_orders = []

                for row in order_rows:

                    try:

                        tds = row.find_elements(By.TAG_NAME, "td")

                        if len(tds) <= 15:
                            continue

                        delivery_to = tds[15].text.strip()

                        if delivery_to.startswith("LAX9"):
                            continue

                        if not (
                            delivery_to.startswith("CA")
                            or delivery_to.startswith("LAX")
                            or delivery_to.startswith("EQ")
                            or delivery_to.startswith("HWC")
                            or delivery_to.startswith("ZM")
                            or delivery_to.startswith("橙联")
                            or delivery_to.startswith("TK")
                        ):
                            continue

                        order_no = tds[1].text.strip()

                        edit_icon = row.find_element(
                            By.CSS_SELECTOR,
                            "img[src*='edit.png']"
                        )

                        link_element = edit_icon.find_element(
                            By.XPATH,
                            "./.."
                        )

                        onclick_attr = link_element.get_attribute(
                            "onclick"
                        )

                        detail_url = ""

                        if (
                            onclick_attr
                            and "/Public/ControlDoc" in onclick_attr
                        ):

                            start = onclick_attr.find(
                                "/Public/ControlDoc"
                            )

                            end = onclick_attr.find(
                                "'",
                                start
                            )

                            if end == -1:

                                end = onclick_attr.find(
                                    '"',
                                    start
                                )

                            sub_url = onclick_attr[start:end]

                            detail_url = urljoin(
                                BASE_URL,
                                sub_url.strip()
                            )

                        if detail_url:

                            target_orders.append({
                                "order_no": order_no,
                                "delivery_to": delivery_to,
                                "detail_url": detail_url
                            })

                    except Exception:

                        continue

                order_list_url = driver.current_url

                # =========================================
                # LOOP ORDERS
                # =========================================

                for order_data in target_orders:

                    try:

                        st.write(
                            f"抓取 Order: "
                            f"{order_data['order_no']}"
                        )

                        driver.get(order_data["detail_url"])

                        time.sleep(2)

                        delivery_address, cbm, ctn = extract_detail_from_iframe(driver)

                        all_data.append({

                            "ContainerNo": container_no,

                            "OrderNo": order_data["order_no"],

                            "DeliveryTo": order_data["delivery_to"],

                            "CTN": ctn,

                            "CBM": cbm,

                            "DeliveryAddress": delivery_address

                        })

                        driver.get(order_list_url)

                        time.sleep(1)

                    except Exception as inner_e:

                        st.error(
                            f"Order "
                            f"{order_data['order_no']} "
                            f"抓取失败: {inner_e}"
                        )

                        driver.switch_to.default_content()

                        driver.get(order_list_url)

                        time.sleep(1)

                        continue

            except Exception as e:

                st.error(
                    f"Container {container_no} "
                    f"抓取失败: {e}"
                )

                continue

        driver.quit()

        return pd.DataFrame(all_data)

    except Exception as e:

        driver.quit()

        raise e


# =========================================
# STREAMLIT UI
# =========================================

st.set_page_config(
    page_title="Equator Scraper",
    layout="wide"
)

st.title("Equator Order Scraper")

st.write("自动登录后，请手动 Search")

if st.button("Start Scraping"):

    with st.spinner("Scraping..."):

        try:

            df = run_scraper()

            st.success(
                f"✅ 抓取完成，共 {len(df)} 条数据"
            )

            st.dataframe(df)

            filename = (
                f"CA_{time.strftime('%Y%m%d_%H%M%S')}.xlsx"
            )

            df.to_excel(filename, index=False)

            with open(filename, "rb") as f:

                st.download_button(
                    label="📥 下载 Excel",
                    data=f,
                    file_name=filename,
                    mime=(
                        "application/"
                        "vnd.openxmlformats-officedocument."
                        "spreadsheetml.sheet"
                    )
                )

        except Exception as e:

            st.error(str(e))