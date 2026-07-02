import zipfile
import xml.etree.ElementTree as ET

def read_docx(file_path: str) -> str:
    """
    Reads text from a .docx file without requiring external libraries like python-docx.
    A .docx file is essentially a ZIP archive containing XML files.
    """
    try:
        with zipfile.ZipFile(file_path, 'r') as docx:
            # document.xml contains the main text
            xml_content = docx.read('word/document.xml')
            
            tree = ET.fromstring(xml_content)
            
            # The namespace for Word processing XML
            ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
            
            # Extract text from all <w:t> nodes
            paragraphs = []
            for p in tree.findall('.//w:p', namespaces=ns):
                texts = [node.text for node in p.findall('.//w:t', namespaces=ns) if node.text]
                if texts:
                    paragraphs.append(''.join(texts))
            
            return '\n'.join(paragraphs)
    except Exception as e:
        print(f"Error reading docx: {e}")
        return ""
