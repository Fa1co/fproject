import csv
import datetime
import json
import time

from bs4 import BeautifulSoup

from selenium import webdriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium_stealth import stealth
from multiprocessing import Pool, Manager
import multiprocessing
import pandas as pd
from selenium.common import exceptions


# Создание драйвера
def create_driver():
    options = Options()
    options.add_argument("--disable-blink-features=AutomationControlled")
    # options.page_load_strategy = 'eager'
    driver = webdriver.Chrome(options=options)
    driver.implicitly_wait(5)
    stealth(driver=driver,
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                       'Chrome/83.0.4103.53 Safari/537.36',
            languages=["ru-RU", "ru"],
            vendor="Google Inc.",
            platform="Win32",
            webgl_vendor="Intel Inc.",
            renderer="Intel Iris OpenGL Engine",
            fix_hairline=True,
            run_on_insecure_origins=True,
            )

    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        'source': '''
                           delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
                           delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
                           delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
                     '''
    })

    return driver


# Сбор данных из катег
def gather_data(url, result):
    try:
        driver = create_driver()
        driver.get(f"{url}&p={1}")
        product_amount = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, 'products-count')))
        pages_count = int(product_amount.text.split()[0]) // 18 + 1 if (int(
            driver.find_element(By.CLASS_NAME, 'products-count').text.split()[0]) // 18) > 0 else 1

        get_page_data(driver=driver, page=1, result=result)

        for page in range(2, pages_count + 1):
            driver.get(f'{url}&p={page}')
            get_page_data(driver=driver, page=page, result=result)
    except Exception:
        print(f'Ошибка в функций gather_data: {Exception}')
    finally:
        driver.close()
        driver.quit()


def get_page_data(driver, page, result):
    try:
        soup = BeautifulSoup(driver.page_source.encode('utf-8'), 'lxml')

        products = soup.findAll('div', class_='catalog-product ui-button-widget', )
        if len(products) == 0:
            return
        # Категория
        try:
            category = soup.find('ol', class_='breadcrumb_last breadcrumb-list__item').text
        except:
            category = "Категория не найдена"

        for product in products:

            # Наименование
            try:
                product_name = product.find('a', class_='catalog-product__name ui-link ui-link_black').text
            except:
                product_name = 'Нет названия'

            try:
                product_id = product['data-product']
            except Exception:
                print(Exception)

            # Ссылка страницы с товаром
            url_to_product = f"https://www.dns-shop.ru{product.find('a', class_='catalog-product__name ui-link ui-link_black')['href']}"

            main_img_url = product.find('div', class_='catalog-product__image').find('img')

            # Ссылку на главное изображение
            if main_img_url.has_attr('data-src'):
                url_to_product_main_img = main_img_url['data-src']
            elif main_img_url.has_attr('src'):
                url_to_product_main_img = main_img_url['src']

            imgs_list = get_all_img(product_id, driver)
            product_characteristics = get_characteristics(product_id, driver)
            product_price, product_is_available, product_description = get_price_description_availability(
                product_id,
                driver)

            result.append(
                {
                    "product_category": category,
                    "product_id": product_id,
                    "product_name": product_name,
                    "product_is_available": product_is_available,
                    "product_price": product_price,
                    "url_to_product": url_to_product,
                    "url_to_product_main_img": url_to_product_main_img,
                    "url_to_product_all_img": imgs_list,
                    "product_characteristics": product_characteristics,
                    "product_description": product_description
                }
            )
        print(f"[INFO] Обработал страницу {page}")
    except:
        print('ошбика тут')


def get_price_description_availability(product_id, driver):
    url = 'https://www.dns-shop.ru/product/microdata/' + product_id
    driver.get(url)
    product_description = 'Нет описания'
    product_price = 0
    product_availability = 'Нет информации'
    try:
        content = driver.find_element(By.CSS_SELECTOR, 'body > pre')
        parsed_json = json.loads(content.text)

        if parsed_json["data"]["description"]:
            product_description = parsed_json["data"]["description"]
        if parsed_json["data"]["offers"]["price"]:
            product_price = parsed_json["data"]["offers"]["price"]
        if parsed_json["data"]["offers"]["availability"]:
            if 'OutOfStock' in parsed_json["data"]["offers"]["availability"]:
                product_availability = 'Товара нет'
            elif 'InStock' in parsed_json["data"]["offers"]["availability"]:
                product_availability = 'В наличии'
    except Exception as error:
        print(error)

    return product_price, product_availability, product_description


