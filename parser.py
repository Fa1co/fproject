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




def get_page_data(driver, page, url, result):
    driver.get(f'{url}&p={page}')
    time.sleep(2)

    soup = BeautifulSoup(driver.page_source, 'html.parser')
    soup.encode("utf-8")
    products = soup.findAll(class_='catalog-product ui-button-widget')
    if len(products) == 0:
        return
    # Категориz
    try:
        category = soup.find(class_='breadcrumb_last breadcrumb-list__item').text
    except:
        category = "Категория не найдена"
    for product in products:

        # Категориz
        product_category = category

        # Наименование
        try:
            product_name = product.find(class_='catalog-product__name ui-link ui-link_black').text
        except:
            product_name = 'Нет названия'
        # доступен или нет к продаже
        if product.find(class_='order-avail-wrap__link ui-link ui-link_blue'):
            product_is_available = product.find(class_='order-avail-wrap__link ui-link ui-link_blue').text.strip()
        else:
            product_is_available = 'Нет в наличии'

        # Цена
        if product.find(class_='product-buy__price'):
            product_price = product.find(class_='product-buy__price').text
        else:
            product_price = 'Цена не указан'

        # Ссылка страницы с товаром
        url_to_product = f"https://www.dns-shop.ru{product.find('a')['href']}"

        # Ссылку на главное изображение
        if product.find(class_='catalog-product__image').find('img').has_attr('data-src'):
            url_to_product_main_img = product.find(class_='catalog-product__image').find('img')['data-src']
        elif product.find(class_='catalog-product__image').find('img').has_attr('src'):
            url_to_product_main_img = product.find(class_='catalog-product__image').find('img')['src']

        result.append(
            {
                "product_category": product_category,
                "product_name": product_name,
                "product_is_available": product_is_available,
                "product_price": product_price,
                "url_to_product": url_to_product,
                "url_to_product_main_img": url_to_product_main_img,
            }
        )
    print(f"[INFO] Обработал страницу {page}")


def gather_data(url, result):
    options = Options()
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument('--window-size=1200,1080')
    driver = webdriver.Chrome(options=options)

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

    driver.get(url)
    time.sleep(5)
    pages_count = int(driver.find_element(By.CLASS_NAME, 'products-count').text.split()[0]) // 18 + 1 if (int(
        driver.find_element(By.CLASS_NAME, 'products-count').text.split()[0]) // 18) > 0 else 1

    for page in range(1, pages_count + 1):
        get_page_data(driver=driver, page=page, url=url, result=result)



    driver.close()
    driver.quit()


def get_extra_info(product):


    options = Options()
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument('--window-size=1200,1080')
    driver = webdriver.Chrome(options=options)

    stealth(
        driver=driver,
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

    url = product['url_to_product']
    driver.get(url)

    if get_element_status(driver, url):
        button = driver.find_element(by=By.CLASS_NAME, value='product-characteristics__expand')
        button.click()

        time.sleep(1)

        product_page = BeautifulSoup(driver.page_source, 'html.parser')
        product_page.encode("utf-8")

        # Ссылки на все изображения
        try:
            url_to_product_all_imgs = []

            imgs = product_page.findAll(class_='tns-item')

            for img in imgs:
                try:
                    if img.find('img').has_attr('data-src'):
                        url_to_product_all_imgs.append(img.find('img')['data-src'])
                        continue
                    elif img.find('img').has_attr('src'):
                        url_to_product_all_imgs.append(img.find('img')['src'])
                except Exception:
                    pass
        except:
            url_to_product_all_imgs.append('Нет изображений')

        # Характеристики
        try:
            product_characteristics = product_page.findAll(class_='product-characteristics-content')
            tmp_str = ''

            for characteristic in product_characteristics:
                tmp_str += characteristic.text.strip().replace('\t', '')
        except:
            tmp_str = 'нет характеристик'
        # Описание
        try:
            product_description = product_page.find(class_='product-card-description-text').text
        except:
            product_description = "Нет описания"
        product.update(
            {
                'url_to_product_all_imgs': url_to_product_all_imgs,
                'product_characteristics': tmp_str,
                'product_description': product_description
            }
        )
        return product


def get_element_status(driver, url):
    connection_attempts = 0
    while connection_attempts < 3:
        try:
            driver.get(url)
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CLASS_NAME, 'product-characteristics__expand')))
            return True
        except Exception as error:
            print(error)
            connection_attempts += 1
            print(f"Ошибка в получение данных для: {url}")
    return False


def convert_csv_to_excel(csv_file, excel_file):
    # Считываем файл CSV
    df = pd.read_csv('data.csv')

    # Создаем объект ExcelWriter
    writer = pd.ExcelWriter('data.xlsx')

    # Записываем данные в файл Excel
    df.to_excel(writer, index=False)

    # Сохраняем файл
    writer.close()

def main():
    start_time = time.time()

    urls = [
        'https://www.dns-shop.ru/catalog/17a9b7a816404e77/podstavki-dlya-noutbukov/?stock=now-today-tomorrow-later-out_of_stock',
        'https://www.dns-shop.ru/catalog/17a9b81216404e77/chexly-dlya-noutbukov/?stock=now-today-tomorrow-later-out_of_stock',
        'https://www.dns-shop.ru/catalog/2a9d4c3cd6084e77/salazki-v-otsek-privoda-noutbukov/?stock=now-today-tomorrow-later-out_of_stock',
        'https://www.dns-shop.ru/catalog/17a9b8e516404e77/ryukzaki-dlya-noutbukov/?stock=now-today-tomorrow-later-out_of_stock',
        'https://www.dns-shop.ru/catalog/17a9b84716404e77/universalnye-bloki-pitaniya/?stock=now-today-tomorrow-later-out_of_stock']

    manager = Manager()
    products_data = manager.list()
    connections = 5

    pool = Pool(connections)

    for url in urls:
        pool.apply_async(gather_data, args=(url, products_data))

    pool.close()
    pool.join()

    result = []
    counter = 0
    print(f'Количество продуктов: {len(products_data)}')
    with Pool(connections) as pool:
        result = pool.map(get_extra_info, products_data)
        print(f'Counter: {counter}')
        counter += 1
    # for product in products_data:
    #     result.append(get_extra_info(product))


    pool.close()
    pool.join()

    print(products_data)

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
        for data in result:
            writer.writerow([
                data["product_category"],
                data["product_name"],
                data["product_is_available"],
                data["product_price"],
                data["url_to_product"],
                data["url_to_product_main_img"],
                data['url_to_product_all_imgs'],
                data['product_characteristics'],
                data['product_description']
            ]
        )


    finish_time = time.time() - start_time
    print(f"Затраченное на работу скрипта время: {finish_time}")


if __name__ == "__main__":
    main()
