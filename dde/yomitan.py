import sqlite3
import json
import logging
import time

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
conjugation_model_mapping = {
    "amar": "1",
    "temer": "2",
    "partir": "3",
    "anunciar": "4",
    "enviar": "5",
    "liar": "6",
    "averiguar": "7",
    "actuar": "8",
    "bailar": "9",
    "aislar": "10",
    "causar": "11",
    "aunar": "12",
    "peinar": "13",
    "descafeinar": "14",
    "adeudar": "15",
    "rehusar": "16",
    "acertar": "17",
    "adquirir": "18",
    "agradecer": "19",
    "andar": "20",
    "asir": "21",
    "bendecir": "22",
    "caber": "23",
    "caer": "24",
    "ceñir": "25",
    "conducir": "26",
    "construir": "27",
    "contar": "28",
    "dar": "29",
    "decir": "30",
    "discernir": "31",
    "dormir": "32",
    "entender": "33",
    "erguir": "34",
    "errar": "35",
    "estar": "36",
    "haber": "37",
    "hacer": "38",
    "huir": "39",
    "ir": "40",
    "jugar": "41",
    "leer": "42",
    "lucir": "43",
    "mover": "44",
    "mullir": "45",
    "oír": "46",
    "oler": "47",
    "pedir": "48",
    "poder": "49",
    "poner": "50",
    "predecir": "51",
    "pudrir": "52",
    "podrir": "52",
    "querer": "53",
    "reír": "54",
    "roer": "55",
    "saber": "56",
    "salir": "57",
    "sentir": "58",
    "ser": "59",
    "sonreír": "60",
    "tañer": "61",
    "tener": "62",
    "traer": "63",
    "valer": "64",
    "venir": "65",
    "ver": "66",
    "yacer": "67"
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

        grouped_definitions = {}

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
                    logging.info(f'Rule identifier "{rule_identifier}" assigned for grammar tag "{tag}".')
                    break

            score = 0

            structured_content = {
                "type": "structured-content",
                "content": [definition]
            }

            examples_content = [
                {
                    "tag": "div",
                    "data": {"content": "example-sentence"},
                    "content": example
                } for example in entry.get('examples', [])
            ]
            if examples_content:
                structured_content["content"].append({
                    "tag": "div",
                    "data": {"content": "extra-info"},
                    "content": examples_content
                })

            synonyms_content = [
                {
                    "tag": "a",
                    "content": synonym,
                    "href": f"?query={synonym}&wildcards=off"
                } for synonym in entry.get('synonyms', [])
            ]
            if synonyms_content:
                structured_content["content"].append({
                    "tag": "div",
                    "data": {"content": "synonyms"},
                    "content": synonyms_content
                })

            antonyms_content = [
                {
                    "tag": "a",
                    "content": antonym,
                    "href": f"?query={antonym}&wildcards=off"
                } for antonym in entry.get('antonyms', [])
            ]
            if antonyms_content:
                structured_content["content"].append({
                    "tag": "div",
                    "data": {"content": "antonyms"},
                    "content": antonyms_content
                })

            key = (definition_tags, rule_identifier)
            if key not in grouped_definitions:
                grouped_definitions[key] = []
            grouped_definitions[key].append(structured_content)

        for (definition_tags, rule_identifier), definitions in grouped_definitions.items():
            conjugation_model = entry.get("conjugation_model")
            term_tags = conjugation_model_mapping.get(conjugation_model, "") if conjugation_model else ""
            sequence_number = 0

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
            logging.info(f"Grouped entry for word '{word}' with tags '{definition_tags}' added.")

    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(yomitan_entries, f, ensure_ascii=False, indent=2)
        logging.info(f"Output written to file: {output_path}")
    except IOError as e:
        logging.error(f"Error writing to output file: {e}")

    conn.close()
    logging.info("Database connection closed. Conversion process completed.")

convert_to_yomitan_format('dde2.db', 'term_bank_1.json')