#!/usr/bin/env python3
"""Greek AI-writing tell checker.

Usage:
  python3 check.py text.txt                 # score one text
  python3 check.py before.txt after.txt     # compare: tells removed, facts kept, length

Score = weighted count of AI tells per 100 words (lower is better).
"""
import re
import sys
import unicodedata

def norm(s):
    # lowercase and strip accents so patterns match regardless of tonos
    s = unicodedata.normalize("NFD", s.lower())
    return "".join(c for c in s if unicodedata.category(c) != "Mn")

# (category, weight, regex on normalized text)
PHRASES = [
    # A. inflated vocabulary / cliches
    ("A", 3, r"στον σημερινο (ψηφιακο )?κοσμο|στη σημερινη εποχη|σε μια εποχη οπου|σε (εναν|ενα|μια) ολοενα και πιο \w+"),
    ("A", 1, r"πολυτιμ\w+ (εμπειρια|μελος|εργαλειο|συμμαχ)|ιδανικη επιλογη|πιστευω ακραδαντα|με την παρουσα επιστολη|διευρυνω τους οριζοντες|πηγαζει απο τη βαθια|ευθυγραμμιζεται|σηματοδοτησε|κομβικης σημασιας|\bεμβαθυν\w*|πραγματικο δωρο|δεν θα ξεχασω ποτε"),
    ("A", 1, r"κυριαρχειται απο|χαρακτηριζεται απο (μια σειρα|)|διαμορφων\w+ (το|τον) δημοσιο διαλογο|επανερχεται στο προσκηνιο|βρισκ\w+ απηχηση|με ιδιαιτερη εμφαση|κρισιμ\w+ (πληροφοριες|ρολο|σημασιας)|κορυφαι\w+ (ερευνητικ|πανεπιστημ|ιδρυμ)\w*|σημαντικ\w+ προοπτικ"),
    ("A", 1, r"προνομιακη τοποθεσια|αξεχαστ\w+ (διαμονη|εμπειρια|στιγμ)|\bιδανικ\w+ για (ζευγαρια|οικογενειες|οσους|ολους)|με μοναδικο τροπο|ειχα την τιμη|εξαιρετικη (μου )?ομαδα|ειναι το κλειδι (της|για)|το ζητουμενο ειναι|να βρουμε (μια|την) ισορροπια|ζητω συγγνωμη για την (αναστατωση|ταλαιπωρια)|ελπιζω να εισαι καλα"),
    ("C", 1, r"(μου|μας) εμαθε (πολλα )?για \w+ \w+, \w+ \w+ \w+ και"),
    ("A", 2, r"ταξιδι (αυτογνωσιας|μαθησης|ζωης)|\w+ (μου|μας) ταξιδι\b|το ταξιδι ειναι πιο|αυτο το ταξιδι"),
    ("C", 1, r"\bτοσο (σε |στο |στη |στην |στον )?\w+ οσο και\b"),
    ("A", 2, r"αξιζει να σημειωθει|ειναι σημαντικο να (τονιστει|σημειωθει|γνωριζ)|δεν πρεπει να παραβλεψουμε|θα πρεπει να εχουμε κατα νου"),
    ("A", 2, r"διαδραματιζ\w* (καθοριστικο|κομβικο|σημαντικο|κεντρικο|ζωτικο) ρολο|ακρογωνιαι\w* λιθ"),
    ("A", 1, r"\bπληθωρα\b|\bπολυπλευρ\w+|ολιστικ\w+ (προσεγγιση|λυση)|\bαπροσκοπτ\w+|\bαδιαμφισβητητα\b|\bαναμφιβολα\b|\bαπαραμιλλ\w+"),
    ("A", 1, r"\bαναδεικνυ\w*|\bυπογραμμιζ\w*|\bοικοσυστημα\b|φερ\w* στο φως|πολλα υποσχομεν\w+|ανοιγοντας τον δρομο"),
    ("A", 2, r"ας (εμβαθυνουμε|βουτηξουμε)|κανει νοημα|στο τελος της ημερας|ρολο-κλειδι|ειμαι ενθουσιασμεν\w+ να (ανακοινωσω|μοιραστω)"),
    # B. bureaucratic syntax
    ("B", 1, r"σε ο,?τι αφορα|\bοσον αφορα\b|στο πλαισιο τ(ης|ου|ων)|\bπροκειμενου να\b|με στοχο την|μεσω της χρησης|η παρουσα εργασια επιχειρει"),
    ("B", 1, r"\b(πραγματοποι|επιτυγχανετ|λαμβανει χωρα)\w*"),
    # C. repeated structures
    ("C", 3, r"δεν (ειναι|ηταν|αποτελει|αποτελουν|προκειται)( για)? (απλως|απλα|μονο)\b|\bοχι μονο\b[^.;!\n]{1,80}\bαλλα και\b"),
    ("C", 2, r"\bδεν (ειναι|ηταν) (το|η|ο|τα|οι) [^,.;\n]{1,40}, αλλα\b"),
    ("C", 2, r"(το αποτελεσμα|ο λογος|η απαντηση|το μυστικο)\s*;"),
    ("C", 2, r"εχεις αναρωτηθει ποτε|εχετε αναρωτηθει ποτε|\bανακαλυψτε\b|\bφανταστειτε\b"),
    # D. vague attributions
    ("D", 2, r"οι ειδικοι (επισημαινουν|τονιζουν|λενε)|συμφωνα με τους ειδικους|μελετες δειχνουν|πολλοι πιστευουν"),
    # E. chatbot tone / closings
    ("E", 3, r"εξαιρετικη ερωτηση|\bαπολυτως!|ελπιζω (αυτο|αυτα|να) (να )?(βοηθ|σας βοηθ|σε βοηθ)|μη διστασ\w+ να|ας δουμε μαζι"),
    ("E", 3, r"θελ(εις|ετε) (μια|να|να σου|να σας) [^\n?;]{0,250}[?;\u037e]|αν θελ(εις|ετε),? μπορω να"),
    ("E", 2, r"εν κατακλειδι|\bσυνοψιζοντας\b|\bσυμπερασματικα\b|το μελλον (προμηνυεται|φαινεται) λαμπρ|σε τελικη αναλυση"),
    ("E", 1, r"ελπιζω το παρον μηνυμα|τον πολυτιμο χρονο σας|εκ των προτερων για την κατανοηση"),
]

