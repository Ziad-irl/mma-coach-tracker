"""Minimal .xlsx writer using only the standard library.

An .xlsx file is a zip of XML parts. This writes just enough of the format
for Excel and LibreOffice: several sheets, a bold shaded header row that
stays frozen while scrolling, column widths, number formats and an optional
right-to-left sheet direction for Arabic.
"""

import re
import zipfile
from xml.sax.saxutils import escape

MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
HEAD = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'

# Cell style indexes in STYLES below.
STYLE_TEXT, STYLE_HEADER, STYLE_MONEY = 0, 1, 2

STYLES = HEAD + (
    '<styleSheet xmlns="%s">'
    '<fonts count="2">'
    '<font><sz val="11"/><name val="Calibri"/></font>'
    '<font><b/><sz val="11"/><name val="Calibri"/></font>'
    '</fonts>'
    '<fills count="3">'
    '<fill><patternFill patternType="none"/></fill>'
    '<fill><patternFill patternType="gray125"/></fill>'
    '<fill><patternFill patternType="solid"><fgColor rgb="FFDDE5F0"/>'
    '<bgColor indexed="64"/></patternFill></fill>'
    '</fills>'
    '<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>'
    '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
    '<cellXfs count="3">'
    '<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>'
    '<xf numFmtId="0" fontId="1" fillId="2" borderId="0" xfId="0" applyFont="1" applyFill="1"/>'
    '<xf numFmtId="4" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/>'
    '</cellXfs>'
    '<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>'
    '</styleSheet>' % MAIN_NS
)

_ILLEGAL_XML = re.compile(u"[\x00-\x08\x0b\x0c\x0e-\x1f]")
_BAD_SHEET_CHARS = re.compile(r"[\[\]:*?/\\]")


def column_letter(index):
    """0 -> A, 25 -> Z, 26 -> AA."""
    letters = ""
    index += 1
    while index:
        index, rem = divmod(index - 1, 26)
        letters = chr(65 + rem) + letters
    return letters


def _text(value):
    return escape(_ILLEGAL_XML.sub("", str(value)))


def _cell(ref, value, kind):
    if value is None or value == "":
        return ""
    if kind in ("money", "int") and isinstance(value, (int, float)):
        style = ' s="%d"' % STYLE_MONEY if kind == "money" else ""
        return '<c r="%s"%s><v>%r</v></c>' % (ref, style, value)
    return '<c r="%s" t="inlineStr"><is><t xml:space="preserve">%s</t></is></c>' % (
        ref, _text(value))


def _sheet_xml(columns, rows, rtl):
    parts = [HEAD, '<worksheet xmlns="%s">' % MAIN_NS,
             '<sheetViews><sheetView workbookViewId="0"%s>'
             '<pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/>'
             '</sheetView></sheetViews>' % (' rightToLeft="1"' if rtl else ""),
             "<cols>"]
    for i, (_header, _kind, width) in enumerate(columns):
        parts.append('<col min="%d" max="%d" width="%d" customWidth="1"/>' % (i + 1, i + 1, width))
    parts.append("</cols><sheetData>")

    parts.append('<row r="1">')
    for i, (header, _kind, _width) in enumerate(columns):
        parts.append('<c r="%s1" t="inlineStr" s="%d"><is><t>%s</t></is></c>' % (
            column_letter(i), STYLE_HEADER, _text(header)))
    parts.append("</row>")

    for r, row in enumerate(rows, start=2):
        parts.append('<row r="%d">' % r)
        for i, value in enumerate(row):
            parts.append(_cell("%s%d" % (column_letter(i), r), value, columns[i][1]))
        parts.append("</row>")
    parts.append("</sheetData></worksheet>")
    return "".join(parts)


def _sheet_name(name, used):
    name = _BAD_SHEET_CHARS.sub(" ", name).strip()[:31] or "Sheet"
    base, n = name, 2
    while name.lower() in used:
        suffix = " (%d)" % n
        name = base[:31 - len(suffix)] + suffix
        n += 1
    used.add(name.lower())
    return name


def write_xlsx(path, sheets, rtl=False):
    """sheets: [(name, [(header, kind, width)], rows)].
    kind is "text", "int" or "money"; rows are sequences matching columns."""
    used = set()
    names = [_sheet_name(s[0], used) for s in sheets]
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", HEAD + (
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
            '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
            + "".join(
                '<Override PartName="/xl/worksheets/sheet%d.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
                % (i + 1) for i in range(len(sheets)))
            + "</Types>"))
        z.writestr("_rels/.rels", HEAD + (
            '<Relationships xmlns="%s">'
            '<Relationship Id="rId1" Type="%s/officeDocument" Target="xl/workbook.xml"/>'
            '</Relationships>' % (PKG_REL_NS, REL_NS)))
        z.writestr("xl/workbook.xml", HEAD + (
            '<workbook xmlns="%s" xmlns:r="%s"><sheets>%s</sheets></workbook>' % (
                MAIN_NS, REL_NS, "".join(
                    '<sheet name="%s" sheetId="%d" r:id="rId%d"/>' % (_text(n), i + 1, i + 1)
                    for i, n in enumerate(names)))))
        z.writestr("xl/_rels/workbook.xml.rels", HEAD + (
            '<Relationships xmlns="%s">%s'
            '<Relationship Id="rId%d" Type="%s/styles" Target="styles.xml"/>'
            '</Relationships>' % (
                PKG_REL_NS,
                "".join('<Relationship Id="rId%d" Type="%s/worksheet" '
                        'Target="worksheets/sheet%d.xml"/>' % (i + 1, REL_NS, i + 1)
                        for i in range(len(sheets))),
                len(sheets) + 1, REL_NS)))
        z.writestr("xl/styles.xml", STYLES)
        for i, (_name, columns, rows) in enumerate(sheets):
            z.writestr("xl/worksheets/sheet%d.xml" % (i + 1), _sheet_xml(columns, rows, rtl))
    return path
