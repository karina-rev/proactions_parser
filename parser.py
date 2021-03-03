from selenium import webdriver
from bs4 import BeautifulSoup
from models import Brand, Action, BrandAction, Comment
import re
import time
import random
import logging

browser = webdriver.Chrome(executable_path='/usr/local/bin/chromedriver')
logging.basicConfig(filename='proactions.log',
                    format='%(asctime)s [%(levelname)s] - %(message)s',
                    level=logging.INFO)


def parse_brands():
    """
    Получение и запись списка брендов в таблицу brands
    """
    logging.info("Парсинг брендов")
    soup = get_soup_page_by_link('https://proactions.ru/brands/')
    lists = soup.find(id='content').findAll('li')
    count = 0
    for e in lists:
        try:
            articles = e.a.attrs
            if articles['href']:
                Brand.create(name=e.text, link='https://proactions.ru' + e.a.attrs['href'])
                count += 1
        except Exception as ex:
            logging.error(str(ex))
    logging.info(f'Записано {count} брендов')


def parse_actions():
    logging.info('Парсинг акций всех брендов')
    brands = Brand.select()
    for brand in brands:
        try:
            parse_actions_of_brand(brand.id, brand.link)
            i += 1
        except Exception as ex:
            logging.error(str(ex))


def parse_actions_of_brand(brand_id, brand_link):
    """
    Получение и запись списка акций бренда в таблицу actions
    :param brand_id: id бренда в таблице brands
    :param brand_link: ссылка на акции бренда
    :return:
    """
    logging.info(f'Парсинг акций бренда {brand_link}')
    soup_page = get_soup_page_by_link(brand_link)

    # определяем количество страниц с акциями
    ul_paging = soup_page.find('ul', class_='paging')
    if ul_paging:
        page_count = ul_paging.find_all('li')[-2]
        page_count = re.search('<li>.+?</li>', str(page_count))
        page_count = re.sub('<li><a.+?>', '', str(page_count.group()))
        page_count = int(re.sub('</a></li>', '', page_count))
    else:
        page_count = 1

    # проходимся по каждой странице с акциями
    page_start = 1
    for page_number in range(page_start, page_count + 1):
        soup_page = get_soup_page_by_link(brand_link + '?page=' + str(page_number))
        stuff = soup_page.find('div', class_='post-container')

        # проходимся по каждому блоку с акцией
        for item in stuff:
            title = re.search('a href=".+?\.html">.+?</a>', str(item))
            if not title:
                continue

            # проверяем, что дата акции позднее 2019 года
            dates = re.search('<span class="time-of">.+?</span>', str(item))
            dates = re.sub('<span class="time-of">', '', str(dates.group()))
            dates = re.sub('</span>', '', dates)
            if int(dates.split(' ')[-1]) < 2019:
                continue

            # заходим на страницу акции и парсим её
            action_link = 'https://proactions.ru' + item.find('a', class_='button-01')['href']
            soup_action_page = get_soup_page_by_link(action_link)
            logging.info(f'Парсинг страницы акции {action_link}')
            result = get_action_page(soup_action_page)

            try:
                action = Action.get(
                    (Action.title == result['title']) &
                    (Action.description == result['description']) &
                    (Action.benefits == result['benefits']) &
                    (Action.date == result['date']))
            except Action.DoesNotExist:
                action = Action.create(
                    title=result['title'],
                    link=action_link,
                    description=result['description'],
                    benefits=result['benefits'],
                    date=result['date'],
                    img=result['img'],
                    url_official=result['url_official'],
                    participation=result['participation'],
                    timing=result['timing'],
                    other_text=result['other_text'],
                    organizers=result['organizers'],
                    operators=result['operators'],
                    rules_link=result['rules_link'],
                    tags=result['tags'],
                    comments_num=int(result['comments_num']),
                    view_num=int(result['view_num']),
                    rating=result['rating'])
                logging.info(f'Запись акции, action.id = {action}')

                if action.comments_num > 0:
                    comments = parse_comments(action_link)
                    for comment in comments:
                        Comment.create(
                            action_id=action.id,
                            username=comment['username'],
                            login=comment['login'],
                            date=comment['date'],
                            link=comment['link'],
                            rating=comment['rating'],
                            text=comment['text'],
                            img=comment['img']
                        )
                    logging.info(f'Запись {len(comments)} комментарий')

            #print('ACTION: ', action)
            try:
                BrandAction.get((BrandAction.brand_id == brand_id) &
                                (BrandAction.action_id == action.id))
            except BrandAction.DoesNotExist:
                BrandAction.create(brand_id=brand_id,
                                   action_id=action.id)


