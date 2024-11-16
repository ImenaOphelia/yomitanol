from bs4 import BeautifulSoup
import json

def convert_table(html):
    soup = BeautifulSoup(html, 'html.parser')

    json_table = {
        "type": "structured-content",
        "content": []
    }

    tbody = soup.find("tbody")
    json_tbody = {"tag": "tbody", "content": []}

    for tr in tbody.find_all("tr"):
        json_tr = {"tag": "tr", "content": []}
        for td in tr.find_all(["td", "th"]):
            cell = {
                "tag": "td" if td.name == "td" else "th",
                "content": td.get_text(strip=True)
            }
            if td.has_attr("colspan"):
                cell["colSpan"] = int(td["colspan"])
            if td.has_attr("rowspan"):
                cell["rowSpan"] = int(td["rowspan"])
            json_tr["content"].append(cell)
        json_tbody["content"].append(json_tr)

    json_table["content"].append(json_tbody)
    
    return json_table