import sqlite3
import json
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

grammar_rule_mapping = {
    "adj.": "adj",
    "aux.": "v",
    "copul.": "v",
    "intr.": "v",
    "reg.": "v",
    "tr.": "v",
    "v.": "v",
    "m.": "n",
    "f.": "n",
    "n.": "n"
}

def convert_to_yomitan_format(db_path, output_path):
    logging.info("Starting the conversion process.")
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        logging.info(f"Connected to the database: {db_path}")
    except sqlite3.Error as e:
        logging.error(f"Error connecting to the database: {e}")
        return

    try:
        cursor.execute("SELECT word, structured_data FROM dde")
        rows = cursor.fetchall()
        logging.info(f"Fetched {len(rows)} rows from the database.")
    except sqlite3.Error as e:
        logging.error(f"Error fetching data from the database: {e}")
        conn.close()
        return

    yomitan_entries = []

    for row in rows:
        word = row[0]
        structured_data = json.loads(row[1])
        logging.info(f"Processing word: {word}")

        reading = ""

        for entry in structured_data:
            definition = entry.get('definition', '')
            logging.debug(f"Definition found: {definition}")

            grammar_tags = [tag['tag'].replace(' ', '-') for tag in entry.get('grammar_tags', [])]
            usage_tags = [tag['tag'].replace(' ', '-') for tag in entry.get('usage_tags', [])]
            definition_tags = ' '.join(grammar_tags + usage_tags)
            logging.debug(f"Combined definition tags: {definition_tags}")

            rule_identifier = ""
            for tag in grammar_tags:
                if tag in grammar_rule_mapping:
                    rule_identifier = grammar_rule_mapping[tag]
                    (f'Rule identifier "{rule_identifier}" assigned for grammar tag "{tag}".')
                    break

            score = 0

            definitions = []
            if 'examples' in entry and entry['examples']:
                structured_content = {
                    "type": "structured-content",
                    "content": [definition]
                }
                examples_content = []
                for example in entry['examples']:
                    examples_content.append({
                        "tag": "div",
                        "data": {"content": "example-sentence"},
                        "content": example
                    })
                structured_content["content"].append({
                    "tag": "div",
                    "data": {"content": "extra-info"},
                    "content": examples_content
                })
                definitions.append(structured_content)
                logging.debug(f"Structured content added for examples.")
            else:
                definitions.append(definition)

            sequence_number = 0

            term_tags = ""

            yomitan_entries.append([
                word,
                reading,
                definition_tags,
                rule_identifier,
                score,
                definitions,
                sequence_number,
                term_tags
            ])
            logging.info(f"Entry for word '{word}' added.")

    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(yomitan_entries, f, ensure_ascii=False, indent=2)
        logging.info(f"Output written to file: {output_path}")
    except IOError as e:
        logging.error(f"Error writing to output file: {e}")

    conn.close()
    logging.info("Database connection closed. Conversion process completed.")

# Example usage
convert_to_yomitan_format('dde2.db', 'term_bank_1.json')
