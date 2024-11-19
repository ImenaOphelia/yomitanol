#!/usr/bin/env python3

import lxml.html
from selenium import webdriver
import json
import csv
from datetime import datetime

def store_entry(file_handle, url, word, entry_type, structured_data):
    try:
        entry = {
            'url': url,
            'word': word,
            'type': entry_type,
            'data': structured_data,
            'timestamp': datetime.now().isoformat()
        }
        file_handle.write(json.dumps(entry, ensure_ascii=False) + '\n')
        print(f' 💾 {entry_type.capitalize()} "{word}" @ {url} stored')
    except Exception as e:
        print(e, url)

def get_text_content(element):
    return ' '.join(element.xpath('.//text()')).strip() if element is not None else ''

def get_next_word(soup, current_word):
    rueda = soup.xpath('//ul[@class="rueda"]/li/a | //ul[@class="rueda"]/li/b')
    current_found = False
    
    words_in_wheel = [link.text_content().strip() for link in rueda]
    
    for i, link in enumerate(rueda):
        word = link.text_content().strip()
        if current_found:
            next_word = word
            print(f"Found next word: {next_word}")
            return next_word
        if word == current_word:
            current_found = True
            if i == len(rueda) - 1:
                next_word = words_in_wheel[0]
                return next_word
            
    if not current_found:
        print(f"Warning: Could not find {current_word} in the term wheel")
    
    return None

def fetch_page(output_file, driver, url, key_word, grammar_tags, usage_tags, geo_tags, not_found_words, max_retries=3):
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
        return None

    try:
        soup = lxml.html.fromstring(markup)
    except lxml.etree.ParserError as e:
        print(f'Parsing error for "{key_word}" @ {url}: {e}. Skipping...')
        not_found_words.append(url)
        return None

    soup.make_links_absolute(base_url='https://rae.es/diccionario-estudiante/')
    word_element = soup.xpath('//span[@class="entrada"]')
    word = word_element[0].text_content() if word_element else None

    if not word:
        print(f' ❌ No entry found for "{key_word}" @ {url}. Skipping...')
        return None

    structured_data = []
    expressions_data = []

    conjugation_model = None
    plural = None
    participios = []
    note = None
    paracep = soup.xpath('//div[@class="paracep"]')

    # Process paracep if it exists
    if paracep:
        model_span = paracep[0].xpath('.//span[contains(@class, "verboModelo")]')
        plural_span = paracep[0].xpath('.//span[contains(@class, "pluralForm")]')
        note_span = paracep[0].xpath('.//div[contains(@class, "par")]')
        participio_spans = paracep[0].xpath('.//span[contains(@class, "participioIrregular")]')

        if model_span:
            conjugation_model = model_span[0].text_content().strip()
        
        if plural_span:
            plural = plural_span[0].text_content().strip()

        if participio_spans:
            participios = [span.text_content().strip() for span in participio_spans]

        if not conjugation_model and not plural and not participios and note_span:
            note = note_span[0].text_content().strip()

        for acep in paracep[0].xpath('.//div[contains(@class, "acep")]'):
            process_definition(acep, structured_data, grammar_tags, usage_tags, geo_tags)

        for p in paracep:
            p.getparent().remove(p)

    # Process articles
    articles = soup.xpath('//article')
    if articles:
        for article in articles:
            locs_and_sols = article.xpath('.//div[@class="locs"]//div[@class="fc"] | .//div[@class="sols"]//div[@class="fc"]')
            
            for loc in locs_and_sols:
                expression_element = loc.xpath('.//span[@class="headword-fc"]')
                headword = expression_element[0].text_content() if expression_element else key_word

                definition_data = {
                    "id": loc.get('id'),
                    "definition": '',
                    "grammar_tags": [],
                    "usage_tags": [],
                    "geo_tags": [],
                    "examples": [],
                    "synonyms": [],
                    "antonyms": [],
                    "main_entry": key_word,
                    "term_notes": [],
                }

                definition = loc.xpath('.//div[@class="acep nogr"]//span[@class="def"]')
                if definition:
                    definition_data["definition"] = get_text_content(definition[0])

                examples = loc.xpath('.//span[@class="ejemplo"]')
                definition_data["examples"].extend(get_text_content(e) for e in examples)

                note_elements = loc.xpath('.//div[contains(@class, "par")]')
                definition_data["term_notes"].extend(get_text_content(note) for note in note_elements)

                extract_tags(loc, definition_data, grammar_tags, usage_tags, geo_tags)

                extract_synonyms_antonyms(loc, definition_data)

                expr_type = "locution" if "locs" in loc.xpath('ancestor::div/@class')[0] else "solution"
                expressions_data.append({
                    "expression": headword,
                    "type": expr_type,
                    "data": definition_data
                })

            for loc in locs_and_sols:
                loc.getparent().remove(loc)

            for acep in article.xpath('.//div[contains(@class, "acep")]'):
                process_definition(acep, structured_data, grammar_tags, usage_tags, geo_tags)

    if structured_data:
        entry_type = 'verb' if paracep else 'general'
        main_entry = {
            'definitions': structured_data,
            'expressions': [expr['expression'] for expr in expressions_data]
        }

        if conjugation_model and entry_type == 'verb':
            main_entry['conjugation_model'] = conjugation_model

        if plural and entry_type == 'verb':
            main_entry['plural'] = plural

        if participios and entry_type == 'verb':
            main_entry['participios'] = participios

        if note and entry_type == 'verb':
            main_entry['term_note'] = note

        store_entry(output_file, url, key_word, entry_type, main_entry)

    for expr in expressions_data:
        expr_url = f"{url}#{expr['data']['id']}"
        store_entry(output_file, expr_url, expr['expression'], expr['type'], [expr['data']])

    return soup