SENT_CONNECTIVES = r"(επιπλεον|επιπροσθετα|ωστοσο|παραλληλα|ταυτοχρονα|επιπροσθετως|επιπλεον τουτου|τελος|ακομη|συνεπως)\s*,"

def sentences(text):
    return [s.strip() for s in re.split(r"(?<=[.!;?·])\s+|\n+", text) if s.strip()]

def score(text):
    n = norm(text)
    words = max(1, len(re.findall(r"\w+", text)))
    hits = []
    for cat, w, pat in PHRASES:
        for m in re.finditer(pat, n):
            hits.append((cat, w, m.group(0)))
    sents = sentences(text)
    # C: trailing participle  ", ...οντας/ωντας <= 8 words to sentence end"
    for s in sents:
        ns = norm(s)
        ns = re.sub(r"\[[^\]]*\]\([^)]*\)", "", ns).strip()
        m = re.search(r",\s*(\w+(οντας|ωντας))\b[^;!]{0,170}[.;!]?$", ns)
        if m:
            hits.append(("C", 2, "μετοχή στο τέλος: " + m.group(1)))
    # C: sentence-initial connectives, counts only when repeated (>=2)
    conn = [s for s in sents if re.match(SENT_CONNECTIVES, norm(s))]
    if len(conn) >= 2:
        for s in conn:
            hits.append(("C", 1, "συνδετικό στην αρχή: " + s.split(",")[0]))
    # B: chains of 3+ genitive articles in a short window
    for m in re.finditer(r"(\b(της|του|των)\b\s+\w+\s+){3,}", n):
        hits.append(("B", 1, "αλυσίδα γενικών"))
    # B: repeated ο οποιος/η οποια in one sentence
    for s in sents:
        if len(re.findall(r"\b(ο|η|το|οι|τα|του|της|των|τον|την|τους|τις)\s+οποι\w+", norm(s))) >= 2:
            hits.append(("B", 1, "διπλό «ο οποίος»"))
    # F: typography
    if re.search(r"[α-ωά-ώ]", text) and re.search(r"\"[^\"\n]{1,80}\"", text):
        hits.append(("F", 1, 'αγγλικά εισαγωγικά ""'))
    dashes = len(re.findall(r"\s—\s|\s–\s", text))
    if dashes:
        hits.append(("F", dashes, f"{dashes} μακριές παύλες"))
    # A: «αποτελεί» used as a fancy «είναι», counts from the 2nd use
    apot = len(re.findall(r"\bαποτελ(ει|ουν|εσε|ουσε)\b", n))
    if apot >= 2:
        hits.append(("A", apot - 1, f"{apot}× «αποτελεί»"))
    # C: section scaffolding «Στο πολιτικό πεδίο… Στο διεθνές επίπεδο…»
    scaff = len(re.findall(r"\bστο (πολιτικο|κοινωνικο|διεθνες|οικονομικο|επιστημονικο|τεχνολογικο|προσωπικο|ακαδημαικο|επαγγελματικο) (πεδιο|επιπεδο)", n))
    if scaff >= 2:
        hits.append(("C", scaff, f"{scaff}× «Στο … πεδίο/επίπεδο»"))
    # A: «σημαντικός/κρίσιμος» overuse
    sim = len(re.findall(r"\b(σημαντικ|κρισιμ)\w*", n))
    if sim >= 3 and sim * 100 / words > 1.2:
        hits.append(("A", sim - 2, f"{sim}× «σημαντικός/κρίσιμος»"))
    # F: chatbot citation leftovers (same source repeated on consecutive lines / same link many times)
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    dup = sum(1 for a, b in zip(lines, lines[1:]) if a == b and len(a) < 40)
    links = re.findall(r"\]\((https?://[^)]+)\)", text)
    if dup:
        hits.append(("F", dup, f"{dup} διπλές γραμμές πηγής"))
    if links and len(links) >= 3 and len(set(links)) == 1:
        hits.append(("F", 1, f"{len(links)}× ίδιο link"))
    # F: emoji
    emoji = len(re.findall(r"[\U0001F300-\U0001FAFF☀-➿]", text))
    if emoji >= 2:
        hits.append(("F", emoji // 2, f"{emoji} emoji"))
    hashtags = len(re.findall(r"#\w+", text))
    if hashtags > 4:
        hits.append(("F", 1, f"{hashtags} hashtags"))
    for line in text.splitlines():
        l = line.strip().lstrip("#").strip()
        ws = [w for w in re.findall(r"[^\W\d_]+", l) if len(w) > 3]
        if 3 <= len(ws) <= 12 and not l.endswith((".", ";", ":", "?")) and all(w[0].isupper() for w in ws) and not l.isupper():
            hits.append(("F", 1, "Title Case: " + l[:40]))
    # bold outside list items (bold labels at the start of list items are a normal convention)
    bold = len(re.findall(r"\*\*[^*]+\*\*", "\n".join(l for l in text.splitlines() if not re.match(r"\s*([-*•]|\d+[.)])\s", l))))
    if bold > max(3, words // 60):
        hits.append(("F", 1, f"{bold} bold"))
    total = sum(w for _, w, _ in hits)
    return total, round(100 * total / words, 2), hits, words

FACT_PATTERNS = [
    r"\d+(?:[.,]\d+)*%?",                     # numbers, dates, percentages
    r"\b[A-Za-z][A-Za-z0-9_.+#/-]*[A-Za-z0-9+#]\b",  # latin tokens: names, code, terms
    r"«[^»]{1,40}»",                           # quoted terms
]
STOP_LATIN = {"the", "and", "of", "Sent", "from", "my", "iPhone"}

def facts(text):
    out = set()
    for p in FACT_PATTERNS:
        for m in re.findall(p, text):
            if m not in STOP_LATIN:
                out.add(m)
    # capitalized Greek words not at sentence start (proper names); skip Title Case heading lines
    body = "\n".join(l for l in text.splitlines()
                     if not (l.strip() and not l.strip().endswith((".", ";", ":", "?", "!", ",")) and len(l.split()) <= 12))
    for s in sentences(body):
        for w in re.findall(r"(?<=\s)[Α-ΩΆ-Ώ][α-ωά-ώ]{2,}", s):
            out.add(norm(w)[:5])  # stem, case-insensitive
    return out

def compare(before, after):
    tb, db, _, wb = score(before)
    ta, da, hits, wa = score(after)
    fb, fa_raw = facts(before), facts(after)
    fa = fa_raw | {norm(x)[:5] for x in fa_raw}
    lost = sorted(x for x in fb if x not in fa and norm(x)[:5] not in fa)
    added = sorted(x for x in fa_raw if re.match(r"\d", x) and x not in fb)
    return {
        "tells_before": tb, "tells_after": ta,
        "density_before": db, "density_after": da,
        "removed_pct": round(100 * (tb - ta) / tb, 1) if tb else None,
        "facts_lost": lost, "numbers_added": added,
        "length_ratio": round(wa / wb, 2),
        "remaining": [h[2] for h in hits],
    }

if __name__ == "__main__":
    if len(sys.argv) == 2:
        t, d, hits, w = score(open(sys.argv[1], encoding="utf-8").read())
        print(f"words={w} tells={t} per100w={d}")
        for c, wt, h in hits:
            print(f"  [{c}] +{wt} {h}")
    elif len(sys.argv) == 3:
        import json
        r = compare(open(sys.argv[1], encoding="utf-8").read(), open(sys.argv[2], encoding="utf-8").read())
        print(json.dumps(r, ensure_ascii=False, indent=1))
    else:
        print(__doc__)
