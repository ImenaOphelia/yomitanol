import scrapy
from datetime import datetime
from ..items import DictionaryItem
from scrapy.exceptions import DropItem
from scrapy.spiders import CrawlSpider
import urllib.parse
import logging

class RaeDictionarySpider(CrawlSpider):
    name = 'rae_dictionary'
    allowed_domains = ['rae.es']
    start_urls = ['https://rae.es/diccionario-estudiante/coche']

    def __init__(self, *args, **kwargs):
        super(RaeDictionarySpider, self).__init__(*args, **kwargs)
        self.processed_words = set()
        self.initial_word = 'coche'
        self.grammar_tags = {}
        self.usage_tags = {}
        self.geo_tags = {}
        self.plev_tags = {}
        self.domain_tags = {}
        self.not_found_words = []
        with open('unfound_words.txt', 'w', encoding='utf-8') as f:
            f.write('')

    def get_text_content(self, element):
        """Extract and clean text content from an element."""
        if element is None:
            return ''
    # Use string() to get all text content, including nested elements
        text = element.xpath('string()').get('')
        return ' '.join(text.split()) if text else ''

    def parse_start_url(self, response):
        """Initial parse method for the start URL."""
        return self.parse_dictionary_entry(response)

    def parse_dictionary_entry(self, response):
        """Main parsing method for dictionary entries."""
        if not response.xpath('//span[@class="entrada"]'):
            self.logger.warning(f"No entry found at {response.url}")
            self.logger.debug(response.text)  # Log the response body to verify its content
            return
        word_element = response.xpath('//span[@class="entrada"]/text()').get('')
    
        if not word_element:
            self.not_found_words.append(response.url)
            self.logger.warning(f"No entry found at {response.url}")
            with open('unfound_words.txt', 'a', encoding='utf-8') as f:
                f.write(f"{response.url}\n")
                
            current_word = word_element.strip() if word_element else urllib.parse.unquote(response.url.split('/')[-1])
            next_word = self.get_next_word(response, current_word)
            if next_word and next_word != self.initial_word:
                next_url = f'https://rae.es/diccionario-estudiante/{next_word}'
                yield scrapy.Request(next_url, 
                                    callback=self.parse_dictionary_entry,
                                    dont_filter=True)
            return

        current_word = word_element.strip()
    
        if current_word in self.processed_words:
            self.logger.info(f"Word already processed: {current_word}")
            return

        self.processed_words.add(current_word)
        structured_data = []
        expressions_data = []

    # Process paracep section
        paracep = response.xpath('//div[@class="paracep"]')
        conjugation_model = None
        plural = None
        participios = []
        note = None

        if paracep:
            conjugation_model = paracep.xpath('.//span[contains(@class, "verboModelo")]/text()').get()
            plural = paracep.xpath('.//span[contains(@class, "pluralForm")]/text()').get()
            participios = paracep.xpath('.//span[contains(@class, "participioIrregular")]/text()').getall()
            note = paracep.xpath('.//div[contains(@class, "par")]/text()').get()

            for acep in paracep.xpath('.//div[contains(@class, "acep")]'):
                self.process_definition(acep, structured_data)

    # Process articles
        for article in response.xpath('//article'):
        # Remove locutions and solutions before processing definitions
            locs_and_sols = article.xpath(
                './/div[@class="locs"]//div[@class="fc"] | .//div[@class="sols"]//div[@class="fc"]'
            )
        
            for loc in locs_and_sols:
                expression_element = loc.xpath('.//span[@class="headword-fc"]')
                headword = expression_element.xpath('string()').get('').strip() if expression_element else current_word

                definition_data = self.create_definition_data(loc)
            
                expr_type = "locution" if loc.xpath('ancestor::div/@class').get('').find('locs') != -1 else "solution"
                expressions_data.append({
                    "expression": headword,
                    "type": expr_type,
                    "data": definition_data
                })

        # Process remaining definitions
            for acep in article.xpath('.//div[contains(@class, "acep")]'):
                if not acep.xpath('ancestor::div[contains(@class, "locs") or contains(@class, "sols")]'):
                    self.process_definition(acep, structured_data)

    # Generate items
        if structured_data:
            entry_type = 'verb' if paracep else 'general'
            main_item = self.create_main_item(
                response.url,
                current_word,
                entry_type,
                structured_data,
                expressions_data,
                conjugation_model,
                plural,
                participios,
                note
            )
            yield main_item

    # Process expressions
        for expr in expressions_data:
            expr_item = self.create_expression_item(response.url, expr)
            yield expr_item

    # Find and follow next word
        next_word = self.get_next_word(response, current_word)
        if next_word and next_word != self.initial_word:
            next_url = f'https://rae.es/diccionario-estudiante/{next_word}'
            yield scrapy.Request(next_url, callback=self.parse_dictionary_entry)

    def create_main_item(self, url, word, entry_type, structured_data, expressions_data,
                        conjugation_model=None, plural=None, participios=None, note=None):
        """Create the main dictionary item."""
        item = DictionaryItem()
        item['url'] = url
        item['word'] = word
        item['type'] = entry_type
        item['data'] = {
            'definitions': structured_data,
            'expressions': [expr['expression'] for expr in expressions_data]
        }

        if conjugation_model:
            item['data']['conjugation_model'] = conjugation_model.strip()
        if plural:
            item['data']['plural'] = plural.strip()
        if participios:
            item['data']['participios'] = [p.strip() for p in participios if p.strip()]
        if note:
            item['data']['term_note'] = note.strip()

        item['timestamp'] = datetime.now().isoformat()
        return item

    def create_expression_item(self, base_url, expr):
        """Create an item for an expression."""
        item = DictionaryItem()
        item['url'] = f"{base_url}#{expr['data']['id']}"
        item['word'] = expr['expression']
        item['type'] = expr['type']
        item['data'] = [expr['data']]
        item['timestamp'] = datetime.now().isoformat()
        return item

    def process_article(self, article, structured_data, expressions_data, current_word):
        """Process an article element and extract its data."""
        locs_and_sols = article.xpath(
            './/div[@class="locs"]//div[@class="fc"] | .//div[@class="sols"]//div[@class="fc"]'
        )
        
        for loc in locs_and_sols:
            expression_element = loc.xpath('.//span[@class="headword-fc"]')
            headword = expression_element.xpath('string()').get('').strip() if expression_element else current_word

            definition_data = self.create_definition_data(loc)
            
            expr_type = "locution" if loc.xpath('ancestor::div/@class').get('').find('locs') != -1 else "solution"
            expressions_data.append({
                "expression": headword,
                "type": expr_type,
                "data": definition_data
            })

        # Process remaining definitions
        for acep in article.xpath('.//div[contains(@class, "acep")]'):
            self.process_definition(acep, structured_data)

    def create_definition_data(self, element):
        """Create a structured definition data dictionary."""
        definition_data = {
            "id": element.attrib.get('id'),
            "definition": '',
            "grammar_tags": [],
            "usage_tags": [],
            "geo_tags": [],
            "plev_tags": [],
            "domain_tags": [],
            "examples": [],
            "synonyms": [],
            "antonyms": [],
            "term_notes": [],
        }

    # Extract definition
        definition = element.xpath('.//div[@class="acep nogr"]//span[@class="def"] | .//span[@class="def"]')
        if definition:
            definition_data["definition"] = self.get_text_content(definition[0])

    # Extract examples
        examples = element.xpath('.//span[@class="ejemplo"]')
        definition_data["examples"].extend(
            self.get_text_content(e) for e in examples if self.get_text_content(e)
        )

    # Extract notes
        note_elements = element.xpath('.//div[contains(@class, "par")]')
        definition_data["term_notes"].extend(
            self.get_text_content(note) for note in note_elements if self.get_text_content(note)
        )

    # Extract tags, synonyms, and antonyms
        self.extract_tags(element, definition_data)
        self.extract_synonyms_antonyms(element, definition_data)

        return definition_data
    
    def process_definition(self, acep, structured_data):
        """Process a definition element and extract its data."""
    # Skip if already processed
        acep_id = acep.attrib.get('id')
        if any(d.get('id') == acep_id for d in structured_data):
            return

        definition_data = {
            "definition": '',
            "grammar_tags": [],
            "usage_tags": [],
            "geo_tags": [],
            "plev_tags": [],
            "domain_tags": [],
            "def_notes": [],
            "examples": [],
            "synonyms": [],
            "antonyms": [],
            "id": acep_id
        }

    # Extract definition text
        definition = acep.xpath('.//span[@class="def"]')
        if definition:
            definition_data["definition"] = self.get_text_content(definition[0])

    # Extract tags
        self.extract_tags(acep, definition_data)

    # Extract examples
        examples = acep.xpath('.//span[@class="ejemplo"]')
        definition_data["examples"].extend(
            self.get_text_content(e) for e in examples if self.get_text_content(e)
        )

    # Extract synonyms and antonyms
        self.extract_synonyms_antonyms(acep, definition_data)

    # Extract notes
        self.extract_notes(acep, definition_data)

    # Only add if we have a definition
        if definition_data["definition"]:
            structured_data.append(definition_data)

    def extract_tags(self, element, definition_data):
        """Extract tags from the given element."""
        grammar_tags_in_element = element.xpath(".//abbr[contains(@class, 'gram') or contains(@class, 'gram primera')]")
        for tag in grammar_tags_in_element:
            tag_name = tag.xpath('@title').get('')
            tag_text = tag.xpath('text()').get('')
            if tag_text:
                definition_data["grammar_tags"].append({"tag": tag_text})
                self.grammar_tags[(tag_text, tag_name)] = True

        usage_tags_in_element = element.xpath(".//abbr[contains(@class, 'register')]")
        for tag in usage_tags_in_element:
            tag_name = tag.xpath('@title').get('')
            tag_text = tag.xpath('text()').get('')
            if tag_text:
                definition_data["usage_tags"].append({"tag": tag_text})
                self.usage_tags[(tag_text, tag_name)] = True

        geo_tags_in_element = element.xpath(".//abbr[contains(@class, 'geo')]")
        for tag in geo_tags_in_element:
            tag_name = tag.xpath('@title').get('')
            tag_text = tag.xpath('text()').get('')
            if tag_text:
                definition_data["geo_tags"].append({"tag": tag_text})
                self.geo_tags[(tag_text, tag_name)] = True
        
        plev_tags_in_element = element.xpath(".//abbr[contains(@class, 'plev')]")
        for tag in plev_tags_in_element:
            tag_name = tag.xpath('@title').get('')
            tag_text = tag.xpath('text()').get('')
            if tag_text:
                definition_data["plev_tags"].append({"tag": tag_text})
                self.plev_tags[(tag_text, tag_name)] = True
                
        domain_tags_in_element = element.xpath(".//abbr[contains(@class, 'domain')]")
        for tag in domain_tags_in_element:
            tag_name = tag.xpath('@title').get('')
            tag_text = tag.xpath('text()').get('')
            if tag_text:
                definition_data["domain_tags"].append({"tag": tag_text})
                self.domain_tags[(tag_text, tag_name)] = True

    def extract_synonyms_antonyms(self, element, definition_data):
        """Extract synonyms and antonyms from the given element."""
        for ref in element.xpath('.//div[contains(@class, "ref")]'):
            ref_type = ref.xpath('@class').get('').replace('ref', '').strip()
            ref_words = ref.xpath('.//a/text()').getall()
            ref_words = [word.strip() for word in ref_words if word.strip()]
            if ref_type == 'S':  # Synonym
                definition_data["synonyms"].extend(ref_words)
            elif ref_type == 'A':  # Antonym
                definition_data["antonyms"].extend(ref_words)

    def extract_notes(self, element, definition_data):
        """Extract notes from the given element."""
        if 'def_notes' not in definition_data:
            definition_data['def_notes'] = []
    
        def_notes_tb = element.xpath('.//span[@class="defP"]')
        if def_notes_tb:
            for note in def_notes_tb:
                definition_data["def_notes"].append(self.get_text_content(note))

        symbols_in_element = element.xpath('.//span[@class="symbol"]')
        for symbol in symbols_in_element:
            symbol_text = symbol.text.strip()
            definition_data["def_notes"].append({"symbol": symbol_text})

    def get_next_word(self, response, current_word):
        """Get the next word from the response."""
        rueda = []
        for element in response.xpath('//ul[@class="rueda"]/li/a | //ul[@class="rueda"]/li/b'):
            main_text = element.xpath('text()').get('')
            word = main_text
            word = word.strip()
            if word:
                rueda.append(word)
    
        try:
            current_index = rueda.index(current_word)
            next_word = rueda[current_index + 1] if current_index < len(rueda) - 1 else rueda[0]
            self.logger.info(f"Current word: {current_word}, Next word: {next_word}")
            return urllib.parse.quote(next_word)
        except ValueError:
            try:
                cleaned_word = urllib.parse.unquote(current_word).strip()
                current_index = rueda.index(cleaned_word)
                next_word = rueda[current_index + 1] if current_index < len(rueda) - 1 else rueda[0]
                self.logger.info(f"Found using cleaned URL word. Current word: {cleaned_word}, Next word: {next_word}")
                return urllib.parse.quote(next_word)
            except ValueError:
                self.logger.warning(f"Could not find neither '{current_word}' nor '{cleaned_word}' in the term wheel: {rueda}")
                try:
                    sorted_rueda = sorted(rueda)
                    # Find the next alphabetical word
                    for i, word in enumerate(sorted_rueda):
                        if word > cleaned_word:
                            # Get the word after the next one
                            if i + 1 < len(sorted_rueda):
                                next_word = sorted_rueda[i + 1]
                                self.logger.info(f"Found next+1 alphabetical word: {next_word}")
                                return urllib.parse.quote(next_word)
                            # If we're at the end, wrap around to the first word
                            else:
                                self.logger.info(f"Using first word in wheel: {sorted_rueda[0]}")
                                return urllib.parse.quote(sorted_rueda[0])
                    if sorted_rueda:
                        self.logger.info(f"Using first word in wheel: {sorted_rueda[0]}")
                        return urllib.parse.quote(sorted_rueda[0])
                except Exception as e:
                    self.logger.error(f"Error finding next word: {e}")
                return None