def get_action_page(soup_page):
    article = soup_page.find('article')

    # название акции, дата проведения, ссылка на изображение
    title = article.find('h1', class_='action__header').text
    action_date = article.find('div', class_='action__date').text
    img = article.find('img')
    # ссылка на официальный сайт акции
    action_url = article.find('div', class_='action__url')
    if action_url:
        action_url = action_url.find('a')['href']

    # описание акции
    section_text = article.find('section', class_='text')
    description = section_text.find('p')
    description = description.text + get_description_after_h2(description)

    # блок 'Призы'
    benefits = section_text.find('h2', string=re.compile(".*Призы.*"))
    if not benefits:
        benefits = section_text.find('p', string=re.compile(".*Призы.*"))
    if benefits:
        benefits = get_description_after_h2(benefits)

    # блок 'Участие в акции'
    participation = section_text.find('h2', string=re.compile(".*Участие.*"))
    if not participation:
        participation = section_text.find('p', string=re.compile(".*Участие.*"))
    if not participation:
        participation = section_text.find('h2', string=re.compile(".*Для участия.*"))
    if participation:
        participation = get_description_after_h2(participation)

    # блок 'Сроки проведения акции'
    timing = section_text.find('h2', string=re.compile(".*Сроки проведения.*"))
    if not timing:
        timing = section_text.find('p', string=re.compile(".*Сроки проведения.*"))
    if timing:
        timing = get_description_after_h2(timing)

    other_text = ''
    all_h2 = section_text.find_all('h2')
    for h2 in all_h2:
        if not re.search('Призы.+?', str(h2.text)) and not re.search('Сроки проведения.+?', str(h2.text)) \
                and not re.search('Участие в.+?', str(h2.text)) and not re.search('Для участия.+?', str(h2.text)):
            other_text += str(h2) + get_description_after_h2(h2)

    org_names = section_text.find('p', class_='action__org_names')
    organizers = re.search('Организаторы? акции:.+?<br', str(org_names))
    if organizers:
        organizers = re.sub('Организаторы? акции:', '', str(organizers.group()))
        organizers = re.sub('<br', '', str(organizers))
        organizers = re.sub('<a.+?>', '', organizers)
        organizers = re.sub('</a>', '', organizers)

    operators = re.search('Операторы? акции:.*', str(org_names))
    if operators:
        operators = re.sub('Операторы? акции:', '', str(operators.group()))
        operators = re.sub('<a.+?>', '', str(operators))
        operators = re.sub('</a>', '', operators)

    rules_link = section_text.find('a', string=re.compile(".*Полные правила акции.*"))
    if rules_link:
        rules_link = rules_link['href']

    footer = article.find('footer', class_='post')
    action_tags = footer.find_all('div', class_='action__tags_block')
    tags = None
    for action_tag in action_tags:
        if re.search('.*Теги.*', str(action_tag.text)):
            tags = action_tag.find_all('a')
            tags = ', '.join([tag.text for tag in tags])

    # количество комментариев, количество просмотров, рейтинг
    area_holder = article.find('div', class_='area-holder')
    comments_num = area_holder.find('a', class_='comment')
    if comments_num:
        comments_num = comments_num.text
    else:
        comments_num = 0
    view_num = area_holder.find('span', class_='view').text
    action_rating = area_holder.find('span', class_='action_rating-score').text
    action_rating = action_rating.strip()

    return {
        "title": title,
        "description": description,
        "benefits": benefits,
        "date": action_date,
        "img": img,
        "url_official": action_url,
        "participation": participation,
        "timing": timing,
        "other_text": other_text,
        "organizers": organizers,
        "operators": operators,
        "rules_link": rules_link,
        "tags": tags,
        "comments_num": comments_num,
        "view_num": view_num,
        "rating": action_rating
    }


def get_description_after_h2(element):
    """
    Вспомогательная функция для парсинга текста после заголовка
    Для блоков "Призы", "Участие в акции", "Сроки проведения акции"
    :param element:
    :return:
    """
    tags = []
    for tag in element.next_siblings:
        if tag.name == 'h2':
            break

        if tag.name:
            tag_classes = tag.get('class')
            if tag_classes:
                if 'action__org_names' in tag_classes:
                    break
            tags.append(tag.name)

    result = ''
    for tag in tags:
        result += str(element.findNextSibling(tag))
    return result


def parse_comments(link):
    soup_page = get_soup_page_by_link(link)
    soup_page = soup_page.find('section', class_='comment-block')

    # определяем количество страниц с комментариями
    ul_paging = soup_page.find('ul', class_='paging')
    if ul_paging:
        page_count = ul_paging.find_all('li')[-2]
        page_count = int(page_count.find('span').text)
    else:
        page_count = 1

    results = []
    # проходимся по каждой странице с комментариями
    page_start = 1
    for page_number in range(page_start, page_count + 1):
        soup_page = get_soup_page_by_link(link + '?page=' + str(page_number))
        soup_page = soup_page.find('section', class_='comment-block')

        comment_list = soup_page.find('ul', class_='comment-list').find_all('li', class_='comment')
        for li in comment_list:
            username_area = li.find('a', class_='username')
            username = re.sub('<a.+?>', '', str(username_area))
            username = re.sub('<span.+?</a>', '', username)
            login = username_area.find('span', class_='login').text

            comment_date = li.find('span', class_='date').text
            comment_link = li.find('a', class_='comment__findpost')['href']
            rating = li.find('span', class_='result')
            if rating:
                rating = rating.text
            text = li.find('div', class_='comment_text').text

            img = ''
            img_ul = li.find('ul', class_='cl-item-images')
            if img_ul:
                for img_li in img_ul.find_all('li'):
                    img += str(img_li.find('img'))

            results.append({
                'username': username,
                'login': login,
                'date': comment_date,
                'link': comment_link,
                'rating': rating,
                'text': text,
                'img': img
            })

    return results


def get_soup_page_by_link(link):
    browser.get(link)
    response_page = browser.page_source
    time.sleep(random.uniform(5, 8.4))
    soup_page = BeautifulSoup(response_page, 'html.parser')
    return soup_page


parse_brands()
parse_actions()

