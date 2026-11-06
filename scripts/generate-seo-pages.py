#!/usr/bin/env python3
"""Build SEO-ready, fully translated static HTML pages from the eleven existing resume sections.

Each /<locale>/index.html contains ONE visible language in the HTTP response,
with its own canonical, title, description and reciprocal hreflang tags.
The original root page remains a backwards-compatible landing page.
"""
from __future__ import annotations

import argparse
import html
import json
import re
from pathlib import Path
from xml.sax.saxutils import escape as xml_escape

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://musikfed.github.io/my_self/"
PROJECT_BASE = "https://musikfed.github.io/view_my_prj/"
LANGS = ("ru", "en", "zh", "de", "hi", "fr", "fi", "ko", "ja", "it", "be")
SITE_LANG = {"zh": "zh-Hans"}
LABELS = {
    "ru": "Выбрать язык", "en": "Choose language",
    "zh": "选择语言", "de": "Sprache wählen", "hi": "भाषा चुनें",
    "fr": "Choisir la langue", "fi": "Valitse kieli",
    "ko": "언어 선택", "ja": "言語を選択",
    "it": "Scegli la lingua", "be": "Выбраць мову",
}
RESUME = {
    "ru":"Резюме системного архитектора","en":"Systems Architect Resume",
    "zh":"系统架构师简历","de":"Lebenslauf Systemarchitekt",
    "hi":"सिस्टम आर्किटेक्ट रिज़्यूमे","fr":"CV d'architecte systèmes",
    "fi":"Järjestelmäarkkitehdin ansioluettelo","ko":"시스템 아키텍트 이력서",
    "ja":"システムアーキテクトの経歴書",
    "it":"Curriculum dell'architetto di sistemi",
    "be":"Рэзюмэ сістэмнага архітэктара",
}
SECTION_PATTERN = re.compile(r'<div id="(' + '|'.join(LANGS) + r')" class="lang-content(?: is-active)?">')
HEAD_END = "</head>"
FOOTER = '<footer class="site-footer"'


def write_or_check(path: Path, text: str, *, check: bool) -> None:
    if check:
        if not path.is_file() or path.read_text(encoding="utf-8") != text:
            raise SystemExit("Out-of-date localized HTML: " + str(path.relative_to(ROOT)))
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


def localized_head(source: str, lang: str, name: str, summary: str) -> str:
    head = source[: source.index(HEAD_END) + len(HEAD_END)]
    head = re.sub(r'<html lang="[^"]+"', f'<html lang="{SITE_LANG.get(lang, lang)}"', head, count=1)
    description = f"{name} — {RESUME[lang]}. {summary}"[:220]
    def attr(s: str) -> str:
        return html.escape(s, quote=True)
    head = re.sub(r'<meta name="description" content="[^"]*">', f'<meta name="description" content="{attr(description)}">', head, count=1)
    head = re.sub(r'<title>[^<]*</title>', f'<title>{html.escape(name)} — {html.escape(RESUME[lang])} | PEGINELAB</title>', head, count=1)
    head = re.sub(r'<link rel="canonical" href="[^"]+">', f'<link rel="canonical" href="{BASE}{lang}/">', head, count=1)
    alternates = "\n".join(f'<link rel="alternate" hreflang="{code}" href="{BASE}{code}/">' for code in LANGS)
    alternates += f'\n<link rel="alternate" hreflang="x-default" href="{BASE}">'
    social = ('<meta property="og:type" content="profile">\n'
              f'<meta property="og:title" content="{attr(name + " — " + RESUME[lang])}">\n'
              f'<meta property="og:description" content="{attr(description)}">\n'
              f'<meta property="og:url" content="{BASE}{lang}/">')
    return head.replace(HEAD_END, alternates + "\n" + social + "\n" + HEAD_END)


