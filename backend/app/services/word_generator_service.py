import docx
import io
import base64
from typing import Dict, Any

class WordGeneratorService:
    def generate_report(
        self, 
        template_path: str, 
        output_path: str, 
        data: Dict[str, Any]
    ):
        """
        Generates a .docx report by filling a template with provided data.
        
        - Replaces {{text_placeholder}} with string values.
        - Replaces [chart:chart_placeholder] with a base64 encoded image.
        """
        doc = docx.Document(template_path)

        # Replace text placeholders
        for p in doc.paragraphs:
            for key, value in data.items():
                if isinstance(value, str) and f"{{{{{key}}}}}" in p.text:
                    # Simple text replacement
                    p.text = p.text.replace(f"{{{{{key}}}}}", value)

        # Replace chart/table placeholders
        for p in doc.paragraphs:
            for key, value in data.items():
                if f"[chart:{key}]" in p.text and self._is_base64(value):
                    p.text = p.text.replace(f"[chart:{key}]", "")
                    # Add image from base64 string
                    image_stream = io.BytesIO(base64.b64decode(value))
                    p.add_run().add_picture(image_stream, width=docx.shared.Inches(5.0))
        
        # Note: Table filling logic would be more complex and is omitted here
        # It would involve finding a [table:key] placeholder and then
        # dynamically adding rows to a table element.

        doc.save(output_path)

    def _is_base64(self, s: Any) -> bool:
        if not isinstance(s, str):
            return False
        try:
            base64.b64decode(s)
            return True
        except Exception:
            return False

word_generator_service = WordGeneratorService()
