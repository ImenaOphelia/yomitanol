import sqlite3

def find_duplicates(db_path, table_name, column_name):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute(f"""
        SELECT {column_name}, COUNT(*)
        FROM {table_name}
        GROUP BY {column_name}
        HAVING COUNT(*) > 1
    """)
    
    duplicates = cursor.fetchall()
    
    if not duplicates:
        print("No duplicates found.")
        conn.close()
        return []
    
    print(f"Found duplicates in column '{column_name}':")
    for value, count in duplicates:
        print(f"Value: {value}, Count: {count}")
    
    conn.close()
    return duplicates

def save_duplicates_to_file(db_path, table_name, column_name, duplicates):
    if not duplicates:
        print("No duplicates to save.")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    with open("duplicates_report.txt", "w", encoding="utf-8") as file:
        for value, _ in duplicates:
            cursor.execute(f"SELECT rowid, * FROM {table_name} WHERE {column_name} = ?", (value,))
            rows = cursor.fetchall()
            
            if not rows:
                print(f"No rows found for duplicate value: '{value}'")
                continue
            
            file.write(f"\nDuplicate entries for '{value}':\n")
            for row in rows:
                file.write(str(row) + "\n")
                print(f"Written to file: {row}")
                
    print("\nDuplicate entries have been saved to 'duplicates_report.txt'. Review them before approving deletion.")
    conn.close()

def delete_duplicates(db_path, table_name, column_name, duplicates, delete_all):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    for value, _ in duplicates:
        cursor.execute(f"SELECT rowid, * FROM {table_name} WHERE {column_name} = ?", (value,))
        rows = cursor.fetchall()
        
        if delete_all:
            for row in rows[1:]:
                cursor.execute(f"DELETE FROM {table_name} WHERE rowid = ?", (row[0],))
            print(f"Deleted all duplicates for '{value}'.")
        else:
            print(f"\nDuplicate entries for '{value}':")
            for row in rows[1:]:
                confirm = input(f"Do you want to delete this entry? {row} (y/n): ").strip().lower()
                if confirm == 'y':
                    cursor.execute(f"DELETE FROM {table_name} WHERE rowid = ?", (row[0],))
                    print(f"Deleted entry: {row}")
                else:
                    print(f"Skipped entry: {row}")
        
        conn.commit()
    
    conn.close()

def main():
    db_path = input("Enter the path to the database: ").strip()
    table_name = input("Enter the table name: ").strip()
    column_name = input("Enter the column name to check for duplicates: ").strip()
    
    duplicates = find_duplicates(db_path, table_name, column_name)
    
    if duplicates:
        save_duplicates_to_file(db_path, table_name, column_name, duplicates)
        
        delete_all = input("Do you want to delete all duplicates at once? (y/n): ").strip().lower() == 'y'
        
        confirm_deletion = input("Are you sure you want to proceed with the deletions? (y/n): ").strip().lower()
        
        if confirm_deletion == 'y':
            delete_duplicates(db_path, table_name, column_name, duplicates, delete_all)
        else:
            print("Deletion cancelled. No records were deleted.")

if __name__ == "__main__":
    main()
