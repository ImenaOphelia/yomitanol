import json
import logging
from datetime import datetime

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


def clean_star_symbols(synonym_or_antonym):
    """
    Remove * symbols from synonyms/antonyms.
    """
    return synonym_or_antonym.replace('*', '').strip()


def read_from_jsonl(file_path):
    """
    Reads the input JSONL file and returns the entries as a list.
    """
    logging.info(f"Reading from JSONL file: {file_path}")
    entries = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                entries.append(json.loads(line))
        logging.info(f"Loaded {len(entries)} entries from {file_path}")
    except Exception as e:
        logging.error(f"Error reading JSONL file: {e}")
    return entries


def get_definitions(entry_data):
    """
    Extract definitions from entry data, handling both regular and solution entries.
    """
    if isinstance(entry_data, dict) and 'definitions' in entry_data:
        return entry_data['definitions']
    elif isinstance(entry_data, list):
        return entry_data
    return []


def convert_to_yomitan_format(db_path, output_path, input_type='jsonl'):
    """
    Converts the JSONL file into the desired Yomitan format.
    """
    logging.info("Starting the conversion process.")

    if input_type == 'jsonl':
        data_source = read_from_jsonl(db_path)
    else:
        logging.error(f"Unsupported input type: {input_type}")
        return

    yomitan_entries = []

    for entry in data_source:
        word = entry['word']
        entry_type = entry['type']
        structured_data = entry['data']
        logging.info(f"Processing word: {word} (type: {entry_type})")

        reading = ""
        grouped_definitions = {}
        plural_form = structured_data.get("plural", "")
        participles = structured_data.get("participios", [])
        expressions = structured_data.get("expressions", [])
        term_note = structured_data.get("term_note", "")

        definitions = get_definitions(structured_data)
        
        if not definitions:
            logging.warning(f"No definitions found for word '{word}'")
            continue

        for idx, definition in enumerate(definitions):
            if not isinstance(definition, dict):
                logging.warning(f"Skipping definition for word '{word}' because it is not a dictionary.")
                continue

            definition_text = definition.get('definition', '')
            logging.debug(f"Definition found: {definition_text}")

            grammar_tags = [tag['tag'].replace(' ', '-') for tag in definition.get('grammar_tags', [])]
            usage_tags = [tag['tag'].replace(' ', '-') for tag in definition.get('usage_tags', [])]
            geo_tags = [tag['tag'].replace(' ', '-') for tag in definition.get('geo_tags', [])]
            def_notes = definition.get('def_notes', [])
            definition_tags = ' '.join(grammar_tags + usage_tags + geo_tags)
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
                "content": [definition_text]
            }

            if idx == 0:
                if term_note:
                    structured_content["content"].append({
                        "tag": "div",
                        "data": {"content": "term-note"},
                        "content": term_note
                    })

                if plural_form:
                    structured_content["content"].append({
                        "tag": "div",
                        "data": {"content": "plural"},
                        "content": plural_form
                    })

                participles_content = [
                    {
                        "tag": "a",
                        "content": clean_star_symbols(participle),
                        "href": f"?query={clean_star_symbols(participle)}&wildcards=off"
                    } for participle in participles
                ]
                for participle in participles_content:
                    structured_content["content"].append({
                        "tag": "div",
                        "data": {"content": "participles"},
                        "content": [participle]
                    })

            examples_content = [
                {
                    "tag": "div",
                    "data": {"content": "example-sentence"},
                    "content": example
                } for example in definition.get('examples', [])
            ]
            if examples_content:
                structured_content["content"].append({
                    "tag": "div",
                    "data": {"content": "extra-info"},
                    "content": examples_content
                })

            def_notes_content = [
                {
                    "tag": "div",
                    "data": {"content": "definition-notes"},
                    "content": note
                } for note in def_notes
            ]

            if def_notes_content:
                structured_content["content"].append({
                    "tag": "div",
                    "data": {"content": "extra-info"},
                    "content": def_notes_content
                })

            synonyms_content = [
                {
                    "tag": "a",
                    "content": clean_star_symbols(synonym),
                    "href": f"?query={clean_star_symbols(synonym)}&wildcards=off"
                } for synonym in definition.get('synonyms', [])
            ]
            for synonym in synonyms_content:
                structured_content["content"].append({
                    "tag": "div",
                    "data": {"content": "synonyms"},
                    "content": [synonym]
                })

            antonyms_content = [
                {
                    "tag": "a",
                    "content": clean_star_symbols(antonym),
                    "href": f"?query={clean_star_symbols(antonym)}&wildcards=off"
                } for antonym in definition.get('antonyms', [])
            ]
            for antonym in antonyms_content:
                structured_content["content"].append({
                    "tag": "div",
                    "data": {"content": "antonyms"},
                    "content": [antonym]
                })

            if idx == len(definitions) - 1:
                structured_content["content"].append({
                    "tag": "div",
                    "data": {"content": "attribution"},
                    "content": [
                        {
                            "tag": "a",
                            "content": "DLE",
                            "href": f"https://dle.rae.es/{word}"
                        },
                        {
                            "tag": "span",
                            "content": " | ",
                        },
                        {
                            "tag": "a",
                            "content": "DLE",
                            "href": f"https://rae.es/diccionario-estudiante/{word}"
                        }
                    ]
                })
                expressions_content = [
                    {
                        "tag": "a",
                        "content": clean_star_symbols(expression),
                        "href": f"?query={clean_star_symbols(expression)}&wildcards=off"
                    } for expression in expressions
                ]
                for expression in expressions_content:
                    structured_content["content"].append({
                        "tag": "div",
                        "data": {"content": "expressions"},
                        "content": [expression]
                    })

            key = (definition_tags, rule_identifier)
            if key not in grouped_definitions:
                grouped_definitions[key] = []
            grouped_definitions[key].append(structured_content)

        for (definition_tags, rule_identifier), definitions in grouped_definitions.items():
            conjugation_model = structured_data.get("conjugation_model") if isinstance(structured_data, dict) else None
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

    logging.info("Conversion process completed.")

convert_to_yomitan_format('term_bank_0.jsonl', 'term_bank_1.json', input_type='jsonl')