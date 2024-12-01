import scrapy
from datetime import datetime
from ..items import DictionaryItem
from scrapy.spiders import CrawlSpider
import urllib.parse
import re
from pathlib import Path
import json
from typing import Tuple


class RaeDictionarySpider(CrawlSpider):
    name = "rae_dictionary"
    allowed_domains = ["rae.es", "www.rae.es"]

    def __init__(self, *args, **kwargs):
        super(RaeDictionarySpider, self).__init__(*args, **kwargs)
        self.processed_words = set()
        self.initial_word = "a"
        self.grammar_tags = {}
        self.usage_tags = {}
        self.geo_tags = {}
        self.plev_tags = {}
        self.domain_tags = {}
        self.redirects_map = {}
        self.not_found_words = []
        self.setup_logging()
        self.failed_urls = set()
        self.output_file = "term_bank_0.jsonl"
        self.processed_words = self.load_processed_words()

        last_word = self.get_last_processed_word()
        if last_word:
            self.start_urls = [
                f"https://www.rae.es/diccionario-estudiante/{urllib.parse.quote(last_word)}"
            ]
            self.logger.info(f"Resuming from last processed word: {last_word}")
        else:
            self.start_urls = ["https://www.rae.es/diccionario-estudiante/a"]
            self.logger.info("Starting from beginning with 'a'")

    def errback_httpbin(self, failure):
        """Handle failed requests after all retries have been exhausted."""
        url = failure.request.url
        self.logger.error(f"Request failed for URL: {url} after all retries")
        self.failed_urls.add(url)

        self.log_unfound_word(url, f"Failed after all retries: {failure.value}")

        referer = failure.request.meta.get("referer")
        if referer:
            yield scrapy.Request(
                referer,
                callback=self.handle_failed_request,
                errback=self.errback_httpbin,
                meta={"failed_word": urllib.parse.unquote(url.split("/")[-1])},
                dont_filter=True,
            )

    def load_processed_words(self):
        """Load already processed words from the output file."""
        processed = set()

        if not Path(self.output_file).exists():
            self.logger.info(f"No existing output file found at {self.output_file}")
            return processed

        try:
            with open(self.output_file, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        entry = json.loads(line.strip())
                        word = entry.get("word")
                        if word:
                            processed.add(self.normalize_word_for_comparison(word))
                    except json.JSONDecodeError:
                        continue

            self.logger.info(
                f"Loaded {len(processed)} processed words from existing output"
            )
            return processed

        except Exception as e:
            self.logger.error(f"Error loading processed words: {str(e)}")
            return processed

    def get_last_processed_word(self):
        """Get the last successfully processed word from the output file."""
        if not Path(self.output_file).exists():
            return None

        try:
            last_word = None
            with open(self.output_file, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        entry = json.loads(line.strip())
                        word = entry.get("word")
                        if word:
                            last_word = word
                    except json.JSONDecodeError:
                        continue
            return last_word

        except Exception as e:
            self.logger.error(f"Error getting last processed word: {str(e)}")
            return None

    def setup_logging(self):
        """Setup logging and file handling."""
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)

        self.unfound_words_file = Path("unfound_words.txt")
        if self.unfound_words_file.exists():
            backup_file = self.unfound_words_file.with_suffix(".bak")
            self.unfound_words_file.rename(backup_file)

        self.unfound_words_file.write_text("", encoding="utf-8")

    def normalize_url(self, url: str) -> str:
        """Normalize URLs to handle spaces and special characters."""
        base_url = "https://www.rae.es/diccionario-estudiante/"
        if url.startswith(base_url):
            word = url[len(base_url) :]
        else:
            word = url

        word = urllib.parse.unquote(word)

        if word.endswith(".") and not self.is_abbreviation(word):
            word = word.rstrip(".")

        word = urllib.parse.quote(word, safe=". ")
        return f"{base_url}{word}"

    def extract_lemma(self, word_element: str, response_url: str) -> Tuple[str, str]:
        """
        Extract the lemma form of the word.
        Returns tuple of (lemma, display_form)
        """
        if not word_element:
            url_word = urllib.parse.unquote(response_url.split("/")[-1])
            if self.is_abbreviation(url_word):
                return url_word, url_word
            return url_word.rstrip("."), url_word

        # Handle cases like "abad, desa" -> "abad"
        display_form = word_element.strip()
        lemma = display_form.split(",")[0].strip()

        return lemma, display_form

    def log_unfound_word(self, url: str, reason: str = "No content found"):
        """Log unfound words."""
        try:
            with open(self.unfound_words_file, "a", encoding="utf-8") as f:
                log_entry = json.dumps(
                    {
                        "url": url,
                        "timestamp": datetime.now().isoformat(),
                        "reason": reason,
                    }
                )
                f.write(f"{log_entry}\n")
        except Exception as e:
            self.logger.error(f"Error logging unfound word {url}: {str(e)}")

    def handle_redirect(self, response):
        """Handle redirects and update redirect map."""
        if response.request.meta.get("redirect_urls"):
            original_url = response.request.meta["redirect_urls"][0]
            final_url = response.url
            original_word = urllib.parse.unquote(original_url.split("/")[-1])
            final_word = urllib.parse.unquote(final_url.split("/")[-1])
            self.redirects_map[original_word] = {
                "target": final_word,
                "original_response": response,
            }
            self.logger.info(f"Redirect detected: {original_word} -> {final_word}")
            return final_word
        return None

    def get_text_content(self, element):
        """Extract and clean text content from an element."""
        if element is None:
            return ""
        text = element.xpath("string()").get("")
        return " ".join(text.split()) if text else ""

    def parse_start_url(self, response):
        """Initial parse method for the start URL."""
        return self.parse_dictionary_entry(response)

    def parse_dictionary_entry(self, response):
        main_page_indicators = [
            "Las voces han sido cuidadosamente seleccionadas",
            "vocabulario fundamental que en su trabajo debe manejar un estudiante",
        ]

        main_page_div = response.xpath(
            '//div[@class="bloque-txt" and @id="resultados"]//text()'
        ).getall()
        main_page_text = " ".join(
            text.strip() for text in main_page_div if text.strip()
        )

        current_url = response.url
        current_word = urllib.parse.unquote(current_url.split("/")[-1])

        if any(indicator in main_page_text for indicator in main_page_indicators):
            self.logger.info(
                f"Main page detected for word: {current_word}. Skipping to next word."
            )
            self.log_unfound_word(current_url, "Main page content detected")

            referer = response.request.headers.get("Referer", b"").decode()
            if referer:
                yield scrapy.Request(
                    referer,
                    callback=self.handle_main_page_redirect,
                    errback=self.errback_httpbin,
                    meta={"problematic_word": current_word},
                    dont_filter=True,
                )
            return

        word_element = response.xpath('//span[@class="entrada"]/text()').get("")
        lemma, display_form = self.extract_lemma(word_element, response.url)

        normalized_lemma = self.normalize_word_for_comparison(lemma)

        if normalized_lemma in self.processed_words:
            self.logger.info(f"Skipping already processed word: {lemma}")
            next_word = self.get_next_word(response, lemma)
            if next_word and next_word != self.initial_word:
                next_url = self.normalize_url(next_word)
                yield scrapy.Request(
                    next_url,
                    callback=self.parse_dictionary_entry,
                    errback=self.errback_httpbin,
                    dont_filter=True,
                )
            return

        self.processed_words.add(normalized_lemma)

        structured_data = []
        expressions_data = []

        self.process_main_definitions(
            response, structured_data, expressions_data, lemma
        )

        if structured_data:
            main_item = self.create_main_item(
                url=response.url,
                lemma=lemma,
                display_form=display_form,
                entry_type="general",
                structured_data=structured_data,
                expressions_data=expressions_data,
            )
            yield main_item

        for expr in expressions_data:
            expr_item = self.create_expression_item(response.url, expr)
            yield expr_item

        next_word = self.get_next_word(response, lemma)
        if next_word and next_word != self.initial_word:
            next_url = self.normalize_url(next_word)
            yield scrapy.Request(
                next_url,
                callback=self.parse_dictionary_entry,
                errback=self.errback_httpbin,
                dont_filter=True,
            )

    def handle_main_page_redirect(self, response):
        """
        Handle redirects from main page by getting the wheel from the previous valid page.
        """
        problematic_word = response.meta["problematic_word"]
        rueda = self.collect_word_wheel(response)

        if rueda:
            self.logger.debug(f"Previous page wheel: {rueda}")
            try:
                current_index = rueda.index(problematic_word)
                if current_index < len(rueda) - 1:
                    next_word = rueda[current_index + 1]
                    self.logger.info(
                        f"Found next word after {problematic_word}: {next_word}"
                    )
                    next_url = self.normalize_url(next_word)
                    yield scrapy.Request(
                        next_url,
                        callback=self.parse_dictionary_entry,
                        errback=self.errback_httpbin,
                        dont_filter=True,
                    )
                else:
                    self.logger.error(f"Word {problematic_word} was last in wheel")
            except ValueError:
                self.logger.error(
                    f"Could not find {problematic_word} in previous page wheel"
                )
        else:
            self.logger.error("Could not get wheel from previous page")

    def get_next_from_previous_wheel(self, response):
        """
        Get the next word from the previous page's wheel, skipping the problematic word.
        """
        skipped_word = response.meta.get("skipped_word")
        rueda = self.collect_word_wheel(response)

        if rueda:
            try:
                current_index = rueda.index(skipped_word)
                if current_index < len(rueda) - 1:
                    next_word = rueda[current_index + 1]
                    next_url = self.normalize_url(next_word)
                    return scrapy.Request(
                        next_url, callback=self.parse_dictionary_entry, dont_filter=True
                    )
            except ValueError:
                self.logger.error(f"Could not find {skipped_word} in wheel")

        self.logger.error(f"Could not find next word after {skipped_word}")
        return None

    def is_abbreviation(self, word: str) -> bool:
        """
        Smarter abbreviation detection using linguistic patterns and context.
        Returns True if the word appears to be an abbreviation.
        """
        if not word:
            return False

        word = word.strip()

        patterns = [
            lambda w: "." in w.rstrip("."),
            lambda w: w.count(".") > 1,
            lambda w: len(w) <= 6 and w.endswith("."),
            lambda w: bool(re.match(r"^[A-Za-z]\.$", w)),
            lambda w: bool(re.match(r"^[A-Za-z]{1,5}\.$", w)),
            lambda w: bool(re.match(r"^[A-Za-z]+\.[A-Za-z]+\.$", w)),
            lambda w: bool(re.match(r"^[A-Za-z]+ón\.$", w)),
            lambda w: bool(re.match(r"^\w+\.\s*\w+\.$", w)),
        ]

        return any(pattern(word) for pattern in patterns)

    def normalize_word_for_comparison(self, word: str) -> str:
        """
        Consistent normalization.
        """
        if not word:
            return ""

        if "/" in word:
            word = word.split("/")[-1]
            word = urllib.parse.unquote(word)

        normalized = word.lower().strip()

        if self.is_abbreviation(normalized):
            parts = [p.strip() for p in normalized.split(".") if p.strip()]
            return ". ".join(parts) + "."

        return " ".join(normalized.split())

    def create_word_normalizer(self):
        """
        Creates a consistent word normalizer function for use across different methods.
        """

        def normalize(word):
            if not word:
                return ""

            word = word.lower().strip()

            if "/" in word:
                word = word.split("/")[-1]
                word = urllib.parse.unquote(word)

            if self.is_abbreviation(word):
                normalized = word.replace(" ", "")
                if not normalized.endswith("."):
                    normalized += "."
                return normalized

            return word.replace(".", "").strip()

        return normalize

    def get_next_word(self, response, current_word):
        """
        Main method to get the next word.
        """
        rueda = self.collect_word_wheel(response)
        if not rueda:
            self.logger.warning(f"Empty word wheel for {current_word}")
            return None

        next_word = self._find_direct_next_word(rueda, current_word)

        if next_word:
            if next_word in self.redirects_map:
                target = self.redirects_map[next_word]["target"]
                if self.normalize_word_for_comparison(target) in self.processed_words:
                    try:
                        current_index = rueda.index(next_word)
                        for i in range(current_index + 1, len(rueda)):
                            candidate = rueda[i]
                            if (
                                candidate not in self.redirects_map
                                and self.normalize_word_for_comparison(candidate)
                                not in self.processed_words
                            ):
                                return self.normalize_url_word(candidate)
                    except ValueError:
                        pass

                    return self._find_alphabetical_next_word(rueda, current_word)

            return self.normalize_url_word(next_word)

        return None

    def collect_word_wheel(self, response):
        """Collect words from the word wheel."""
        rueda = []
        wheel_elements = response.xpath(
            '//ul[@class="rueda"]/li/a | //ul[@class="rueda"]/li/b'
        )

        self.logger.debug("Found wheel elements: %d", len(wheel_elements))

        for element in wheel_elements:
            href = element.xpath("@href").get()
            if href:
                word = href.split("/")[-1]
                word = urllib.parse.unquote(word)
            else:
                word = element.xpath("text()").get("").strip()

            if word:
                rueda.append(word)

        self.logger.debug("Collected wheel words: %s", rueda)
        return rueda

    def _find_direct_next_word(self, rueda, current_word):
        """
        Enhanced next word finding with proper space and abbreviation handling.
        """
        try:
            self.logger.debug(f"Finding next word after: {current_word}")

            normalized_current = self.normalize_word_for_comparison(current_word)

            wheel_mapping = {}
            for wheel_word in rueda:
                normalized_wheel_word = self.normalize_word_for_comparison(wheel_word)
                wheel_mapping[normalized_wheel_word] = wheel_word

            if normalized_current in wheel_mapping:
                current_index = rueda.index(wheel_mapping[normalized_current])
            else:
                normalized_current_no_period = normalized_current.rstrip(".")
                for norm_wheel_word, orig_wheel_word in wheel_mapping.items():
                    if norm_wheel_word.rstrip(".") == normalized_current_no_period:
                        current_index = rueda.index(orig_wheel_word)
                        break
                else:
                    self.logger.warning(f"Word not found in wheel: {current_word}")
                    return self._find_alphabetical_next_word(rueda, current_word)

            for i in range(current_index + 1, len(rueda)):
                candidate = rueda[i]
                normalized_candidate = self.normalize_word_for_comparison(candidate)

                if candidate in self.redirects_map:
                    target = self.redirects_map[candidate]["target"]
                    if (
                        self.normalize_word_for_comparison(target)
                        in self.processed_words
                    ):
                        continue

                if normalized_candidate in self.processed_words:
                    continue

                return candidate

            self.logger.warning(
                f"No suitable next word found in wheel after {current_word}"
            )
            return self._find_alphabetical_next_word(rueda, current_word)

        except Exception as e:
            self.logger.error(f"Error finding next word: {str(e)}")
            return None

    def _find_normalized_next_word(self, rueda, current_word):
        """Try finding next word with normalized current word."""
        try:
            normalized_word = urllib.parse.unquote(current_word)
            current_index = rueda.index(normalized_word)
            next_word = (
                rueda[current_index + 1] if current_index < len(rueda) - 1 else rueda[0]
            )
            return urllib.parse.quote(next_word)
        except ValueError:
            return None

    def _find_redirected_next_word(self, rueda, current_word):
        """Check if word was redirected and use redirected word."""
        redirected_word = self.redirects_map.get(current_word)
        if redirected_word:
            return self._find_direct_next_word(rueda, redirected_word)
        return None

    def _find_word_with_fallback(self, rueda, current_word):
        """
        Implements multiple fallback strategies for finding the next word.
        """
        normalize = self.create_word_normalizer()
        normalized_current = normalize(current_word)

        strategies = [
            lambda: self._find_alphabetical_next_word(rueda, normalized_current),
            lambda: self._find_with_period_variation(rueda, normalized_current),
            lambda: self._find_partial_match(rueda, normalized_current),
            lambda: rueda[0] if rueda else None,
        ]

        for strategy in strategies:
            result = strategy()
            if result:
                return self.normalize_url_word(result)

        return None

    def _find_alphabetical_next_word(self, rueda, normalized_word):
        """Find the next word alphabetically."""
        sorted_words = sorted(rueda, key=self.create_word_normalizer())
        for word in sorted_words:
            if self.create_word_normalizer()(word) > normalized_word:
                return word
        return None

    def _find_with_period_variation(self, rueda, normalized_word):
        """Try matching with and without trailing period."""
        normalize = self.create_word_normalizer()
        variations = [normalized_word]

        if normalized_word.endswith("."):
            variations.append(normalized_word[:-1])
        else:
            variations.append(normalized_word + ".")

        for word in rueda:
            if normalize(word) in variations:
                return word
        return None

    def _find_partial_match(self, rueda, normalized_word):
        """Find partial matches for abbreviated forms."""
        normalize = self.create_word_normalizer()

        search_term = normalized_word.rstrip(".")

        for word in rueda:
            normalized = normalize(word).rstrip(".")
            if normalized.startswith(search_term):
                return word
        return None

    def normalize_url_word(self, word: str) -> str:
        """
        Normalize a word for use in URLs while preserving abbreviation structure and spaces.
        """
        if not word:
            return ""

        if self.is_abbreviation(word):
            normalized = word.strip()
            parts = [p.strip() for p in normalized.split(".") if p.strip()]
            normalized = ". ".join(parts)
            if not normalized.endswith("."):
                normalized += "."
            return urllib.parse.quote(normalized, safe=" .")

        normalized = word.strip().rstrip(".")
        return urllib.parse.quote(normalized, safe=" ")

    def extract_paracep_details(self, paracep):
        """Extracts details from the paracep section of the response."""
        details = {
            "conjugation_model": None,
            "plural": None,
            "participios": [],
            "note": None,
        }

        if paracep:
            details["conjugation_model"] = paracep.xpath(
                './/span[contains(@class, "verboModelo")]/text()'
            ).get()
            details["plural"] = paracep.xpath(
                './/span[contains(@class, "pluralForm")]/text()'
            ).get()
            details["participios"] = paracep.xpath(
                './/span[contains(@class, "participioIrregular")]/text()'
            ).getall()
            details["note"] = paracep.xpath(
                './/div[contains(@class, "par")]/text()'
            ).get()

        return details

    def process_main_definitions(
        self, response, structured_data, expressions_data, lemma
    ):
        """Process definitions found in the main article section."""
        for article in response.xpath("//article"):
            self.process_article(article, structured_data, expressions_data, lemma)

    def process_article(self, article, structured_data, expressions_data, current_word):
        """Process an article element and extract definitions and expressions."""
        processed_ids = set()

        locs_and_sols = article.xpath(
            './/div[@class="locs"]//div[@class="fc"] | .//div[@class="sols"]//div[@class="fc"]'
        )
        for loc in locs_and_sols:
            loc_id = loc.attrib.get("id")
            if loc_id in processed_ids:
                continue
            processed_ids.add(loc_id)

            headword = loc.xpath('string(.//span[@class="headword-fc"])').get().strip()

            definition_data = self.create_definition_data(loc)

            expr_type = (
                "locution"
                if loc.xpath("ancestor::div/@class").get("").find("locs") != -1
                else "solution"
            )
            expressions_data.append(
                {
                    "expression": headword,
                    "type": expr_type,
                    "data": definition_data,
                }
            )

        for acep in article.xpath('.//div[contains(@class, "acep")]'):
            if not acep.xpath(
                'ancestor::div[contains(@class, "locs") or contains(@class, "sols")]'
            ):
                self.process_definition(acep, structured_data)

        for paracep in article.xpath('.//div[@class="fc"]'):
            paracep_id = paracep.attrib.get("id")
            if paracep_id in processed_ids:
                continue
            processed_ids.add(paracep_id)

            self.process_paracep(paracep, expressions_data, processed_ids)

    def process_paracep(self, paracep, expressions_data, current_word, processed_ids):
        """Process paracep expressions and add them to expressions_data."""
        headword = paracep.xpath('.//span[@class="headword-fc"]//text()').getall()
        headword = " ".join(word.strip() for word in headword if word.strip())

        plural = paracep.xpath('.//span[contains(@class, "pluralForm")]/text()').get()
        participios = paracep.xpath(
            './/span[contains(@class, "participioIrregular")]/text()'
        ).getall()
        note = paracep.xpath('.//div[contains(@class, "par")]/text()').get()

        for acep in paracep.xpath('.//div[contains(@class, "acep")]'):

            acep_id = acep.attrib.get("id")
            if acep_id in processed_ids:
                continue
            processed_ids.add(acep_id)

            definition_data = self.create_definition_data(acep)

            if plural:
                definition_data["plural"] = plural.strip()
            if participios:
                definition_data["participios"] = [
                    p.strip() for p in participios if p.strip()
                ]
            if note:
                definition_data["term_notes"].append(note.strip())

            expressions_data.append(
                {"expression": headword, "type": "solution", "data": definition_data}
            )

    def create_main_item(
        self,
        url,
        lemma,
        display_form,
        entry_type,
        structured_data,
        expressions_data,
        conjugation_model=None,
        plural=None,
        participios=None,
        note=None,
    ):
        """Create the main dictionary item."""
        item = DictionaryItem()
        item["url"] = url
        item["word"] = lemma
        item["type"] = entry_type
        item["data"] = {
            "definitions": structured_data,
            "expressions": sorted(set(expr["expression"] for expr in expressions_data)),
            "display_form": display_form,
        }

        if conjugation_model:
            item["data"]["conjugation_model"] = conjugation_model.strip()
        if plural:
            item["data"]["plural"] = plural.strip()
        if participios:
            item["data"]["participios"] = [p.strip() for p in participios if p.strip()]
        if note:
            item["data"]["term_note"] = note.strip()

        item["timestamp"] = datetime.now().isoformat()
        return item

    def process_definition(self, acep, structured_data):
        """Process a definition element and extract its data."""
        acep_id = acep.attrib.get("id")
        if any(d.get("id") == acep_id for d in structured_data):
            return

        definition_data = self.create_definition_data(acep)
        if definition_data["definition"]:
            structured_data.append(definition_data)

    def create_definition_data(self, element):
        """Create a structured definition data dictionary."""
        definition_data = {
            "id": element.attrib.get("id"),
            "definition": "",
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

        definition = element.xpath(
            './/div[@class="acep nogr"]//span[@class="def"] | .//span[@class="def"]'
        )
        if definition:
            definition_data["definition"] = self.get_text_content(definition[0])

        examples = element.xpath('.//span[@class="ejemplo"]')
        definition_data["examples"].extend(
            self.get_text_content(e) for e in examples if self.get_text_content(e)
        )

        note_elements = element.xpath('.//div[contains(@class, "par")]')
        if not element.xpath(
            'ancestor::div[contains(@class, "locs") or contains(@class, "sols")]'
        ):
            definition_data["term_notes"].extend(
                self.get_text_content(note)
                for note in note_elements
                if self.get_text_content(note)
            )

        self.extract_tags(element, definition_data)
        self.extract_synonyms_antonyms(element, definition_data)

        return definition_data

    def create_expression_item(self, base_url, expr):
        """Create an item for an expression."""
        item = DictionaryItem()
        item["url"] = (
            f"{base_url}#{expr['data']['id']}" if expr["data"].get("id") else base_url
        )
        item["word"] = expr["expression"]
        item["type"] = expr["type"]
        item["data"] = [expr["data"]]
        item["timestamp"] = datetime.now().isoformat()
        return item

    def extract_tags(self, element, definition_data):
        """Extract tags from the given element."""
        grammar_tags_in_element = element.xpath(
            ".//abbr[contains(@class, 'gram') or contains(@class, 'gram primera')]"
        )
        for tag in grammar_tags_in_element:
            tag_name = tag.xpath("@title").get("")
            tag_text = tag.xpath("text()").get("")
            if tag_text:
                definition_data["grammar_tags"].append({"tag": tag_text})
                self.grammar_tags[(tag_text, tag_name)] = True

        usage_tags_in_element = element.xpath(".//abbr[contains(@class, 'register')]")
        for tag in usage_tags_in_element:
            tag_name = tag.xpath("@title").get("")
            tag_text = tag.xpath("text()").get("")
            if tag_text:
                definition_data["usage_tags"].append({"tag": tag_text})
                self.usage_tags[(tag_text, tag_name)] = True

        geo_tags_in_element = element.xpath(".//abbr[contains(@class, 'geo')]")
        for tag in geo_tags_in_element:
            tag_name = tag.xpath("@title").get("")
            tag_text = tag.xpath("text()").get("")
            if tag_text:
                definition_data["geo_tags"].append({"tag": tag_text})
                self.geo_tags[(tag_text, tag_name)] = True

        plev_tags_in_element = element.xpath(".//abbr[contains(@class, 'plev')]")
        for tag in plev_tags_in_element:
            tag_name = tag.xpath("@title").get("")
            tag_text = tag.xpath("text()").get("")
            if tag_text:
                definition_data["plev_tags"].append({"tag": tag_text})
                self.plev_tags[(tag_text, tag_name)] = True

        domain_tags_in_element = element.xpath(".//abbr[contains(@class, 'domain')]")
        for tag in domain_tags_in_element:
            tag_name = tag.xpath("@title").get("")
            tag_text = tag.xpath("text()").get("")
            if tag_text:
                definition_data["domain_tags"].append({"tag": tag_text})
                self.domain_tags[(tag_text, tag_name)] = True

    def extract_synonyms_antonyms(self, element, definition_data):
        """Extract synonyms and antonyms from the given element."""
        for ref in element.xpath('.//div[contains(@class, "ref")]'):
            ref_type = ref.xpath("@class").get("").replace("ref", "").strip()
            ref_words = ref.xpath(".//a/text()").getall()
            ref_words = [word.strip() for word in ref_words if word.strip()]
            if ref_type == "S":  # Synonym
                definition_data["synonyms"].extend(ref_words)
            elif ref_type == "A":  # Antonym
                definition_data["antonyms"].extend(ref_words)

    def extract_notes(self, element, definition_data):
        """Extract notes from the given element."""
        if "def_notes" not in definition_data:
            definition_data["def_notes"] = []

        def_notes_tb = element.xpath('.//span[@class="defP"]')
        if def_notes_tb:
            for note in def_notes_tb:
                definition_data["def_notes"].append(self.get_text_content(note))

        symbols_in_element = element.xpath('.//span[@class="symbol"]')
        for symbol in symbols_in_element:
            symbol_text = symbol.text.strip()
            definition_data["def_notes"].append({"symbol": symbol_text})