def process_definition(acep, structured_data, grammar_tags, usage_tags, geo_tags):
    definition_text = get_text_content(acep.xpath('.//span[@class="def"]')[0]) if acep.xpath('.//span[@class="def"]') else ""
    acep_id = acep.get('id')

    if acep_id is None:
        return

    definition_data = {
        "definition": '',
        "grammar_tags": [],
        "usage_tags": [],
        "geo_tags": [],
        "def_notes": [],
        "examples": [],
        "synonyms": [],
        "antonyms": [],
        "id": acep_id
    }

    definition = acep.xpath('.//span[@class="def"]')
    if definition:
        definition_data["definition"] = get_text_content(definition[0])

    for loc in acep.xpath('.//div[@class="locs"]//div[@class="fc"] | .//div[@class="sols"]//div[@class="fc"]'):
        loc.getparent().remove(loc)

    extract_tags(acep, definition_data, grammar_tags, usage_tags, geo_tags)

    examples = acep.xpath('.//span[@class="ejemplo"]')
    definition_data["examples"].extend(get_text_content(e) for e in examples)

    extract_synonyms_antonyms(acep, definition_data)

    extract_notes(acep, definition_data)

    structured_data.append(definition_data)

def extract_notes(element, definition_data):
    if 'def_notes' not in definition_data:
        definition_data['def_notes'] = []
    
    def_notes_tb = element.xpath('.//span[@class="defP"]')
    if def_notes_tb:
        for note in def_notes_tb:
            definition_data["def_notes"].append(get_text_content(note))

    symbols_in_element = element.xpath('.//span[@class="symbol"]')
    for symbol in symbols_in_element:
        symbol_text = symbol.text_content().strip()
        definition_data["def_notes"].append({"symbol": symbol_text})

def extract_tags(element, definition_data, grammar_tags, usage_tags, geo_tags):
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

    geo_tags_in_element = element.xpath(".//abbr[@class='geo']")
    for tag in geo_tags_in_element:
        tag_name = tag.get('title')
        tag_text = tag.text
        definition_data["geo_tags"].append({"tag": tag_text})
        geo_tags[(tag_text, tag_name)] = True
    pass

def extract_synonyms_antonyms(element, definition_data):
    for ref in element.xpath('.//div[contains(@class, "ref")]'):
        ref_type = ref.get('class').replace('ref', '').strip()
        ref_words = [word.strip() for word in ref.xpath('.//a/text()')]
        if ref_type == 'S':  # Synonym
            definition_data["synonyms"].extend(ref_words)
        elif ref_type == 'A':  # Antonym
            definition_data["antonyms"].extend(ref_words)

def save_tags_to_file(tags, filename):
    with open(filename, 'w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(['tag', 'name'])
        for tag, name in sorted(tags.keys()):
            writer.writerow([tag, name])
    pass

if __name__ == '__main__':
    initial_word = "actitud"  # Starting word
    processed_words = set()
    current_word = initial_word
    output_file = open('term_bank_0.jsonl', 'w', encoding='utf-8')
    
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--guest")
    chrome_options.add_argument("--blink-settings=imagesEnabled=false")
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--disable-first-run-ui')
    chrome_options.add_argument('--disable-popup-blocking')
    chrome_options.add_argument('--disable-notifications')
    chrome_options.add_argument('--disable-infobars')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--ignore-certificate-errors')
    chrome_options.add_argument('--ignore-ssl-errors')
    chrome_options.add_argument('--disable-extensions')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('window-size=800,700')
    driver = webdriver.Chrome(options=chrome_options)

    grammar_tags = {}
    usage_tags = {}
    geo_tags = {}
    not_found_words = []

    try:
        while current_word and current_word not in processed_words:
            print(f"\nProcessing word: {current_word}")
            url = f'https://rae.es/diccionario-estudiante/{current_word}'
            soup = fetch_page(output_file, driver, url, current_word, grammar_tags, usage_tags, geo_tags, not_found_words)
            
            if soup is None:
                print(f"Error processing {current_word}, stopping")
                break
                
            processed_words.add(current_word)
            
            next_word = get_next_word(soup, current_word)
            
            if next_word is None:
                break
                
            if next_word == initial_word:
                break
                
            current_word = next_word

    except Exception as e:
        print(f"Unexpected error: {e}")
        
    finally:
        output_file.close()
        
        save_tags_to_file(grammar_tags, 'grammar_tags.csv')
        save_tags_to_file(usage_tags, 'usage_tags.csv')
        save_tags_to_file(geo_tags, 'geo_tags.csv')

        with open('unfound_words.txt', 'w', encoding='utf-8') as f:
            for unfound_word in sorted(not_found_words):
                f.write(f"{unfound_word}\n")

        print('Completed. Quitting...')
        driver.quit()