def build(*, check: bool = False) -> None:
    source = (ROOT / "index.html").read_text(encoding="utf-8")
    matches = list(SECTION_PATTERN.finditer(source))
    if [m.group(1) for m in matches] != list(LANGS):
        raise SystemExit("Resume sections missing or out of order; refusing partial locale output")
    footer_pos = source.index(FOOTER)
    final_section_end = source.rfind("\n</div>\n", matches[-1].start(), footer_pos)
    if final_section_end < 0:
        raise SystemExit("Outer resume layout no longer matches safe extraction pattern")
    header = source[source.index("<body>"): matches[0].start()]
    footer = source[footer_pos : source.index("</footer>", footer_pos) + len("</footer>")]
    label_data = re.search(r'const labels = (\{[^\n]+\});', source)
    if not label_data:
        raise SystemExit("Translation labels are unavailable")
    translations = json.loads(label_data.group(1))
    if set(translations) != set(LANGS):
        raise SystemExit("Header translation count differs from eleven languages")

    for i, match in enumerate(matches):
        lang = match.group(1)
        end = matches[i+1].start() if i+1 < len(matches) else final_section_end
        block = source[match.start():end]
        block = re.sub(r'\s*<!--[^>]*-->\s*$', "", block).rstrip()
        if not block.endswith("</div>") or "<h1>" not in block:
            raise SystemExit("Broken section extraction: " + lang)
        block = re.sub(r'class="lang-content(?: is-active)?"', 'class="lang-content is-active"', block, count=1)
        block = block.replace('./assets/', '/my_self/assets/')
        block = block.replace(PROJECT_BASE + '"', PROJECT_BASE + lang + '/"')
        name_match = re.search(r"<h1>(.*?)</h1>", block, re.S)
        intro_match = re.search(r"<div class=\"resume-hero-copy\">.*?<p>(.*?)</p>", block, re.S)
        if not name_match or not intro_match:
            raise SystemExit("Missing translated name or introduction: " + lang)
        name = html.unescape(re.sub(r'<[^>]+>', '', name_match.group(1)).strip())
        intro = html.unescape(re.sub(r'<[^>]+>', '', intro_match.group(1)).strip())
        if len(intro) < 50:
            raise SystemExit("Short translated introduction: " + lang)
        localized = header
        localized = localized.replace('data-ui="projects">Проекты', 'data-ui="projects">' + html.escape(translations[lang]["projects"]))
        localized = localized.replace('data-ui="caption">Инженерное портфолио и резюме', 'data-ui="caption">' + html.escape(translations[lang]["caption"]))
        localized = localized.replace('data-ui="language">Выбрать язык', 'data-ui="language">' + html.escape(LABELS[lang]))
        localized = localized.replace(PROJECT_BASE + '"', PROJECT_BASE + lang + '/"')
        localized_footer = footer.replace('data-ui="foot">Персональное резюме · PEGINELAB',
                                            'data-ui="foot">' + html.escape(translations[lang]["foot"]))
        # A static page must remain fully readable with JavaScript disabled.
        script = ("<script>\n(() => {\n  const current = " + json.dumps(lang) + ";\n"
                  "  const input = document.getElementById('resume-language');\n"
                  "  if (input) { input.value = current; input.addEventListener('change', () => {\n"
                  "    const next = input.value;\n"
                  "    if (/^(ru|en|zh|de|hi|fr|fi|ko|ja|it|be)$/.test(next)) "
                  "location.assign('/my_self/' + next + '/');\n"
                  "  }); }\n})();\n</script>")
        page = (localized_head(source, lang, name, intro) + "\n" + localized + "\n"
                + block + "\n</div>\n" + localized_footer + "\n" + script + "\n</body>\n</html>\n")
        if page.count('class="lang-content is-active"') != 1 or page.count('<h1>') != 1:
            raise SystemExit("Locale page unexpectedly contains multiple language sections: " + lang)
        if '#en' in page or 'data-ui="language">Язык резюме' in page:
            raise SystemExit("Legacy locale switch leaked into SEO page " + lang)
        write_or_check(ROOT / lang / "index.html", page, check=check)
        print(f"{lang}: {name} — {len(page):,} HTML characters")

    sitemap = ['<?xml version="1.0" encoding="UTF-8"?>',
               '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    sitemap += [f'  <url><loc>{xml_escape(BASE + lang + "/")}</loc></url>' for lang in LANGS]
    sitemap.append("</urlset>")
    write_or_check(ROOT / "sitemap.xml", "\n".join(sitemap) + "\n", check=check)
    write_or_check(ROOT / "robots.txt",
                   "User-agent: *\nAllow: /\nSitemap: " + BASE + "sitemap.xml\n", check=check)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="Validate generated files without changing them")
    build(check=parser.parse_args().check)
