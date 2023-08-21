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

    soup = BeautifulSoup(driver.page_source, 'lxml')
    soup.encode("utf-8")
    products = soup.findAll('div', class_='catalog-product ui-button-widget')
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

        try:
            product_id = product['data-product']
        except Exception:
            print(Exception)

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

        imgs_list = get_all_img(product_id, driver)
        product_characteristics = get_characteristics(product_id, driver)
        product_description = get_description(product_id, driver)




        result.append(
            {
                "product_category": product_category,
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


def get_all_img(product_id, driver):
    url = 'https://www.dns-shop.ru/catalog/product/get-media-content/?id=' + product_id

    imgs_list = []
    driver.get(url)
    try:
        content = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'body > pre')))
        parsed_json = json.loads(content.text)
        for i in parsed_json["data"]["tabs"][0]["objects"]:
            if i["id"].isdigit():
                imgs_list.append(i["origSrc"]["orig"])
    except Exception as error:
        print(error)

    return imgs_list


def get_description(product_id, driver):
    url = 'https://www.dns-shop.ru/product/microdata/' + product_id
    driver.get(url)
    product_description = ''
    try:
        content = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'body > pre')))
        parsed_json = json.loads(content.text)
        product_description = parsed_json["data"]["description"]
    except Exception as error:
        print(error)

    return product_description

def get_characteristics(product_id, driver):
    url = 'https://www.dns-shop.ru/catalog/product/get-product-characteristics-actual/?id=' + product_id
    driver.get(url)
    characteristics = ''
    try:
        content = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'body > pre')))
        parsed_json = json.loads(content.text)
        soup = BeautifulSoup(parsed_json['html'], 'lxml')
        product_characteristics_group_title = soup.findAll(class_='product-characteristics__group')
        product_characteristics_spec_value = soup.findAll(class_='product-characteristics__spec')


        for title, spec in zip(product_characteristics_group_title, product_characteristics_spec_value):
            characteristics += title.text.strip().replace('\t', '') + spec.text.strip().replace('\t', '')

    except Exception as error:
        print(error)
    return characteristics

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
    driver.implicitly_wait(10)
    time.sleep(5)
    pages_count = int(driver.find_element(By.CLASS_NAME, 'products-count').text.split()[0]) // 18 + 1 if (int(
        driver.find_element(By.CLASS_NAME, 'products-count').text.split()[0]) // 18) > 0 else 1

    for page in range(1, pages_count + 1):
        get_page_data(driver=driver, page=page, url=url, result=result)

    driver.close()
    driver.quit()





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
        'https://www.dns-shop.ru/catalog/17a9b7a816404e77/podstavki-dlya-noutbukov/?stock=now-today-tomorrow-later-out_of_stock',
        'https://www.dns-shop.ru/catalog/17a9b81216404e77/chexly-dlya-noutbukov/?stock=now-today-tomorrow-later-out_of_stock',
        'https://www.dns-shop.ru/catalog/2a9d4c3cd6084e77/salazki-v-otsek-privoda-noutbukov/?stock=now-today-tomorrow-later-out_of_stock',
        'https://www.dns-shop.ru/catalog/17a9b8e516404e77/ryukzaki-dlya-noutbukov/?stock=now-today-tomorrow-later-out_of_stock',
        'https://www.dns-shop.ru/catalog/17a9b84716404e77/universalnye-bloki-pitaniya/?stock=now-today-tomorrow-later-out_of_stock']




    manager = Manager()
    products_data = manager.list()
    connections = 3

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
                    data["product_is_available"],
                    data["product_price"],
                    data["url_to_product"],
                    data["url_to_product_main_img"],
                    data['url_to_product_all_img'],
                    data['product_characteristics'],
                    data['product_description']

            ]
    )

    # options = Options()
    # options.add_argument("--disable-blink-features=AutomationControlled")
    # options.add_argument('--window-size=1200,1080')
    # driver = webdriver.Chrome(options=options)
    #
    # stealth(driver=driver,
    #         user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
    #                    'Chrome/83.0.4103.53 Safari/537.36',
    #         languages=["ru-RU", "ru"],
    #         vendor="Google Inc.",
    #         platform="Win32",
    #         webgl_vendor="Intel Inc.",
    #         renderer="Intel Iris OpenGL Engine",
    #         fix_hairline=True,
    #         run_on_insecure_origins=True,
    #         )
    #
    # driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
    #     'source': '''
    #                    delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
    #                    delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
    #                    delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
    #              '''
    # })
    #
    # driver.get('https://www.dns-shop.ru/catalog/17a8ae4916404e77/televizory/?stock=now-today-tomorrow-later-out_of_stock')
    # driver.implicitly_wait(5)
    # time.sleep(1)
    # soup = BeautifulSoup(driver.page_source, 'lxml')
    # pages = soup.find("div", class_="catalog-product ui-button-widget")
    # # pages = WebDriverWait(driver, 10).until(EC.presence_of_all_elements_located((By.CLASS_NAME, 'catalog-product')))
    #
    # print(len(pages))
    # print(pages[-1].get_attribute('data-page-number'))


    finish_time = time.time() - start_time
    print(f"Затраченное на работу скрипта время: {finish_time}")


if __name__ == "__main__":
    main()
    convert_csv_to_excel('data.csv')