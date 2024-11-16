from bs4 import BeautifulSoup

def beautify_conjugation_table(html_content):
    # Parse the HTML
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Find the table
    table = soup.find('table', class_='cnj')
    
    # Add language attribute
    table['lang'] = 'es'
    table['aria-label'] = 'Conjugación del verbo'
    
    # Remove the "Número" and "Personas del discurso" columns
    for row in table.find_all('tr'):
        cells = row.find_all(['th', 'td'])
        if cells:
            # Remove "Número" column (usually first column)
            if cells[0].get_text(strip=True) == 'Número' or 'data-g' in cells[0].attrs:
                cells[0].decompose()
            
            # Remove "Personas del discurso" column
            remaining_cells = row.find_all(['th', 'td'])
            if remaining_cells and (remaining_cells[0].get_text(strip=True) == 'Personas del discurso' 
                                or 'data-p' in remaining_cells[0].attrs):
                remaining_cells[0].decompose()

    # Remove completely empty rows or cells if desired
    for row in table.find_all('tr'):
        cells = row.find_all(['th', 'td'])
        # Optional: remove completely empty cells
        cells = [cell for cell in cells if cell.get_text(strip=True)]
        
        # Rebuild row with non-empty cells
        row.clear()
        for cell in cells:
            row.append(cell)

    # Optional: Add a wrapper div for responsiveness
    wrapper = soup.new_tag('div')
    wrapper['class'] = 'table-responsive'
    table.wrap(wrapper)
    
    return str(soup)

with open('input_table.html', 'r', encoding='utf-8') as file:
    html_content = file.read()

beautified_html = beautify_conjugation_table(html_content)

with open('beautified_table.html', 'w', encoding='utf-8') as file:
    file.write(beautified_html)