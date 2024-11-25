import json

input_file = "frecuencia_lemas_corpes_1_2.txt"
output_file = "term_meta_bank_0.json"

punctuation_marks = {",", ".", "¡", "!", "¿", "?", "??", ";", ":", "'", "\"", "‘", "’", "“" "”", "«", "»", "[", "]", "{", "}", "…", "...", "—", "_", "-", "%", "\\", "/"}

output_data = []
rank = 1 
with open(input_file, "r", encoding="utf-8") as file:
    for line in file:
        parts = line.strip().split("\t")
        if len(parts) < 1:
            continue
        word = parts[0]
        if word in punctuation_marks:
            continue
        output_data.append([
            word,
            "freq",
            {
                "value": rank,
                "displayValue": str(rank)
            }
        ])
        rank += 1

with open(output_file, "w", encoding="utf-8") as file:
    json.dump(output_data, file, indent=2, ensure_ascii=False)

print(f"Conversion complete! Output saved to '{output_file}'")
