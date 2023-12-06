from utils import *


class ParserAvito:
    def __init__(self, search_phrase, record_border):
        # страница, которую будем парсить (дополним url после того как пользователь введет свой запрос)
        self.url = "https://www.avito.ru/"

        #===========================ПАРСЕР==========================
        #фраза для поиска
        self.search_phrase = search_phrase
        #количество объявлений для парсинга (по умолчанию бесконечность)
        self.record_border = record_border
        # объект, содержащий настройки драйвера
        self.options = webdriver.ChromeOptions()
        # и замаскируем webdriver, чтобы сайты не блокировали наше автономное ПО
        self.options.add_argument("--disable-blink-features=AutomationControlled")
        # запускаем браузер в фоновом режиме
        self.options.add_argument("--headless")
        # создаем объект драйвера с заданными настройками
        self.driver = webdriver.Chrome(options=self.options)

        #===========================SQLite==========================

        #подключение к БД
        self.conn = None
        self.cursor = None
        self.db_name = 'cache.db'

    # выбираем категорию на авито и переходим на страницу с объявлениями по этой категории
    # в зависимости от запроса пользователя, если категория не найдется, то просто будем искать по тексту запроса
    def Form_url(self):

        self.driver.get(url=self.url)
        #находим поле "поиск по объявлениям" и эмулируем ввод нашего запроса туда и кликаем по нему
        our_input = self.driver.find_element('xpath', "//input[@data-marker='search-form/suggest']")
        our_input.click()
        our_input.clear()
        # набираем поисковую фразу в поисковой строке
        our_input.send_keys(self.search_phrase)
        time.sleep(1)
        # выбираем первую попавшуюся категорию, которую предложило авито по нашему запросy, если такая нашлась
        try:
            category_img = self.driver.find_element('xpath',"//img[@class='suggest-itemIconImg-kXlmA']")
            category_img.click()
        # если категория не нашлась, то просто ищем через кнопку "Найти"
        except NoSuchElementException:
            find_button = self.driver.find_element('xpath', "//button[@data-marker='search-form/submit-button']")
            find_button.click()
        time.sleep(1)
        #получаем url по которому будем парсить
        self.url = self.driver.current_url
        print('status: form_check')


    # создание БД, если не существует
    def DB_create(self):
        try:
            # Создаем БД, если еще не существует
            self.conn = sqlite3.connect(self.db_name)
            self.cursor = self.conn.cursor()
            self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS Cache (
            ad_id INTEGER PRIMARY KEY,
            ad_number TEXT NOT NULL UNIQUE,
            ad_name TEXT NOT NULL,
            ad_price TEXT NOT NULL,
            ad_address TEXT NOT NULL,
            ad_description TEXT NOT NULL,
            ad_publication_date TEXT NOT NULL,
            ad_views TEXT NOT NULL,
            ad_cur_link TEXT NOT NULL,
            ad_status TEXT NOT NULL,
            search_phrase TEXT NOT NULL,
            insert_time TEXT NOT NULL,
            update_time TEXT NOT NULL
            )''')
            self.conn.commit()
            print('БД: БД создана, таблица Cache создана, подключение установлено')
        except Error as e:
            raise NameError('Подключение к БД не произошло:',e)

    # возвращаем записи по определенному поисковому запросу
    def DB_select_by_phrase(self):
        try:
            time_sleep()
            self.cursor.execute('SELECT * FROM Cache WHERE search_phrase = ?',(self.search_phrase,))
            table = self.cursor.fetchall()
            return table
        except Error as e:
            raise NameError('Получить таблицу не удалось:',e)

    #вставка записи
    def DB_insert(self, ad_info):
        time_sleep()
        # ad_info - данные для кеширования
        try:
            insert_time = datetime.now()
            # формируем запрос и добавляем запись
            self.cursor.execute('INSERT INTO Cache (ad_number, ad_name, ad_price, ad_address, ad_description, ad_publication_date, '
                                'ad_views, ad_cur_link, ad_status, search_phrase, insert_time, update_time) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',
                                (ad_info[0], ad_info[1], ad_info[2], ad_info[3], ad_info[4], ad_info[5], ad_info[6], ad_info[7], ad_info[8],
                                 self.search_phrase, insert_time, insert_time)
            )
            self.conn.commit()
            print('БД: Новая запись добавлена')
        except Error as e:
            raise NameError('Вставка записи не удалась:', e)

    # проверка наличия записи в кеше
    def DB_ad_exist_checker(self, ad_number):
        time_sleep()
        # если запись с определенным номером
        try:
            self.cursor.execute("SELECT ad_number FROM Cache WHERE ad_number = ?", (ad_number,))
            result = self.cursor.fetchall()
            if len(result) == 0:
                return False
            else:
                return True
        except Error as e:
            raise NameError('Проверка на наличие записи не удалась:', e)

    # проверка наличия изменений в объявлении (статус, цена, имя, описание)
    def DB_ad_upd_check(self, ad_new_info):
        time_sleep()
        try:
            self.cursor.execute("SELECT ad_status, ad_price, ad_name, ad_description FROM Cache")
            result = self.cursor.fetchall()
            for ad_elem in result:
                if normalize_text(ad_elem[0]) != normalize_text(ad_new_info[8]):
                    return True
                elif normalize_text(ad_elem[1]) != normalize_text(ad_new_info[2]):
                    return True
                elif normalize_text(ad_elem[2]) != normalize_text(ad_new_info[1]):
                    return True
                #если тексты описаний не совпадают
                elif ad_elem[3] != ad_new_info[4]:
                    # если различие в текстах больше 10%, тогда обновляем объявление
                    if percentage_difference(ad_elem[3], ad_new_info[4]) > 10:
                        return True
                    else:
                        return False
                else:
                    return False
        except Error as e:
            raise NameError('БД: Проверка изменения в объявлении не удалась', e)
        except:
            raise NameError('При проверке объявления на изменения не обработался результат')

    # обновление объявления
    def DB_ad_update(self, ad_new_info):
        time_sleep()
        try:
            self.cursor.execute("UPDATE Cache SET ad_name = ?, ad_price = ?, ad_description = ?, ad_status = ?, update_time = ? WHERE ad_number = ?",
                                (ad_new_info[1],ad_new_info[2], ad_new_info[4], ad_new_info[8],str(datetime.now()),ad_new_info[0]))
            self.conn.commit()
            print('БД: Запись успешно обновлена')
        except Error as e:
            raise NameError('БД: Обновление записи не удалось', e)


    # обработка одного объявления
    def parse_ad(self):
        # переходим на открытое окно с объявлением:
        self.driver.switch_to.window(self.driver.window_handles[1])

        # собираем нужную информацию в этом объявлении:
        ad_number = self.driver.find_element("xpath", "//span[@data-marker='item-view/item-id']").text[2:]
        ad_name = self.driver.find_element("xpath", "//h1[@data-marker='item-view/title-info']").text
        ad_price = self.driver.find_element("xpath", "//span[@itemprop='price']").get_attribute("content")
        ad_address = self.driver.find_element("xpath", "//span[@class='style-item-address__string-wt61A']").text
        ad_description = self.driver.find_element("xpath","//div[@class='style-item-view-block-SEFaY style-item-view-description-k9US4 style-new-style-iX7zV']").text
        new_ad_description = ad_description.replace("Описание", '')
        ad_description = delete_emoji(new_ad_description)

        ad_publication_date = self.driver.find_element("xpath", "//span[@data-marker='item-view/item-date']").text[2:]
        # проверяем дату публикации на наличие "вчера"/"позавчера"/"сегодня" и тд, заменяем на запись следующего вида,например (5 ноября в 20:57)
        # если сегодня 5 ноября, например
        if 'позавчера' in ad_publication_date:
            new_month = str((datetime.now() - timedelta(days=2)).strftime("%B"))
            new_day = str((datetime.now() - timedelta(days=2)).strftime("%d"))
            ad_publication_date = ad_publication_date.replace('позавчера',new_day+' '+new_month)
        if 'вчера' in ad_publication_date:
            new_month = str((datetime.now() - timedelta(days=1)).strftime("%B"))
            new_day = str((datetime.now() - timedelta(days=1)).strftime("%d"))
            ad_publication_date = ad_publication_date.replace('вчера',new_day+' '+new_month)
        if 'сегодня' in ad_publication_date:
            new_month = str((datetime.now()).strftime("%B"))
            new_day = str((datetime.now()).strftime("%d"))
            ad_publication_date = ad_publication_date.replace('сегодня',new_day+' '+new_month)
        # если на объявлении нет просмотров => оно новое и их там 0
        try:
            ad_views = self.driver.find_element("xpath", "//span[@data-marker='item-view/total-views']").text
            #если просмотров сейчас нет
            if ad_views == ' просмотров':
                ad_views = '0'
        except NoSuchElementException:
            ad_views = '0'
        ad_cur_link = self.driver.current_url
        # если находим данный класс => объявление снято и закрыто
        try:
            ad_status = self.driver.find_element("xpath", "//span[@class='closed-warning-content-_f4_B']")
            ad_status = 'Закрыто'
        except NoSuchElementException:
            ad_status = 'Открыто'

        # закрываем окно браузера с объявлением, чтобы не засорять браузер вкладками
        self.driver.close()
        # переключаемся на наше исходное окно и начинаем парсить следующее объявление
        self.driver.switch_to.window(self.driver.window_handles[0])

        # возвращаем из объявления все что требовалось в задании соответсвенно:
        # [номер объявления, название_объявления, цена, адрес, описание, дата публикации, просмотры, ссылка, статус]
        return [ad_number, ad_name, ad_price, ad_address, ad_description, ad_publication_date,
                ad_views, ad_cur_link, ad_status]

    # обработка списка объявлений
    def parsing_ads(self):
        #счетчик обработанных объявлений
        counter = 0
        # открываем страницу, которую будем парсить
        self.Form_url()

        # когда задано ограничение в виде целого числа
        if isinstance(self.record_border, int):
            while True:
                # список объявлений, которые мы будем парсить
                item_photos = self.driver.find_elements("xpath", "//div[@data-marker='item-photo']")
                for item_photo in item_photos:
                    if counter < self.record_border:
                        counter+=1
                        item_photo.click()
                        # возвращаем результаты парсинга
                        ad_info = self.parse_ad()
                        # если записи нет в кеше
                        if self.DB_ad_exist_checker(ad_info[0]) == False:
                            # вставка новой записи в таблицу
                            self.DB_insert(ad_info)
                        else:
                            # если объявление изменилось
                            if self.DB_ad_upd_check(ad_info):
                                #обновляем в кеше
                                self.DB_ad_update(ad_info)
                    else:
                        break
                # переходим на следующую страницу авито, если есть, если нет, то завершаем
                try:
                    # если дошли до ограничения на кол-во обработанных объявлений
                    if counter == self.record_border:
                        return
                    print('Парсер: Переход на следующую страницу Avito')
                    time.sleep(1)
                    NP_active_check = self.driver.find_element("xpath", "//a[@data-marker='pagination-button/nextPage']")
                    NP_active_check.click()
                    time_sleep()
                # если обработали все страницы
                except NoSuchElementException:
                    return
                except:
                    raise NameError('Переход на следующую страницу не работает')

        # когда введено не целочисленное значение и не 'inf'
        else:
            raise NameError('Сложновато парсить, когда ограничение кол-ва объявлений для парсинга указано не целочисленным значением!')

    # сохранение данных в Excel по последней поисковой фразе
    def save_to_Excel(self):
        try:
            result = self.DB_select_by_phrase()
            wb = openpyxl.Workbook()
            sheet = wb.active
            for row in result:
                sheet.append(row)
            wb.save(self.search_phrase+".xlsx")
        except:
            raise NameError("Не удалось сохранить результаты запроса в Excel")


    # запускаем парсер
    def start_parsing(self):
        try:
            # создаем БД
            self.DB_create()

            # начинаем парсить объявления
            self.parsing_ads()

            # сохранение в Excel
            self.save_to_Excel()
        except Error:
            print('БД: Ошибка при создании БД')
        except NameError as e:
            print('Ошибка:', e)
        except:
            print('Ошибка: Неизвестно, что могло пойти не так...')
        finally:
            self.driver.close()
            self.driver.quit()


if __name__ == '__main__':
    # входные параметры: 1-запрос пользователя, 2-количество объявлений сколько будем парсить или до конца, если об. меньше
    new_parser = ParserAvito('Toyota Camry',10000)
    new_parser.start_parsing()