def get_all_img(product_id, driver):
    url = 'https://www.dns-shop.ru/catalog/product/get-media-content/?id=' + product_id

    imgs_list = []
    driver.get(url)
    try:
        content = driver.find_element(By.CSS_SELECTOR, 'body > pre')
        # content = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'body > pre')))
        parsed_json = json.loads(content.text)
        for img in parsed_json["data"]["tabs"][0]["objects"]:
            if img["id"].isdigit():
                imgs_list.append(img["origSrc"]["orig"])
    except Exception as error:
        print(error)

    return imgs_list


def get_characteristics(product_id, driver):
    url = 'https://www.dns-shop.ru/catalog/product/get-product-characteristics-actual/?id=' + product_id
    driver.get(url)
    characteristics = ''
    try:
        content = driver.find_element(By.CSS_SELECTOR, 'body > pre')
        # content = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'body > pre')))
        parsed_json = json.loads(content.text)
        soup = BeautifulSoup(parsed_json['html'], 'lxml')
        product_characteristics_group_title = soup.findAll(class_='product-characteristics__group')
        product_characteristics_spec_value = soup.findAll(class_='product-characteristics__spec')

        for title, spec in zip(product_characteristics_group_title, product_characteristics_spec_value):
            characteristics += title.text.strip().replace('\t', '') + spec.text.strip().replace('\t', '')

    except Exception as error:
        print(error)
    return characteristics


# def get_description(product_id, driver):
#     url = 'https://www.dns-shop.ru/product/microdata/' + product_id
#     driver.get(url)
#     product_description = ''
#     try:
#         content = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'body > pre')))
#         parsed_json = json.loads(content.text)
#         product_description = parsed_json["data"]["description"]
#     except Exception as error:
#         print(error)
#
#     return product_description


def convert_csv_to_excel(csv_file):
    # Считываем файл CSV
    df = pd.read_csv(csv_file)

    # Создаем объект ExcelWriter
    writer = pd.ExcelWriter('data.xlsx')

    # Записываем данные в файл Excel
    df.to_excel(writer, index=False)

    # Сохраняем файл
    writer.close()


def main():
    start_time = time.time()

    urls = [
        # 'https://www.dns-shop.ru/catalog/17a9b7a816404e77/podstavki-dlya-noutbukov/?stock=now-today-tomorrow-later-out_of_stock',
        # 'https://www.dns-shop.ru/catalog/17a9b81216404e77/chexly-dlya-noutbukov/?stock=now-today-tomorrow-later-out_of_stock',
        # 'https://www.dns-shop.ru/catalog/2a9d4c3cd6084e77/salazki-v-otsek-privoda-noutbukov/?stock=now-today-tomorrow-later-out_of_stock',
        # 'https://www.dns-shop.ru/catalog/17a9b8e516404e77/ryukzaki-dlya-noutbukov/?stock=now-today-tomorrow-later-out_of_stock',
        'https://www.dns-shop.ru/catalog/17a9b84716404e77/universalnye-bloki-pitaniya/?stock=now-today-tomorrow-later-out_of_stock'
    ]

    manager = Manager()
    products_data = manager.list()
    connections = 1

    pool = Pool(connections)

    for url in urls:
        pool.apply_async(gather_data, args=(url, products_data))

    pool.close()
    pool.join()

    with open('data.csv', 'w', encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(
            [
                "Категория",
                "Наименование",
                "Цена",
                "Наличие",
                "Ссылка страницы с товаром",
                "Ссылку на главное изображение",
                "Ссылки на все изображения",
                "Характеристики",
                "Описание"
            ]
        )
        for data in products_data:
            writer.writerow(
                [
                    data["product_category"],
                    data["product_name"],
                    data["product_price"],
                    data["product_is_available"],
                    data["url_to_product"],
                    data["url_to_product_main_img"],
                    data['url_to_product_all_img'],
                    data['product_characteristics'],
                    data['product_description']

                ]
            )

    finish_time = time.time() - start_time
    print(f"Затраченное на работу скрипта время: {finish_time}")


if __name__ == "__main__":
    main()
    convert_csv_to_excel('data.csv')
