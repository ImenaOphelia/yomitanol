import json

def find_duplicates(json_path, key_name):
    with open(json_path, "r", encoding="utf-8") as file:
        data = json.load(file)
    
    value_counts = {}
    for entry in data:
        value = entry.get(key_name)
        if value:
            value_counts[value] = value_counts.get(value, 0) + 1
    
    duplicates = {k: v for k, v in value_counts.items() if v > 1}
    
    if not duplicates:
        print("No duplicates found.")
        return []
    
    print(f"Found duplicates in key '{key_name}':")
    for value, count in duplicates.items():
        print(f"Value: {value}, Count: {count}")
    
    return duplicates

def save_duplicates_to_file(json_path, key_name, duplicates):
    if not duplicates:
        print("No duplicates to save.")
        return
    
    with open(json_path, "r", encoding="utf-8") as file:
        data = json.load(file)
    
    with open("duplicates_report.txt", "w", encoding="utf-8") as file:
        for value in duplicates:
            duplicate_entries = [entry for entry in data if entry.get(key_name) == value]
            
            if not duplicate_entries:
                print(f"No entries found for duplicate value: '{value}'")
                continue
            
            file.write(f"\nDuplicate entries for '{value}':\n")
            for entry in duplicate_entries:
                file.write(json.dumps(entry, ensure_ascii=False) + "\n")
                print(f"Written to file: {entry}")
                
    print("\nDuplicate entries have been saved to 'duplicates_report.txt'. Review them before approving deletion.")

def delete_duplicates(json_path, key_name, duplicates, delete_all):
    with open(json_path, "r", encoding="utf-8") as file:
        data = json.load(file)
    
    values_seen = set()

    new_data = []
    for entry in data:
        value = entry.get(key_name)
        if value in duplicates:
            if value in values_seen:
                if delete_all:
                    print(f"Deleted duplicate for '{value}': {entry}")
                    continue
                else:
                    confirm = input(f"Do you want to delete this entry? {entry} (y/n): ").strip().lower()
                    if confirm == 'y':
                        print(f"Deleted entry: {entry}")
                        continue
                    else:
                        print(f"Skipped entry: {entry}")
            else:
                values_seen.add(value)
        new_data.append(entry)

    with open(json_path, "w", encoding="utf-8") as file:
        json.dump(new_data, file, ensure_ascii=False, indent=4)
    
    print("\nDuplicate deletion completed.")

def main():
    json_path = input("Enter the path to the JSON file: ").strip()
    key_name = input("Enter the key name to check for duplicates: ").strip()
    
    duplicates = find_duplicates(json_path, key_name)
    
    if duplicates:
        save_duplicates_to_file(json_path, key_name, duplicates)
        
        delete_all = input("Do you want to delete all duplicates at once? (y/n): ").strip().lower() == 'y'
        
        confirm_deletion = input("Are you sure you want to proceed with the deletions? (y/n): ").strip().lower()
        
        if confirm_deletion == 'y':
            delete_duplicates(json_path, key_name, duplicates, delete_all)
        else:
            print("Deletion cancelled. No records were deleted.")

if __name__ == "__main__":
    main()
