from src.utils.base.libraries import re, urljoin, NavigableString, BeautifulSoup, html2text



class HeaderExtractor:
    def __init__(self , soup , word_count_limit = 200):
        self.soup = soup
        self.word_count_limit = word_count_limit
        self.all_headers_para_list = []

    def extract_text_from_element(self, element):
        text = ''.join(element.stripped_strings)
        return text

    def count_words(self, text):
        return len(text.split())

    def find_headers_recursively(self, element, header_paragraph):
        if element.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            header_text = self.extract_text_from_element(element)
            header_paragraph.append(header_text)

        for child in element.children:
            if not isinstance(child, NavigableString):
                self.find_headers_recursively(child, header_paragraph)

    def process_headers(self):

        main_headers = self.soup.find_all(['h1', 'h2', 'h3' ])

        for idx, header in enumerate(main_headers):
            header_text = self.extract_text_from_element(header)
            #print(f"Header {idx + 1} ({header.name}): {header_text}")

            word_count = 0
            sibling = header.find_next_sibling()
            while sibling:
                if not isinstance(sibling, NavigableString):
                    tag_name = sibling.name
                    element_text = self.extract_text_from_element(sibling)
                    if element_text:
                        words_in_element = self.count_words(element_text)
                        word_count += words_in_element
                sibling = sibling.find_next_sibling()

            #print(f"Total words under header {idx + 1}: {word_count}")

            if word_count > self.word_count_limit:
                header_paragraph = []
                sibling = header.find_next_sibling()
                while sibling:
                    self.find_headers_recursively(sibling, header_paragraph)
                    sibling = sibling.find_next_sibling()
                
                #print(' '.join(header_paragraph))
                #add header text
                header_paragraph.insert(0,f"{header_text}: ")
                self.all_headers_para_list.append(' '.join(header_paragraph))
            #print("\n")

        return self.all_headers_para_list


# Define a function to check if an element contains a keyword
def contains_cookie_keyword(element, keyword):
    if element and element.string and keyword in element.string.lower():
        return True
    if 'href' in element.attrs and keyword in element['href'].lower():
        return True
    if 'class' in element.attrs and any(keyword in cls.lower() for cls in element['class']):
        return True
    return False


def contains_unwanted_keywords(sentence, keywords):
    for keyword in keywords:
        if keyword.lower() in sentence.lower():
            return True
    return False


def remove_cookie_js_text(page_text):
    cookie_keywords = ['cookies', 'cookie', 'cookie-policy']
    unwanted_keywords = ["JavaScript has been disabled", "enable JS", "please enable JS", "enable javascript on your browser to make this app work","JavaScript has been disabled on your browser , please enable JS to make this app work."]

    # Create a pattern to match whole sentences containing cookie keywords
    cookie_pattern = r'(?:^|(?<=\s))[^.!?]*\b(?:' + '|'.join(cookie_keywords) + r')\b[^.!?]*(?:[.!?]+|$)'

    # Remove the matching sentences from the extracted text
    page_text_cleaned = re.sub(cookie_pattern, '', page_text, flags=re.IGNORECASE)

    # Split the cleaned text into sentences
    sentences = re.split(r'(?<=[.!?])\s+', page_text_cleaned)

    #print(f"sentences: {sentences}\n\n")

    # Filter out sentences containing any unwanted keywords
    filtered_sentences = [sentence for sentence in sentences if not contains_unwanted_keywords(sentence, unwanted_keywords)]

    # Join the filtered sentences back into a single text
    page_text_cleaned = ' '.join(filtered_sentences)

    return page_text_cleaned


def convert_html_to_markdown(html):
    try:
        h = html2text.HTML2Text()
        h.ignore_links = False
        return h.handle(html)
    except Exception as e:
        return "Sorry, Not able to parse it!"


def parse_html( url , html_text , remove_header_footer = True ):
    # Remove all HTML comments
    cleaned_html_text = re.sub(r'<!--.*?-->', '', html_text, flags=re.DOTALL)
   
    # Remove all content within <script> tags
    cleaned_html_text = re.sub(r'<script.*?>.*?</script>', '', cleaned_html_text, flags=re.DOTALL)

    soup = BeautifulSoup(cleaned_html_text, 'html.parser')

    # Remove script and style tags
    for script in soup(['script', 'style']):
        script.decompose()
   
    # Remove head tag and its content
    head_tag = soup.find("head")
    if head_tag:
        head_tag.decompose()

    # Remove specific messages like cookie notices and JavaScript messages
    for element in soup.find_all(text=re.compile('cookies|JavaScript', re.IGNORECASE)):
        parent_element = getattr(element, 'parent', None)
        if parent_element:
            parent_element.extract()

    # Remove elements that have certain keywords in their class or id attributes
    keywords_to_remove = ['cookie', 'footer', 'header']
    for element in soup.find_all(True):
        try:
            class_attr = ' '.join(element.attrs.get('class', []))
            id_attr = element.attrs.get('id', '')
            if any(keyword in class_attr for keyword in keywords_to_remove) or any(keyword in id_attr for keyword in keywords_to_remove):
                element.decompose()
        except AttributeError:
            continue
           
    if remove_header_footer:
        try:
            # Remove header and footer based on known tags, classes or IDs
            for tag in soup.find_all(['header', 'footer']):
                tag.extract()

            # Additional logic to remove headers and footers if they couldn't be found by 'find'
            for element in soup.find_all(['div', 'nav', 'section']):
                class_attr = getattr(element, 'attrs', {}).get('class', [])
                id_attr = getattr(element, 'attrs', {}).get('id', '')
               
                if 'header' in class_attr or 'header' in id_attr:
                    element.extract()
                if 'footer' in class_attr or 'footer' in id_attr:
                    element.extract()
        except:
            pass

    # Replace 'a' tags with their URLs
    for link in soup.find_all('a'):
        if link.has_attr('href') and not link['href'].startswith("#"):
            link_url = urljoin(url, link['href'])
            link['href'] = link_url
    
    return convert_html_to_markdown(html=soup.prettify())

