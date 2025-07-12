import re
from typing import Any, Dict, List

import docx


class TemplateParser:
    # Regex to find {{placeholder "description"}}, [chart:name "description"], [table:name "description"]
    PLACEHOLDER_REGEX = re.compile(
        r"\{\{(?P<scalar>[\w\s]+?)\s*(?:\s+\"(?P<s_desc>.*?)\")?\s*\}\}|"
        r"\[(?P<type>chart|table):(?P<name>[\w\s]+?)\s*(?:\s+\"(?P<ct_desc>.*?)\")?\s*\]"
    )

    def parse(self, file_path: str) -> Dict[str, List[Dict[str, Any]]]:
        """
        Parses a .docx file to extract placeholders for scalar values, charts, and tables.

        Each placeholder can have an optional description.
        """
        doc = docx.Document(file_path)
        placeholders = []
        found_keys = set()

        # Combine text from paragraphs and tables for parsing
        full_text = "\n".join([p.text for p in doc.paragraphs])
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    full_text += "\n" + cell.text

        for match in self.PLACEHOLDER_REGEX.finditer(full_text):
            if match.group("scalar"):
                key = match.group("scalar").strip()
                if key not in found_keys:
                    placeholders.append(
                        {
                            "name": key,
                            "type": "scalar",
                            "description": match.group("s_desc") or "",
                        }
                    )
                    found_keys.add(key)
            else:
                key = match.group("name").strip()
                if key not in found_keys:
                    placeholders.append(
                        {
                            "name": key,
                            "type": match.group("type"),
                            "description": match.group("ct_desc") or "",
                        }
                    )
                    found_keys.add(key)

        return {"placeholders": placeholders}


template_parser = TemplateParser()
