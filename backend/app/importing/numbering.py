import re

from docx.oxml.ns import qn


NUMBERED_TASK = re.compile(r"^\s*\d{1,3}(?:\s*[.)\-:](?=\s|$)|\s+|$)")


class DocxNumbering:
    def __init__(self, document):
        self.levels: dict[str, dict[int, tuple[str, int]]] = {}
        self.styles: dict[str, tuple[str, int]] = {}
        self.counters: dict[tuple[str, int], int] = {}
        try:
            numbering = document.part.numbering_part.element
        except KeyError:
            return

        abstract_numbers = {
            node.get(qn("w:abstractNumId")): node
            for node in numbering.findall(qn("w:abstractNum"))
        }

        for number in numbering.findall(qn("w:num")):
            number_id = number.get(qn("w:numId"))
            abstract_id = self._value(number.find(qn("w:abstractNumId")))
            abstract = abstract_numbers.get(abstract_id)
            if not number_id or abstract is None:
                continue

            levels: dict[int, tuple[str, int]] = {}
            for level in abstract.findall(qn("w:lvl")):
                level_index = int(level.get(qn("w:ilvl"), "0"))
                number_format = self._value(level.find(qn("w:numFmt")))
                start = self._integer(level.find(qn("w:start")), 1)
                levels[level_index] = (number_format, start)
                style_id = self._value(level.find(qn("w:pStyle")))
                if style_id:
                    self.styles[style_id] = (number_id, level_index)

            for override in number.findall(qn("w:lvlOverride")):
                level_index = int(override.get(qn("w:ilvl"), "0"))
                level_override = override.find(qn("w:lvl"))
                if level_override is not None:
                    number_format = self._value(level_override.find(qn("w:numFmt")))
                    start = self._integer(level_override.find(qn("w:start")), 1)
                    if number_format:
                        levels[level_index] = (
                            number_format,
                            start if start else levels.get(level_index, ("", 1))[1],
                        )
                start_override = self._integer(
                    override.find(qn("w:startOverride")), 0
                )
                if start_override:
                    number_format = levels.get(level_index, ("", 1))[0]
                    levels[level_index] = (number_format, start_override)

            self.levels[number_id] = levels

    def marker_for(self, paragraph) -> str:
        properties = paragraph._p.pPr
        number_properties = (
            properties.find(qn("w:numPr")) if properties is not None else None
        )
        number_id = None
        level_index = 0
        if number_properties is not None:
            number_id = self._value(number_properties.find(qn("w:numId")))
            level_index = self._integer(
                number_properties.find(qn("w:ilvl")), 0
            )

        if not number_id or number_id == "0":
            style = paragraph.style
            while style is not None:
                style_reference = self.styles.get(style.style_id)
                if style_reference:
                    number_id, level_index = style_reference
                    break
                style = style.base_style

        if not number_id:
            return ""
        number_format, start = self.levels.get(number_id, {}).get(
            level_index, ("", 1)
        )
        if number_format not in {"decimal", "decimalZero"}:
            return ""

        for key in list(self.counters):
            if key[0] == number_id and key[1] > level_index:
                del self.counters[key]
        key = (number_id, level_index)
        current = self.counters.get(key, start - 1) + 1
        self.counters[key] = current
        return f"{current}. "

    @staticmethod
    def _value(element) -> str | None:
        return element.get(qn("w:val")) if element is not None else None

    @classmethod
    def _integer(cls, element, default: int) -> int:
        value = cls._value(element)
        try:
            return int(value) if value is not None else default
        except ValueError:
            return default
