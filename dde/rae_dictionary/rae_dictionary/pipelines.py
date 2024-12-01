import json
import csv


class RaeDictionaryPipeline:
    def __init__(self):
        self.file = None

    def open_spider(self, spider):
        self.file = open("term_bank_0.jsonl", "a", encoding="utf-8")

    def process_item(self, item, spider):
        line = json.dumps(dict(item), ensure_ascii=False) + "\n"
        self.file.write(line)
        return item

    def close_spider(self, spider):
        if self.file:
            self.file.close()


class TagsPipeline:
    def __init__(self):
        self.grammar_tags = {}
        self.usage_tags = {}
        self.geo_tags = {}
        self.not_found_words = []

    def process_item(self, item, spider):
        if "data" in item and "definitions" in item["data"]:
            for definition in item["data"]["definitions"]:
                self._process_tags(definition)
        return item

    def _process_tags(self, definition):
        for tag in definition.get("grammar_tags", []):
            self.grammar_tags[tag["tag"]] = True
        for tag in definition.get("usage_tags", []):
            self.usage_tags[tag["tag"]] = True
        for tag in definition.get("geo_tags", []):
            self.geo_tags[tag["tag"]] = True

    def close_spider(self, spider):
        self._save_tags_to_file(self.grammar_tags, "grammar_tags.csv")
        self._save_tags_to_file(self.usage_tags, "usage_tags.csv")
        self._save_tags_to_file(self.geo_tags, "geo_tags.csv")

        with open("unfound_words.txt", "w", encoding="utf-8") as f:
            for word in sorted(self.not_found_words):
                f.write(f"{word}\n")

    def _save_tags_to_file(self, tags, filename):
        with open(filename, "w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(["tag", "name"])
            for tag in sorted(tags.keys()):
                writer.writerow([tag, ""])
