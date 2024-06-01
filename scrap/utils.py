import os
import json
import requests
from bs4 import BeautifulSoup
from tqdm import tqdm
import xml.etree.ElementTree as ET

# Define constants for classes and tags to exclude
CLASSES_TO_EXCLUDE = [
    "elementor-location-header",
    "navbar-header",
    "nav",
    "list-inline",
    "Footnote"
]

TAGS_TO_EXCLUDE = [
    "aside",
    "form",
    "header",
    "noscript",
    "svg",
    "canvas",
    "footer",
    "script",
    "style",
    "a",
    "sup"
]



def parse_xml_tree(url="https://laws-lois.justice.gc.ca/eng/XML/Legis.xml"):
    """This reads the given sitemap and return array of hashmap"""
    response = requests.get(url)
    xml_data = response.text
    root = ET.fromstring(xml_data)
    acts = []
    regulations = []
    acts_elem = root.find('Acts')
    if acts_elem is not None:
        for act_elem in acts_elem.findall('Act'):
            act = {}
            if act_elem.find('Language').text=="eng":
                act['officialnumber']=act_elem.find('OfficialNumber').text
                act['UniqueId']=act_elem.find('UniqueId').text
                act['title'] = act_elem.find('Title').text
                act['date']=act_elem.find('CurrentToDate').text
                act['linkToHtml']=act_elem.find('LinkToHTMLToC').text
                regs_made_under_act = act_elem.find('RegsMadeUnderAct')
                if regs_made_under_act is not None:
                    id_ref_arr=[]
                    for reg in regs_made_under_act.findall("Reg"):
                        id_ref=reg.attrib.get("idRef")
                        if id_ref:
                            id_ref_arr.append(id_ref)
                    act['regs_id']=id_ref_arr
                acts.append(act)
    regulations_elem=root.find('Regulations')
    if regulations_elem is not None:
        for regulation_elem in regulations_elem.findall("Regulation"):
            regulation = {}
            if regulation_elem.find('Language').text=="eng":
                regulation["reg_id"]=regulation_elem.attrib.get("id")
                regulation['title'] = regulation_elem.find('Title').text
                regulation['UniqueId']=regulation_elem.find('UniqueId').text

                regulation['linkToHtml']=regulation_elem.find('LinkToHTMLToC').text
                regulation['title'] = regulation_elem.find('Title').text
                act['UniqueId']=regulation_elem.find('UniqueId').text
                regulation['date']=regulation_elem.find('CurrentToDate').text
                regulation['linkToHtml']=regulation_elem.find('LinkToHTMLToC').text
                regulations.append(regulation)
    return acts, regulations



def array_to_json(name,array):
    file_path = name
    with open(file_path, 'w') as json_file:
        json.dump(array, json_file)


def read_json(file_path):
    """
    This function reads a JSON object from a file and converts it to a Python array.
    """
    with open(file_path, 'r') as json_file:
        python_array = json.load(json_file)
    return python_array

def scrape_text_from_webpage(url, exclude_tags=None, exclude_classes=None):
    """
    This function scrapes text from a webpage, excluding specified tags and classes.
    """
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        if exclude_tags:
            for tag in exclude_tags:
                for element in soup.find_all(tag):
                    element.decompose()

        if exclude_classes:
            for clas in exclude_classes:
                for element in soup.find_all(class_=clas):
                    element.decompose()

        text = soup.get_text(separator=' ', strip=True)
        return text

    except requests.exceptions.RequestException as e:
        print(f"An error occurred while fetching the webpage: {e}")
        return None

def scrape_and_save():
    """
    This function scrapes data from webpages listed in a JSON file and saves the scraped text to text files.
    """
    direc = "data/"
    all_url_meta = read_json(direc + "laws.json")
    n = len(all_url_meta)

    for i in tqdm(range(n)):
        file_path = os.path.join(direc, 'text_raw', f"{all_url_meta[i]['UniqueId']}.txt")
        if os.path.exists(file_path):
            print(file_path, ' already exists in directory')
            continue

        url = all_url_meta[i]['linkToHtml'].replace("index.html", "FullText.html")
        scraped_text = scrape_text_from_webpage(url, exclude_tags=TAGS_TO_EXCLUDE, exclude_classes=CLASSES_TO_EXCLUDE)
        if scraped_text:
            with open(file_path, 'w') as f:
                f.write(scraped_text)

    const_url = "https://laws-lois.justice.gc.ca/eng/const/FullText.html"
    const_file_path = os.path.join(direc, 'text_raw', '01_constitution.txt')
    const_text = scrape_text_from_webpage(const_url, exclude_tags=TAGS_TO_EXCLUDE, exclude_classes=CLASSES_TO_EXCLUDE)
    if const_text:
        with open(const_file_path, 'w') as f:
            f.write(const_text)

def read_text_files_from_folder(text_file):
    """
    THIS FUNCTION READS TEXT FILE
    """
    with open(text_file, 'r', encoding='utf-8') as f:
        return f.read()



# Usage
# if __name__ == "__main__":
#     scrape_and_save()
