#!/usr/bin/env python3

import lxml.html
from selenium import webdriver
import sqlite3
import json
import csv

def init_db(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS dde (
        id integer PRIMARY KEY autoincrement,
        url text NOT NULL UNIQUE,
        word text,
        type text,  -- 'verb' or 'expression'
        structured_data text,  -- Store data in JSON format
        time DATETIME DEFAULT CURRENT_TIMESTAMP
    )""")

    return conn, cursor

def store_entry(url, word, entry_type, structured_data):
    try:
        cur.execute('''
        INSERT INTO dde (
            url, word, type, structured_data
        ) VALUES (?, ?, ?, ?)
        ''', [url, word, entry_type, json.dumps(structured_data, ensure_ascii=False)])

        con.commit()
        print(f' 💾 {entry_type.capitalize()} "{word}" @ {url} stored')
    except Exception as e:
        print(e, url)

def fetch_page(driver, url, key_word, grammar_tags, usage_tags, not_found_words, max_retries=3):
    cur.execute('SELECT count(*) FROM dde WHERE url=?', (url,))
    count = cur.fetchone()[0]
    if count == 1:
        print(f'SKIPPING: URL already saved {url}')
        return

    retries = 0
    markup = ''

    while retries < max_retries:
        print(f'Fetching {url}... Attempt {retries + 1}/{max_retries}')
        driver.get(url)
        markup = driver.page_source.strip()

        if markup:
            break
        else:
            print(f'Warning: Empty document retrieved for "{key_word}" @ {url}')
            retries += 1

    if not markup:
        not_found_words.append(url)
        print(f' ❌ No valid content found for "{key_word}" @ {url} after {max_retries} attempts. Skipping...')
        return

    try:
        soup = lxml.html.fromstring(markup)
    except lxml.etree.ParserError as e:
        print(f'Parsing error for "{key_word}" @ {url}: {e}. Skipping...')
        not_found_words.append(url)
        return

    soup.make_links_absolute(base_url='https://rae.es/diccionario-estudiante/')

    word_element = soup.xpath('//span[@class="entrada"]')
    word = word_element[0].text_content() if word_element else None

    if not word:
        print(f' ❌ No entry found for "{key_word}" @ {url}. Skipping...')
        return

    structured_data = []

    paracep = soup.xpath('//div[@class="paracep"]')
    if paracep:
        for acep in paracep[0].xpath('.//div[contains(@class, "acep")]'):
            definition_data = {
                "definition": '',
                "grammar_tags": [],
                "usage_tags": [],
                "examples": [],
                "synonyms": [],
                "antonyms": []
            }

            definition = acep.xpath('.//span[@class="def"]/text()')
            if definition:
                definition_data["definition"] = ' '.join(definition)

            extract_tags(acep, definition_data, grammar_tags, usage_tags)

            example_elements = acep.xpath('.//span[@class="ejemplo"]/text()')
            definition_data["examples"].extend(example_elements)

            extract_synonyms_antonyms(acep, definition_data)

            structured_data.append(definition_data)

    articles = soup.xpath('//article')
    if articles:
        for article in articles:
            for acep in article.xpath('.//div[contains(@class, "acep")]'):
                definition_data = {
                    "definition": '',
                    "grammar_tags": [],
                    "usage_tags": [],
                    "examples": [],
                    "synonyms": [],
                    "antonyms": []
                }

                definition = acep.xpath('.//span[@class="def"]/text()')
                if definition:
                    definition_data["definition"] = ' '.join(definition)

                extract_tags(acep, definition_data, grammar_tags, usage_tags)

                example_elements = acep.xpath('.//span[@class="ejemplo"]/text()')
                definition_data["examples"].extend(example_elements)

                extract_synonyms_antonyms(acep, definition_data)

                structured_data.append(definition_data)

    locs_and_sols = article.xpath('.//div[@class="locs"]//div[@class="fc"] | .//div[@class="sols"]//div[@class="fc"]')
    if locs_and_sols:
        for loc in locs_and_sols:
            expression_element = loc.xpath('.//span[@class="headword-fc"]')
            headword = expression_element[0].text_content() if expression_element else key_word

            definition_data = {
                "definition": '',
                "grammar_tags": [],
                "usage_tags": [],
                "examples": []
            }

            definition = loc.xpath('.//div[@class="acep nogr"]//span[@class="def"]/text()')
            if definition:
                definition_data["definition"] = ' '.join(definition)

            extract_tags(loc, definition_data, grammar_tags, usage_tags)

            examples_loc = loc.xpath('.//div[@class="acep nogr"]//span[@class="ejemplo"]/text()')
            definition_data["examples"].extend(examples_loc)

            expression_url = f"{url}#{loc.get('id')}"

            if headword:
                store_entry(expression_url, headword, 'expression', [definition_data])


    store_entry(url, key_word, 'verb' if paracep else 'general', structured_data)



def extract_tags(element, definition_data, grammar_tags, usage_tags):
    grammar_tags_in_element = element.xpath(".//abbr[@class='gram' or @class='gram primera']")
    for tag in grammar_tags_in_element:
        tag_name = tag.get('title')
        tag_text = tag.text
        definition_data["grammar_tags"].append({"tag": tag_text})
        grammar_tags[(tag_text, tag_name)] = True

    usage_tags_in_element = element.xpath(".//abbr[@class='register']")
    for tag in usage_tags_in_element:
        tag_name = tag.get('title')
        tag_text = tag.text
        definition_data["usage_tags"].append({"tag": tag_text})
        usage_tags[(tag_text, tag_name)] = True

def extract_synonyms_antonyms(acep, definition_data):
    for ref in acep.xpath('.//div[contains(@class, "ref")]'):
        ref_type = ref.get('class').replace('ref', '').strip()
        ref_word = ref.xpath('.//a/text()')
        if ref_type == 'S':  # Synonym
            definition_data["synonyms"].extend(ref_word)
        elif ref_type == 'A':  # Antonym
            definition_data["antonyms"].extend(ref_word)

def save_tags_to_file(tags, filename):
    with open(filename, 'w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(['tag', 'name'])
        for tag, name in sorted(tags.keys()):
            writer.writerow([tag, name])

if __name__ == '__main__':
    words = open('dde_keys.txt', encoding='utf-8').readlines()
    words = [w.strip().rstrip('.') for w in words]
    words = [w.split(',')[0] if ',' in w else w for w in words]

    try:
        with open('unfound_words.txt', 'r', encoding='utf-8') as f:
            unfound_words = set(line.strip() for line in f)
    except FileNotFoundError:
        unfound_words = set()

    words = [word for word in words if word not in unfound_words]

    con, cur = init_db('dde2.db')

    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--ignore-certificate-errors')
    chrome_options.add_argument('--ignore-ssl-errors')
    chrome_options.add_argument('--disable-extensions')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('window-size=800,700')

    driver = webdriver.Chrome(options=chrome_options)

    grammar_tags = {}
    usage_tags = {}

    for word in words:
        url = f'https://rae.es/diccionario-estudiante/{word}'
        fetch_page(driver, url, word, grammar_tags, usage_tags, unfound_words)

    save_tags_to_file(grammar_tags, 'grammar_tags.csv')
    save_tags_to_file(usage_tags, 'usage_tags.csv')

    with open('unfound_words.txt', 'w', encoding='utf-8') as f:
        for unfound_word in sorted(unfound_words):
            f.write(f"{unfound_word}\n")

    print('Completed. Quitting...')
    driver.quit()
