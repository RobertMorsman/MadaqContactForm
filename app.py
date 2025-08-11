import streamlit as st
import re, html, unicodedata, json
from typing import Tuple, Dict, List

# ---------- Pagina & stijl ----------
st.set_page_config(
    page_title="Madaq Signature Generator",
    page_icon="✉️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #412119 0%, #6B4226 100%);
        padding: 2rem;
        border-radius: 10px;
        margin-bottom: 2rem;
    }
    .main-header h1 {
        color: white;
        text-align: center;
        margin-bottom: 0.5rem;
    }
    .main-header p {
        color: #f0f0f0;
        text-align: center;
        margin: 0;
    }
    .signature-preview {
        background-color: white;
        padding: 1rem;
        border-radius: 8px;
        border: 2px solid #412119;
        margin: 1rem 0;
    }
    .kv {
        font-size: 0.95rem;
        line-height: 1.6;
    }
    .kv b { color: #412119; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="main-header">
    <h1>🍫 Madaq Signature Generator</h1>
    <p>Plak hieronder het submission‑blok of upload een .txt — je ziet direct de preview en kunt de HTML downloaden. Upload optioneel ook je <code>thumbnails.json</code> voor dynamische thumbnails.</p>
</div>
""", unsafe_allow_html=True)

# ---------- Helpers ----------
DUTCH_MOBILE_RE = re.compile(r'^(\+31|0031|0)6[0-9]{8}$')
DUTCH_LANDLINE_RE = re.compile(r'^(\+31|0031|0)[1-9][0-9]{7,8}$')
PHONE_E164_RE = re.compile(r'^\+?[1-9]\d{7,14}$')

DEFAULT_THUMB = {
    "image_url": "https://cdn.shopify.com/s/files/1/0729/8203/6780/files/bonbon3.png?v=1684836531",
    "label": "Madaq Bonbon"
}

def smart_title(name: str) -> str:
    """Titelcase met behoud van delen na apostrof/koppelteken (van-der, D'Angelo)."""
    name = name.strip()
    if not name:
        return ""
    parts = re.split(r'(\s+)', name)  # behoud spaties
    def cap_piece(p: str) -> str:
        sub = re.split(r"(-|')", p)  # behoud - en '
        return "".join(s.capitalize() if s not in ["-", "'"] else s for s in sub)
    return "".join(cap_piece(p) if not p.isspace() else p for p in parts)

def is_valid_phone(phone: str) -> bool:
    clean = re.sub(r'[\s\-\(\)]', '', phone)
    if DUTCH_MOBILE_RE.match(clean) or DUTCH_LANDLINE_RE.match(clean):
        return True
    return PHONE_E164_RE.match(clean) is not None

def normalize_phone(phone: str) -> str:
    clean = re.sub(r'[\s\-\(\)]', '', phone)
    if clean.startswith('06') and len(clean) == 10:
        return '+31' + clean[1:]
    elif clean.startswith('0') and not clean.startswith('06'):
        return '+31' + clean[1:]
    elif not clean.startswith('+'):
        return '+' + clean
    return clean

def build_tel_link(phone: str) -> str:
    return f"tel:{normalize_phone(phone)}"

def remove_accents(s: str) -> str:
    nfkd = unicodedata.normalize('NFKD', s)
    return ''.join(c for c in nfkd if not unicodedata.combining(c))

def safe_filename(first_name: str, last_name: str) -> str:
    raw = f"{first_name}{last_name}"
    normalized = remove_accents(raw)
    safe = re.sub(r'[^a-zA-Z0-9]', '', normalized)
    return safe or "signature"

def generate_company_email(first_name: str, last_name: str) -> str:
    """{eerste_letter}.{achternaam}@madaq.com, spaties/tekens verwijderd, lowercase."""
    first = first_name.strip()
    last = last_name.strip()
    if not first or not last:
        return ""
    first_letter = first[0].lower()
    clean_last = re.sub(r'[^\w]', '', last).lower()
    return f"{first_letter}.{clean_last}@madaq.com"

# ---------- Parser voor het aangeleverde tekstformaat ----------
FIELD_MAP = {
    "name": r"^Name:\s*(.+)$",
    "surname": r"^Surname:\s*(.+)$",
    "email": r"^Email:\s*(.+)$",
    "phone": r"^Phone Number:\s*(.+)$",
    "job_title": r"^Job Title:\s*(.+)$",
    "favourite_bonbon": r"^Favourite bonbon:\s*(.+)$",
}

def parse_submission(text: str) -> Dict[str, str]:
    """Parseert het blok en geeft dict terug met velden (lege string als niet gevonden)."""
    data = {k: "" for k in FIELD_MAP}
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    for key, pattern in FIELD_MAP.items():
        regex = re.compile(pattern, re.IGNORECASE)
        for ln in lines:
            m = regex.match(ln)
            if m:
                data[key] = m.group(1).strip()
                break
    return data

# ---------- Thumbnail rules ----------
def _norm(s: str) -> str:
    s = s or ""
    s = s.strip().lower()
    s = "".join(c for c in unicodedata.normalize('NFKD', s) if not unicodedata.combining(c))
    return s

def load_thumb_rules_from_file(path: str = "thumbnails.json") -> List[Dict]:
    """Probeer lokale thumbnails.json te laden (niet verplicht)."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception:
        return []

def pick_thumbnail(user_text: str, rules: List[Dict], default: Dict = DEFAULT_THUMB) -> Dict:
    """Kies hoogste priority regel waarvan een keyword voorkomt in de user_text (substring match)."""
    t = _norm(user_text)
    best = None
    for rule in sorted(rules, key=lambda r: r.get("priority", 0), reverse=True):
        for kw in rule.get("keywords", []):
            if _norm(kw) in t:
                best = rule
                break
        if best:
            break
    return best or default

# ---------- Signature HTML ----------
def render_signature_html(first_name: str, last_name: str, job_title: str, phone: str,
                          favourite_bonbon: str, thumb_rules: List[Dict]) -> str:
    # Format naam
    full_name = f"{smart_title(first_name)} {smart_title(last_name)}".strip()
    full_name_html = html.escape(full_name)

    # Job title: altijd eerste letter hoofdletter, rest ongewijzigd
    jt_raw = job_title.strip()
    job_title_formatted = (jt_raw[:1].upper() + jt_raw[1:]) if jt_raw else ""
    job_title_html = html.escape(job_title_formatted)

    # Overige velden
    fav_bonbon_html = html.escape(favourite_bonbon.strip())
    phone_text_html = html.escape(phone.strip())
    tel_href = build_tel_link(phone.strip())
    derived_email = generate_company_email(first_name, last_name)
    email_text_html = html.escape(derived_email)
    mailto_href = f"mailto:{derived_email}"

    # English favourite label: "Robert's favourite"
    first_n = smart_title(first_name).strip()
    fav_title = f"{first_n}'s favourite" if first_n else "Favourite"
    fav_title_html = html.escape(fav_title)

    # Thumbnail kiezen
    thumb = pick_thumbnail(favourite_bonbon, thumb_rules, DEFAULT_THUMB)
    thumb_url = thumb.get("image_url", DEFAULT_THUMB["image_url"])
    thumb_label = thumb.get("label", DEFAULT_THUMB["label"])

    signature_html = f"""
<div style="font-family: Avenir, Arial, Helvetica, sans-serif;">
    <p style="font-size: 11pt; margin: 0 0 10px 0;">Kind regards,</p>

    <table style="width: 800px; font-size: 11pt; font-family: Avenir, Arial, Helvetica, sans-serif;" cellpadding="0" cellspacing="0" border="0">
    <tbody>
     <tr>
        <td style="width:82px;" width="82">
            <p style="margin: 0px; padding: 0px;">
                <a href="https://madaq.com/" target="_blank" rel="noopener">
                    <img border="0" alt="Madaq Logo" width="80" style="width:80px; height:auto; border:0;"
                         src="https://cdn.shopify.com/s/files/1/0729/8203/6780/files/Madaq-logo-donkerbruin-zwart.png?v=1684943708">
                </a>
            </p>
        </td>
        <td style="width: 15px;"></td>
        <td style="min-width: 200px; vertical-align: top;">
            <div style="font-weight: bold; font-size: 14pt; line-height: 16pt; color:#000000; margin-bottom: 5px;">
                {full_name_html}
            </div>
            <div style="color:#333333; font-size: 10pt; line-height: 14pt; margin-bottom: 10px;">
                {job_title_html}
            </div>

            <div style="margin-top: 10px;">
                <a href="https://www.facebook.com/madak.chocolatier/" target="_blank" rel="noopener" style="margin-right: 5px;">
                    <img border="0" alt="Facebook" style="border:0; height:25px; width:25px;"
                         src="https://cdn.shopify.com/s/files/1/0729/8203/6780/files/facebook.png?v=1684920878">
                </a>
                <a href="https://nl.linkedin.com/company/madak" target="_blank" rel="noopener" style="margin-right: 5px;">
                    <img border="0" alt="LinkedIn" style="border:0; height:25px; width:25px;"
                         src="https://cdn.shopify.com/s/files/1/0729/8203/6780/files/linkedin.png?v=1684920878">
                </a>
                <a href="https://www.instagram.com/madaqchocolates/" target="_blank" rel="noopener">
                    <img border="0" alt="Instagram" style="border:0; height:25px; width:25px;"
                         src="https://cdn.shopify.com/s/files/1/0729/8203/6780/files/instagram.png?v=1684920878">
                </a>
            </div>
        </td>
        <td style="width: 2px; border-right: 2px solid #412119; height: 80px;"></td>
        <td style="width: 15px;"></td>
        <td style="min-width: 175px; vertical-align: top;">
            <div style="font-size: 10pt; line-height: 14pt;">
                <div style="margin-bottom: 3px;">
                    <a href="{tel_href}" style="text-decoration:none; color:#333333;">{phone_text_html}</a>
                </div>
                <div style="margin-bottom: 3px;">
                    <a href="{mailto_href}" style="text-decoration: none; color:#333333;">{email_text_html}</a>
                </div>
                <div style="margin-bottom: 3px;">
                    <a href="https://www.madaq.com" style="text-decoration: none; color:#333333;">www.madaq.com</a>
                </div>
                <div style="color:#333333;">
                    Florijnweg 23B<br>
                    6883 JN Velp
                </div>
            </div>
        </td>
        <td style="width: 2px; border-right: 2px solid #412119; height: 80px;"></td>
        <td style="width: 15px;"></td>
        <td style="width:67px;" width="67">
            <p style="margin: 0px; padding: 0px;">
                <a href="#" target="_blank" rel="noopener">
                    <img border="0" alt="{html.escape(thumb_label)}" width="67" style="width:67px; height:auto; border:0;"
                         src="{thumb_url}">
                </a>
            </p>
        </td>
        <td style="width: 15px;"></td>
        <td style="width: 160px; vertical-align: top;">
            <div style="color:#412119; font-weight: bold; font-size: 14pt; line-height: 16pt; margin-bottom: 5px;">
                {fav_title_html}
            </div>
            <div style="color:#412119; font-size: 10pt; line-height: 14pt; margin-bottom: 8px;">
                {fav_bonbon_html}
            </div>
            <div style="color:#412119; font-size: 10pt; line-height: 14pt;">
                What's yours?
            </div>
        </td>
     </tr>
    </tbody>
    </table>
</div>
"""
    return signature_html

# ---------- Invoer (textarea/.txt + thumbnails.json upload) ----------
left, right = st.columns([1.1, 1])

with left:
    st.markdown("### 🧾 Plak of upload het submission‑blok")
    uploaded_txt = st.file_uploader("Upload .txt", type=["txt"], key="uploader_txt", help="Upload het tekstbestand met de submission.")

    default_text = """New contact form submission received:

Date & Time: 2025-08-11 12:46:25

Contact Details:
================
Name: robert
Surname: morsman
Email: r.morsman@madaq.com
Phone Number: +316 37 01 16 14
Job Title: baasje
Favourite bonbon: Yuzu caramel

Best regards,
Je digitale maatje
"""
    text_value = st.text_area("Of plak hier de tekst", value=default_text, height=320, key="submission_text")

    if uploaded_txt is not None:
        try:
            raw_text = uploaded_txt.read().decode("utf-8", errors="ignore")
        except Exception:
            raw_text = text_value
    else:
        raw_text = text_value

    st.markdown("### 🖼️ Thumbnails mapping")
    uploaded_json = st.file_uploader("Upload thumbnails.json", type=["json"], key="uploader_json",
                                     help="JSON met regels: keywords, image_url, label, priority.")

    if "thumb_rules" not in st.session_state:
        # probeer lokale thumbnails.json (optioneel, geen fout als niet aanwezig)
        st.session_state.thumb_rules = load_thumb_rules_from_file()

    if uploaded_json is not None:
        try:
            st.session_state.thumb_rules = json.load(uploaded_json)
            st.success("Thumbnail-regels geladen uit geüpload JSON.")
        except Exception as e:
            st.error(f"Kon JSON niet lezen: {e}")

# Parse op elke rerun (live)
parsed = parse_submission(raw_text or "")

# Post-processing/formatting
first_name = smart_title(parsed.get("name", ""))
last_name = smart_title(parsed.get("surname", ""))

# Job title: altijd eerste letter hoofdletter, rest ongewijzigd
job_title_raw = parsed.get("job_title", "").strip()
job_title = job_title_raw[:1].upper() + job_title_raw[1:] if job_title_raw else ""

phone_in = parsed.get("phone", "").strip()
fav_bonbon = parsed.get("favourite_bonbon", "").strip()

# ---------- Live preview & download ----------
with right:
    st.markdown("### 👀 Live preview")
    sig_html = render_signature_html(first_name, last_name, job_title, phone_in, fav_bonbon,
                                     st.session_state.get("thumb_rules", []))
    st.markdown('<div class="signature-preview">', unsafe_allow_html=True)
    st.markdown(sig_html, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    fname_base = safe_filename(first_name, last_name)
    st.download_button(
        label="📥 Download HTML‑handtekening",
        data=sig_html,
        file_name=f"{fname_base}_signature.html",
        mime="text/html",
        use_container_width=True
    )

# Info-paneel met geparseerde data
st.markdown("### 🔎 Geparseerde gegevens")
colA, colB = st.columns(2)
with colA:
    st.markdown('<div class="kv">', unsafe_allow_html=True)
    st.markdown(f"<b>Voornaam:</b> {first_name or '—'}", unsafe_allow_html=True)
    st.markdown(f"<b>Achternaam:</b> {last_name or '—'}", unsafe_allow_html=True)
    st.markdown(f"<b>Functie:</b> {job_title or '—'}", unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
with colB:
    derived_email = generate_company_email(first_name, last_name)
    thumb = pick_thumbnail(fav_bonbon, st.session_state.get("thumb_rules", []), DEFAULT_THUMB)
    st.markdown('<div class="kv">', unsafe_allow_html=True)
    st.markdown(f"<b>Telefoon (weergegeven):</b> {phone_in or '—'}", unsafe_allow_html=True)
    st.markdown(f"<b>Tel‑link:</b> {build_tel_link(phone_in) if phone_in else '—'}", unsafe_allow_html=True)
    st.markdown(f"<b>Bedrijfs‑e‑mail:</b> {derived_email or '—'}", unsafe_allow_html=True)
    st.markdown(f"<b>Gekozen thumbnail:</b> {thumb.get('label', '—')} → <code>{thumb.get('image_url', '')}</code>", unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
