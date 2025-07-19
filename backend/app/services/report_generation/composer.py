import base64
from typing import Any, Dict


class ReportCompositionService:
    def is_base64(self, s: Any) -> bool:
        """
        A simple check to see if a string looks like a base64 encoded image.
        This is not foolproof but works for common cases (e.g., PNGs).
        """
        if not isinstance(s, str):
            return False
        # Common base64 padding can be '==' or '='.
        # A more robust check might involve trying to decode it.
        return s.startswith("iVBORw0KGgo") or s.endswith(("==", "="))

    def compose_report(self, template_content: str, results: Dict[str, Any]) -> str:
        """
        Composes the final report by replacing placeholders in the template
        with the results from the ToolDispatcherService.

        Args:
            template_content: The raw string content of the template.
            results: A dictionary where keys are placeholders (e.g., "{{count:...}}")
                     and values are the generated results.

        Returns:
            The composed report content with placeholders replaced.
        """
        composed_content = template_content
        for placeholder, result in results.items():
            replacement = ""
            if self.is_base64(result):
                # If the result is a base64 image, wrap it in an <img> tag.
                # The WordGeneratorService will need to be able to parse this.
                replacement = f'<img src="data:image/png;base64,{result}">'
            else:
                # For any other type, convert it to a string.
                replacement = str(result)

            composed_content = composed_content.replace(placeholder, replacement)

        return composed_content


report_composition_service = ReportCompositionService()
