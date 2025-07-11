import docx
import io
import base64
import re
from docx.shared import Inches

class WordGeneratorService:
    # Regex to find <img ...> tags with base64 data
    IMG_REGEX = re.compile(r'<img src="data:image/png;base64,([^"]+)">')

    def generate_report_from_content(self, composed_content: str, output_path: str):
        """
        Generates a .docx report from a string containing the fully composed content.
        This content can include text and special <img> tags for base64 images.
        """
        doc = docx.Document()
        
        # Split the content into paragraphs based on newlines
        paragraphs = composed_content.split('\n')
        
        for para_text in paragraphs:
            self._process_paragraph(doc, para_text)
            
        doc.save(output_path)

    def _process_paragraph(self, doc, para_text: str):
        """
        Processes a single paragraph of text, adding text and images to the document.
        """
        # Find all image tags in the paragraph
        img_matches = list(self.IMG_REGEX.finditer(para_text))
        
        if not img_matches:
            # If no images, add the whole paragraph as text
            doc.add_paragraph(para_text)
            return

        current_pos = 0
        for match in img_matches:
            # Add text before the image
            start, end = match.span()
            if start > current_pos:
                doc.add_paragraph(para_text[current_pos:start])

            # Add the image
            base64_data = match.group(1)
            try:
                image_stream = io.BytesIO(base64.b64decode(base64_data))
                doc.add_picture(image_stream, width=Inches(6.0))
            except Exception as e:
                print(f"Error decoding or adding picture: {e}")
                # Add a placeholder text on error
                doc.add_paragraph(f"[Image could not be loaded: {e}]")
            
            current_pos = end
        
        # Add any remaining text after the last image
        if current_pos < len(para_text):
            doc.add_paragraph(para_text[current_pos:])

word_generator_service = WordGeneratorService()
