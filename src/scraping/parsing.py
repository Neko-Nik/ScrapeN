from src.utils.base.libraries import re, urljoin, NavigableString, BeautifulSoup



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


def parse_html( url , html_text , remove_header_footer = True ):

    soup = BeautifulSoup( html_text, 'html.parser' )
    # Remove script and style tags
    for script in soup(["script", "style"]):
        script.extract()

    if remove_header_footer:
        # Find the header tag or class in the HTML document
        header = soup.find('header')  # replace with the actual header tag or class
        # Find the footer tag or class in the HTML document
        footer = soup.find('footer')  # replace with the actual footer tag or class
        # Remove the header and footer tags or classes from the parsed data
        if header:
            header.extract()
        if footer:
            footer.extract()

    # Remove elements containing JavaScript message
    js_message = soup.find_all(string="If you're seeing this message, that means JavaScript has been disabled on your browser , please enable JS to make this app work")
    for elem in js_message:
        elem.extract()

    # Remove elements containing "Privacy Statement" with cookies link
    # Define keywords related to cookie-policy
    cookie_keywords = ['cookie', 'cookie-policy']

    # Find and remove elements containing the keywords
    for keyword in cookie_keywords:
        elements_to_remove = soup.find_all(lambda tag: contains_cookie_keyword(tag, keyword))
        for elem in elements_to_remove:
            elem.extract()


    # Replace 'a' tags with their URLs
    url_data = []
    already_added_links = []
    #print(f"all links: {soup.find_all('a')}")
    for link in soup.find_all('a'):
        if link.has_attr('href') and not link['href'].startswith("#"): #and link['href'].startswith(('http', 'https')):
            link_url = urljoin(url, link['href'])
            link_old_text = link.text
            link_string = f"[{link.text}]{link_url}"
            if link_string not in already_added_links:
                link.string = link_string
                already_added_links.append(link_string)

                #find headers and other data for metdata
                header = link.find_previous('h1') or link.find_previous('h2') or link.find_previous('h3') or link.find_previous('h4') or link.find_previous('h5') or link.find_previous('h6')
                if header:
                    header_text = header.text.strip()
                else:
                    header_text = None
                    
                url_data.append({'url': link_url, 'text': link_old_text  , 'header': header_text})


    # Remove JavaScript and CSS code
    clean_text = re.sub(r"(?is)<(script|style).*?>.*?(</\1>)", "", str(soup))
    # Remove HTML tags, except <hsep>
    clean_text = re.sub(r"(?s)<(?!hsep).*?>", " ", clean_text)
    # Remove extra whitespace
    clean_text = re.sub(r"\s+", " ", clean_text)
    #remove text related to cookies
    clean_text = remove_cookie_js_text(page_text = clean_text )

    #logging.debug(f"Extracted text from: {url}")

    #add the headers text if the text under header section is more 
    header_extractor = HeaderExtractor( soup = soup )
    header_text_list = header_extractor.process_headers()
    if header_text_list:
        extra_header_text = ". ".join( header_text_list )
        clean_text = extra_header_text + '. ' + clean_text
    
    current_url_data = { "text": clean_text.strip() , "links_data": url_data }

    return current_url_data
