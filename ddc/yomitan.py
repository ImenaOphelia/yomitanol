import json
from convert_tables import convert_table

def convert_json_entry(entry):
    word = entry['word']
    table_html = entry['table']
    print(f"Processing word: {word}")
    
    converted_table = convert_table(table_html)
    
    output = [
        word,           
        "",            
        "",            
        "v",           
        0,             
        [converted_table],
        0,             
        ""            
    ]
    
    print(f"Processed word: {word}")
    return output

with open('conjugation_filtered.json', 'r', encoding='utf-8') as f:
    input_data = json.load(f)
    print("Loaded JSON data")
    
    if isinstance(input_data, list):
        results = [convert_json_entry(entry) for entry in input_data]
    else:
        raise TypeError("Expected JSON data to be a list of entries.")

output_path = 'term_bank_1.json'
try:
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"Output written to file: {output_path}")
except Exception as e:
    print(f"Error: {e}")
