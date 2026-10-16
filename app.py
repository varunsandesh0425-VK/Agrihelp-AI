import base64
import hashlib
import json
import os
import uuid
from datetime import date, timedelta
from io import BytesIO
from pathlib import Path

import requests
import streamlit as st
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from gtts import gTTS
from gtts.tts import gTTSError
from PIL import Image, UnidentifiedImageError
import speech_recognition as sr
from streamlit.errors import StreamlitSecretNotFoundError


st.set_page_config(
    page_title="AgriHelp AI",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="expanded",
)

farm_background = base64.b64encode(
    (Path(__file__).parent / "assets" / "farm-background.webp").read_bytes()
).decode("ascii")

st.markdown(
    """
    <style>
    .stApp {
        background-image:
            linear-gradient(rgb(112 139 83 / 12%), rgb(92 69 43 / 14%)),
            url("data:image/webp;base64,__FARM_BACKGROUND__");
        background-position: center center;
        background-repeat: no-repeat;
        background-size: cover;
        background-attachment: fixed;
    }
    .block-container {
        max-width: 1180px;
        padding-top: 1.5rem;
        padding-bottom: 3rem;
        border-radius: 1.25rem;
    }
    .stApp [data-testid="stMain"] [data-testid="stColumn"] div[data-testid="stButton"] > button[data-testid^="stBaseButton"] {
        min-height: 4.25rem;
        padding: .8rem 1rem;
        border: 1px solid rgb(91 132 73 / 55%);
        border-left: 4px solid #4c7d43;
        border-radius: 1rem;
        background: rgb(74 126 66 / 16%);
        color: inherit !important;
        box-shadow: 0 3px 12px rgb(35 60 35 / 10%);
        font-weight: 650;
        text-align: left;
        transition: border-color .15s ease, box-shadow .15s ease, transform .15s ease;
    }
    .stApp [data-testid="stMain"] [data-testid="stColumn"] div[data-testid="stButton"] > button[data-testid^="stBaseButton"]:hover {
        border-color: #4c7d43;
        background: rgb(74 126 66 / 25%);
        color: inherit !important;
        box-shadow: 0 6px 18px rgb(35 60 35 / 16%);
        transform: translateY(-1px);
    }
    .stApp [data-testid="stMain"] [data-testid="stColumn"] div[data-testid="stButton"] > button[data-testid^="stBaseButton"]:focus-visible {
        outline: 3px solid #659354;
        outline-offset: 2px;
    }
    .stApp [data-testid="stMain"] [data-testid="stColumn"] [data-testid="stMarkdownContainer"] {
        display: block;
        overflow: visible;
        white-space: normal;
        -webkit-line-clamp: unset;
    }
    .stApp [data-testid="stMain"] [data-testid="stColumn"] [data-testid="stMarkdownContainer"] p {
        margin: 0;
        overflow-wrap: anywhere;
        white-space: normal;
    }
    .stApp [data-testid="stSidebar"] [data-testid="stButton"] > button[data-testid^="stBaseButton"] {
        min-height: 2.75rem;
        border-radius: .75rem;
        color: var(--text-color);
        background: rgb(74 126 66 / 12%);
    }
    @media (max-width: 650px) {
        .block-container {
            padding: 1rem .8rem 2rem;
        }
        .stApp [data-testid="stMain"] [data-testid="stColumn"] div[data-testid="stButton"] > button[data-testid^="stBaseButton"] {
            min-height: 4rem;
            padding: .7rem .8rem;
            font-size: .95rem;
        }
    }
    </style>
    """.replace("__FARM_BACKGROUND__", farm_background),
    unsafe_allow_html=True,
)

LANGUAGES = {"English": "en", "తెలుగు": "te", "हिन्दी": "hi"}
TEXT = {
    "en": {
        "tagline": "Practical farming guidance, useful tools, and trusted links.",
        "language": "Language",
        "navigation": "Navigation",
        "dashboard": "Dashboard",
        "crop_help": "Crop disease help",
        "weather": "Weather",
        "schemes": "Government schemes",
        "vault": "Private document vault",
        "tools": "Farmer tools",
        "prices": "Market prices",
        "contacts": "Help & emergency contacts",
        "welcome": "Welcome to AgriHelp AI",
        "welcome_text": "Choose a tool from the navigation menu. Weather and market information are fetched from their named sources when available.",
        "crop": "Crop name",
        "problem": "Describe crop symptoms",
        "analyze": "Analyze",
        "upload": "Crop photo (optional)",
        "possible": "Possible causes — not a confirmed diagnosis",
        "causes": "Possible causes",
        "care": "Basic care",
        "prevention": "Prevention",
        "expert": "When to contact an agriculture expert",
        "disclaimer": "Informational guidance only. This app cannot confirm a crop disease and is not a substitute for a qualified local agriculture expert. Follow local advice and product labels.",
        "image_note": "The image check looks only for broad yellow/brown color patterns. Lighting, soil, and background objects can affect it; it does not identify a disease.",
        "image_yellow": "Yellow or yellow-green areas are noticeable ({:.1f}% of sampled pixels). Lighting and background objects can affect this.",
        "image_brown": "Brown-colored areas are noticeable ({:.1f}% of sampled pixels). These may be soil or background, not crop damage.",
        "image_none": "The simple color check found no clear yellow or brown pattern. This does not rule out a crop problem.",
        "need_problem": "Describe the problem or upload a photo before analyzing.",
        "image_error": "This image could not be read. Please try a PNG or JPEG photo.",
        "photo_observations": "Photo observations (local color check)",
        "no_match": "No clear symptom match. Check soil moisture, drainage, pests, and recent weather; note when symptoms began and whether they are spreading.",
        "weather_title": "Local weather and 5-day forecast",
        "place": "Town, village, or district in India",
        "get_weather": "Get weather",
        "temperature": "Temperature",
        "humidity": "Humidity",
        "rain_now": "Current precipitation",
        "forecast": "Daily forecast",
        "source": "Source",
        "weather_error": "Weather data could not be loaded. Check your internet connection and try again.",
        "place_error": "No matching Indian location found. Try a nearby town or district name.",
        "schemes_title": "Government scheme directory",
        "central": "Central Government",
        "state": "Andhra Pradesh",
        "eligibility": "Who may qualify",
        "benefit": "Potential support",
        "verify": "Eligibility and current benefits can change. Verify details on the official portal before applying.",
        "open_official": "Open official portal",
        "vault_title": "Encrypted personal document vault",
        "vault_note": "Documents are encrypted on this server with a key derived from your passphrase. Use a long, unique passphrase and remember it: it cannot be recovered. This is a local-file vault, not an audited cloud storage service. Avoid uploading unmasked Aadhaar unless essential.",
        "account": "Vault name (not a login account)",
        "passphrase": "Vault passphrase",
        "confirm": "Confirm passphrase",
        "unlock": "Create / unlock vault",
        "new_vault": "First use: create a vault with a passphrase of at least 12 characters.",
        "wrong_pass": "Could not unlock the vault. Check the passphrase.",
        "pass_mismatch": "Passphrases do not match.",
        "short_pass": "Use at least 12 characters for your passphrase.",
        "vault_open": "Vault unlocked on this browser session.",
        "lock": "Lock vault",
        "choose_doc": "Choose a document to encrypt and save",
        "save_doc": "Encrypt and save document",
        "size_error": "The file exceeds the 10 MB upload limit.",
        "saved": "Document encrypted and saved.",
        "stored_docs": "Stored documents",
        "empty_vault": "No documents saved yet.",
        "download": "Download decrypted copy",
        "delete": "Delete",
        "vault_storage_warning": "The encrypted files stay on this machine's disk. Many free cloud hosts use temporary storage that may be wiped on restart; this vault is not suitable for production document retention without persistent private storage and a security review.",
        "vault_public_warning": "Do not upload real Aadhaar or land records to a public deployment. This hackathon app has no user login system or independent security audit.",
        "tools_title": "Practical farmer tools",
        "calendar": "Crop calendar",
        "crop_for_calendar": "Crop",
        "sowing_date": "Sowing / planting date",
        "create_calendar": "Build reminder calendar",
        "calendar_note": "Generic reminders only—not a crop-specific agronomy schedule. Confirm timings with your local agriculture department.",
        "emergence": "Check germination/emergence",
        "weed_check": "Check weeds, moisture, and early growth",
        "field_check": "Inspect plants, pests, and soil moisture",
        "irrigation": "Irrigation tips",
        "fertilizer": "Fertilizer guidance",
        "market_title": "Live mandi prices",
        "commodity": "Commodity name (English)",
        "state_name": "State",
        "district": "District (optional)",
        "load_prices": "Fetch latest reported prices",
        "price_key_missing": "Live mandi data needs a free API key from data.gov.in. Set DATA_GOV_IN_API_KEY in the deployment environment or Streamlit secrets; no prices are shown when the key is missing.",
        "no_prices": "No records were returned for that selection. Try another commodity or district.",
        "contacts_title": "Agriculture help and emergency contacts",
        "kcc": "Kisan Call Centre",
        "kcc_note": "For farming-related questions in India; language support depends on availability.",
        "emergency": "Emergency services",
        "emergency_note": "For immediate danger to people, call India's emergency number.",
    },
    "te": {
        "tagline": "వ్యవసాయ సూచనలు, ఉపయోగకరమైన సాధనాలు, నమ్మదగిన లింకులు.",
        "language": "భాష",
        "navigation": "నావిగేషన్",
        "dashboard": "డాష్‌బోర్డ్",
        "crop_help": "పంట సమస్య సహాయం",
        "weather": "వాతావరణం",
        "schemes": "ప్రభుత్వ పథకాలు",
        "vault": "వ్యక్తిగత పత్రాల భద్రపేటిక",
        "tools": "రైతు సాధనాలు",
        "prices": "మార్కెట్ ధరలు",
        "contacts": "సహాయం / అత్యవసర సంప్రదింపులు",
        "welcome": "AgriHelp AIకి స్వాగతం",
        "welcome_text": "నావిగేషన్ మెనులో ఒక సాధనాన్ని ఎంచుకోండి. వాతావరణం, మార్కెట్ సమాచారం అందుబాటులో ఉన్నప్పుడు పేర్కొన్న వనరుల నుంచి పొందబడుతుంది.",
        "crop": "పంట పేరు",
        "problem": "పంట లక్షణాలను వివరించండి",
        "analyze": "విశ్లేషించండి",
        "upload": "పంట ఫోటో (ఐచ్ఛికం)",
        "possible": "సంభావ్య కారణాలు — నిర్ధారిత వ్యాధి నిర్ధారణ కాదు",
        "causes": "సంభావ్య కారణాలు",
        "care": "ప్రాథమిక సంరక్షణ",
        "prevention": "నివారణ",
        "expert": "వ్యవసాయ నిపుణుడిని ఎప్పుడు సంప్రదించాలి",
        "disclaimer": "ఇది సమాచార సూచన మాత్రమే. ఈ యాప్ పంట వ్యాధిని నిర్ధారించదు; స్థానిక వ్యవసాయ నిపుణుడి సలహాకు ప్రత్యామ్నాయం కాదు. స్థానిక సూచనలు, ఉత్పత్తి లేబుళ్లను పాటించండి.",
        "image_note": "చిత్ర తనిఖీ పసుపు/గోధుమ రంగు నమూనాలను మాత్రమే చూస్తుంది. వెలుతురు, మట్టి, నేపథ్యం ప్రభావం చూపవచ్చు; వ్యాధిని గుర్తించదు.",
        "image_yellow": "పసుపు లేదా పసుపు-ఆకుపచ్చ భాగాలు కనిపిస్తున్నాయి (నమూనా పిక్సెల్‌లలో {:.1f}%). వెలుతురు, నేపథ్యం ప్రభావం చూపవచ్చు.",
        "image_brown": "గోధుమ రంగు భాగాలు కనిపిస్తున్నాయి (నమూనా పిక్సెల్‌లలో {:.1f}%). ఇవి మట్టి లేదా నేపథ్యం కావచ్చు.",
        "image_none": "సరళమైన రంగు తనిఖీలో స్పష్టమైన పసుపు లేదా గోధుమ నమూనా కనిపించలేదు. సమస్య లేదని దీని అర్థం కాదు.",
        "need_problem": "విశ్లేషణకు ముందు సమస్యను వివరించండి లేదా ఫోటోను అప్‌లోడ్ చేయండి.",
        "image_error": "ఈ చిత్రాన్ని చదవలేకపోయాం. PNG లేదా JPEG ఫోటోను ప్రయత్నించండి.",
        "photo_observations": "ఫోటో పరిశీలనలు (స్థానిక రంగు తనిఖీ)",
        "no_match": "స్పష్టమైన లక్షణ సరిపోలిక లేదు. మట్టి తేమ, నీటి పారుదల, పురుగులు, ఇటీవలి వాతావరణాన్ని పరిశీలించి లక్షణాలు ఎప్పుడు మొదలయ్యాయో గమనించండి.",
        "weather_title": "స్థానిక వాతావరణం, 5 రోజుల అంచనా",
        "place": "భారతదేశంలోని పట్టణం, గ్రామం లేదా జిల్లా",
        "get_weather": "వాతావరణం పొందండి",
        "temperature": "ఉష్ణోగ్రత",
        "humidity": "తేమ",
        "rain_now": "ప్రస్తుత వర్షపాతం",
        "forecast": "రోజువారీ అంచనా",
        "source": "మూలం",
        "weather_error": "వాతావరణ సమాచారం అందలేదు. ఇంటర్నెట్‌ను తనిఖీ చేసి మళ్లీ ప్రయత్నించండి.",
        "place_error": "భారతదేశంలో ఆ ప్రదేశం కనిపించలేదు. సమీప పట్టణం లేదా జిల్లా పేరును ప్రయత్నించండి.",
        "schemes_title": "ప్రభుత్వ పథకాల వివరాలు",
        "central": "కేంద్ర ప్రభుత్వం",
        "state": "ఆంధ్రప్రదేశ్",
        "eligibility": "ఎవరికి అర్హత ఉండవచ్చు",
        "benefit": "సంభావ్య సహాయం",
        "verify": "అర్హత, ప్రస్తుత ప్రయోజనాలు మారవచ్చు. దరఖాస్తుకు ముందు అధికారిక పోర్టల్‌లో నిర్ధారించండి.",
        "open_official": "అధికారిక పోర్టల్ తెరవండి",
        "vault_title": "గుప్తీకరించిన వ్యక్తిగత పత్రాల భద్రపేటిక",
        "vault_note": "మీ పాస్‌ఫ్రేజ్‌తో రూపొందించిన కీ ద్వారా ఈ సర్వర్‌లో పత్రాలు గుప్తీకరించబడతాయి. బలమైన ప్రత్యేక పాస్‌ఫ్రేజ్ వాడి గుర్తుంచుకోండి; తిరిగి పొందలేరు. ఇది స్థానిక ఫైళ్ల భద్రపేటిక మాత్రమే, ధృవీకరించిన క్లౌడ్ నిల్వ కాదు. అవసరం లేకపోతే పూర్తి ఆధార్‌ను అప్‌లోడ్ చేయవద్దు.",
        "account": "భద్రపేటిక పేరు (లాగిన్ ఖాతా కాదు)",
        "passphrase": "భద్రపేటిక పాస్‌ఫ్రేజ్",
        "confirm": "పాస్‌ఫ్రేజ్ నిర్ధారించండి",
        "unlock": "భద్రపేటిక సృష్టించండి / తెరవండి",
        "new_vault": "మొదటి వినియోగం: కనీసం 12 అక్షరాల పాస్‌ఫ్రేజ్‌తో భద్రపేటిక సృష్టించండి.",
        "wrong_pass": "భద్రపేటిక తెరవలేకపోయాం. పాస్‌ఫ్రేజ్ తనిఖీ చేయండి.",
        "pass_mismatch": "పాస్‌ఫ్రేజ్‌లు సరిపోలడం లేదు.",
        "short_pass": "కనీసం 12 అక్షరాల పాస్‌ఫ్రేజ్ వాడండి.",
        "vault_open": "ఈ బ్రౌజర్ సెషన్‌లో భద్రపేటిక తెరిచి ఉంది.",
        "lock": "భద్రపేటిక మూసివేయండి",
        "choose_doc": "గుప్తీకరించి భద్రపరచడానికి పత్రాన్ని ఎంచుకోండి",
        "save_doc": "పత్రాన్ని గుప్తీకరించి భద్రపరచండి",
        "size_error": "ఫైల్ 10 MB పరిమితిని మించింది.",
        "saved": "పత్రం గుప్తీకరించి భద్రపరచబడింది.",
        "stored_docs": "భద్రపరచిన పత్రాలు",
        "empty_vault": "ఇంకా పత్రాలు భద్రపరచలేదు.",
        "download": "డీక్రిప్ట్ చేసిన కాపీని డౌన్‌లోడ్ చేయండి",
        "delete": "తొలగించండి",
        "vault_storage_warning": "గుప్తీకరించిన ఫైళ్లు ఈ కంప్యూటర్ డిస్క్‌లో ఉంటాయి. ఉచిత క్లౌడ్ హోస్టింగ్‌లో రీస్టార్ట్‌కు ఫైళ్లు తొలగిపోవచ్చు. శాశ్వత ప్రైవేట్ నిల్వ, భద్రతా సమీక్ష లేకుండా ఉత్పత్తి వినియోగానికి ఇది సరిపోదు.",
        "vault_public_warning": "నిజమైన ఆధార్ లేదా భూమి పత్రాలను పబ్లిక్ డిప్లాయ్‌మెంట్‌లో అప్‌లోడ్ చేయవద్దు. ఈ హ్యాకథాన్ యాప్‌లో వినియోగదారు లాగిన్ లేదా స్వతంత్ర భద్రతా సమీక్ష లేదు.",
        "tools_title": "రైతులకు ఉపయోగకరమైన సాధనాలు",
        "calendar": "పంట క్యాలెండర్",
        "crop_for_calendar": "పంట",
        "sowing_date": "విత్తే / నాటే తేదీ",
        "create_calendar": "రిమైండర్ క్యాలెండర్ రూపొందించండి",
        "calendar_note": "ఇవి సాధారణ రిమైండర్లు మాత్రమే; పంట-నిర్దిష్ట వ్యవసాయ షెడ్యూల్ కాదు. స్థానిక వ్యవసాయ శాఖతో సమయాలను నిర్ధారించండి.",
        "emergence": "మొలకలను తనిఖీ చేయండి",
        "weed_check": "కలుపు, తేమ, ప్రారంభ పెరుగుదలను తనిఖీ చేయండి",
        "field_check": "మొక్కలు, పురుగులు, మట్టి తేమను పరిశీలించండి",
        "irrigation": "నీటిపారుదల సూచనలు",
        "fertilizer": "ఎరువుల సూచనలు",
        "market_title": "తాజా మండీ ధరలు",
        "commodity": "వస్తువు పేరు (ఆంగ్లంలో)",
        "state_name": "రాష్ట్రం",
        "district": "జిల్లా (ఐచ్ఛికం)",
        "load_prices": "తాజా నివేదిత ధరలను పొందండి",
        "price_key_missing": "లైవ్ మండీ సమాచారం కోసం data.gov.in ఉచిత API కీ అవసరం. DATA_GOV_IN_API_KEYని హోస్టింగ్ ఎన్విరాన్‌మెంట్ లేదా Streamlit secretsలో జోడించండి. కీ లేకుండా ధరలు చూపబడవు.",
        "no_prices": "ఎంపికకు రికార్డులు లేవు. వేరే వస్తువు లేదా జిల్లాను ప్రయత్నించండి.",
        "contacts_title": "వ్యవసాయ సహాయం, అత్యవసర సంప్రదింపులు",
        "kcc": "కిసాన్ కాల్ సెంటర్",
        "kcc_note": "భారతదేశంలో వ్యవసాయ ప్రశ్నల కోసం; భాషా సహాయం అందుబాటును బట్టి ఉంటుంది.",
        "emergency": "అత్యవసర సేవలు",
        "emergency_note": "ప్రాణాలకు తక్షణ ప్రమాదం ఉంటే భారత అత్యవసర నంబర్‌కు కాల్ చేయండి.",
    },
    "hi": {
        "tagline": "खेती की उपयोगी सलाह, औज़ार और भरोसेमंद लिंक।",
        "language": "भाषा",
        "navigation": "नेविगेशन",
        "dashboard": "डैशबोर्ड",
        "crop_help": "फसल समस्या सहायता",
        "weather": "मौसम",
        "schemes": "सरकारी योजनाएँ",
        "vault": "निजी दस्तावेज़ तिजोरी",
        "tools": "किसान के औज़ार",
        "prices": "बाज़ार भाव",
        "contacts": "सहायता / आपातकालीन संपर्क",
        "welcome": "AgriHelp AI में आपका स्वागत है",
        "welcome_text": "नेविगेशन मेनू से कोई औज़ार चुनें। उपलब्ध होने पर मौसम और बाज़ार की जानकारी बताए गए स्रोतों से ली जाती है।",
        "crop": "फसल का नाम",
        "problem": "फसल के लक्षण बताएँ",
        "analyze": "विश्लेषण करें",
        "upload": "फसल की फ़ोटो (वैकल्पिक)",
        "possible": "संभावित कारण — पक्की पहचान नहीं",
        "causes": "संभावित कारण",
        "care": "सामान्य देखभाल",
        "prevention": "बचाव",
        "expert": "कृषि विशेषज्ञ से कब संपर्क करें",
        "disclaimer": "यह केवल सामान्य जानकारी है। ऐप फसल रोग की पुष्टि नहीं कर सकता और स्थानीय कृषि विशेषज्ञ की सलाह का विकल्प नहीं है। स्थानीय सलाह और उत्पाद के लेबल का पालन करें।",
        "image_note": "फ़ोटो जाँच केवल पीले/भूरे रंग के सामान्य पैटर्न देखती है। रोशनी, मिट्टी और पृष्ठभूमि असर डाल सकते हैं; यह रोग की पहचान नहीं करती।",
        "image_yellow": "पीले या पीले-हरे हिस्से दिख रहे हैं (नमूने के {:.1f}% पिक्सेल)। रोशनी और पृष्ठभूमि असर डाल सकते हैं।",
        "image_brown": "भूरे रंग के हिस्से दिख रहे हैं (नमूने के {:.1f}% पिक्सेल)। ये मिट्टी या पृष्ठभूमि भी हो सकते हैं।",
        "image_none": "सरल रंग जाँच में पीला या भूरा पैटर्न स्पष्ट नहीं मिला। इससे फसल की समस्या होने से इनकार नहीं होता।",
        "need_problem": "विश्लेषण से पहले समस्या बताएँ या फ़ोटो अपलोड करें।",
        "image_error": "यह फ़ोटो पढ़ी नहीं जा सकी। PNG या JPEG फ़ोटो आज़माएँ।",
        "photo_observations": "फ़ोटो से संकेत (स्थानीय रंग जाँच)",
        "no_match": "लक्षण का स्पष्ट मिलान नहीं मिला। मिट्टी की नमी, जल निकासी, कीट और हाल का मौसम जाँचें; लक्षण कब शुरू हुए और फैल रहे हैं या नहीं, लिखें।",
        "weather_title": "स्थानीय मौसम और 5-दिन का पूर्वानुमान",
        "place": "भारत का शहर, गाँव या ज़िला",
        "get_weather": "मौसम देखें",
        "temperature": "तापमान",
        "humidity": "नमी",
        "rain_now": "अभी वर्षा",
        "forecast": "दैनिक पूर्वानुमान",
        "source": "स्रोत",
        "weather_error": "मौसम जानकारी नहीं मिली। इंटरनेट जाँचकर फिर प्रयास करें।",
        "place_error": "भारत में यह स्थान नहीं मिला। पास के शहर या ज़िले का नाम आज़माएँ।",
        "schemes_title": "सरकारी योजनाओं की जानकारी",
        "central": "केंद्र सरकार",
        "state": "आंध्र प्रदेश",
        "eligibility": "कौन पात्र हो सकता है",
        "benefit": "संभावित सहायता",
        "verify": "पात्रता और लाभ बदल सकते हैं। आवेदन से पहले आधिकारिक पोर्टल पर जानकारी जाँचें।",
        "open_official": "आधिकारिक पोर्टल खोलें",
        "vault_title": "एन्क्रिप्ट की गई निजी दस्तावेज़ तिजोरी",
        "vault_note": "दस्तावेज़ इस सर्वर पर आपके पासफ़्रेज़ से बनी कुंजी द्वारा एन्क्रिप्ट होते हैं। लंबा, अलग पासफ़्रेज़ रखें और याद रखें—इसे वापस नहीं पाया जा सकता। यह स्थानीय फ़ाइल तिजोरी है, प्रमाणित क्लाउड स्टोरेज नहीं। ज़रूरी न हो तो बिना मास्क किया आधार अपलोड न करें।",
        "account": "तिजोरी का नाम (लॉगिन खाता नहीं)",
        "passphrase": "तिजोरी पासफ़्रेज़",
        "confirm": "पासफ़्रेज़ की पुष्टि करें",
        "unlock": "तिजोरी बनाएँ / खोलें",
        "new_vault": "पहली बार: कम से कम 12 अक्षरों का पासफ़्रेज़ बनाएँ।",
        "wrong_pass": "तिजोरी नहीं खुली। पासफ़्रेज़ जाँचें।",
        "pass_mismatch": "पासफ़्रेज़ मेल नहीं खाते।",
        "short_pass": "कम से कम 12 अक्षरों का पासफ़्रेज़ रखें।",
        "vault_open": "इस ब्राउज़र सत्र में तिजोरी खुली है।",
        "lock": "तिजोरी बंद करें",
        "choose_doc": "एन्क्रिप्ट करके सहेजने के लिए दस्तावेज़ चुनें",
        "save_doc": "दस्तावेज़ एन्क्रिप्ट करके सहेजें",
        "size_error": "फ़ाइल 10 MB की सीमा से बड़ी है।",
        "saved": "दस्तावेज़ एन्क्रिप्ट करके सहेजा गया।",
        "stored_docs": "सहेजे गए दस्तावेज़",
        "empty_vault": "अभी कोई दस्तावेज़ नहीं है।",
        "download": "डिक्रिप्ट की गई प्रति डाउनलोड करें",
        "delete": "हटाएँ",
        "vault_storage_warning": "एन्क्रिप्ट की गई फ़ाइलें इस मशीन की डिस्क पर रहती हैं। मुफ़्त क्लाउड होस्ट की अस्थायी फ़ाइलें रीस्टार्ट पर मिट सकती हैं; स्थायी निजी स्टोरेज और सुरक्षा समीक्षा के बिना यह उत्पादन उपयोग के लिए नहीं है।",
        "vault_public_warning": "वास्तविक आधार या भूमि दस्तावेज़ सार्वजनिक डिप्लॉयमेंट पर अपलोड न करें। इस हैकाथॉन ऐप में उपयोगकर्ता लॉगिन या स्वतंत्र सुरक्षा समीक्षा नहीं है।",
        "tools_title": "किसानों के उपयोगी औज़ार",
        "calendar": "फसल कैलेंडर",
        "crop_for_calendar": "फसल",
        "sowing_date": "बुवाई / रोपाई की तारीख",
        "create_calendar": "रिमाइंडर कैलेंडर बनाएँ",
        "calendar_note": "ये सामान्य रिमाइंडर हैं, फसल-विशिष्ट कृषि समय-सारणी नहीं। स्थानीय कृषि विभाग से समय की पुष्टि करें।",
        "emergence": "अंकुरण जाँचें",
        "weed_check": "खरपतवार, नमी और शुरुआती वृद्धि जाँचें",
        "field_check": "पौधे, कीट और मिट्टी की नमी देखें",
        "irrigation": "सिंचाई सुझाव",
        "fertilizer": "उर्वरक सलाह",
        "market_title": "ताज़ा मंडी भाव",
        "commodity": "फसल / वस्तु का नाम (अंग्रेज़ी में)",
        "state_name": "राज्य",
        "district": "ज़िला (वैकल्पिक)",
        "load_prices": "नवीनतम रिपोर्ट किए भाव लें",
        "price_key_missing": "लाइव मंडी डेटा के लिए data.gov.in की मुफ़्त API कुंजी चाहिए। होस्टिंग वातावरण या Streamlit secrets में DATA_GOV_IN_API_KEY जोड़ें; कुंजी के बिना भाव नहीं दिखेंगे।",
        "no_prices": "इस चयन के लिए रिकॉर्ड नहीं मिले। दूसरी वस्तु या ज़िला आज़माएँ।",
        "contacts_title": "कृषि सहायता और आपातकालीन संपर्क",
        "kcc": "किसान कॉल सेंटर",
        "kcc_note": "भारत में खेती संबंधी प्रश्नों के लिए; भाषा सहायता उपलब्धता पर निर्भर है।",
        "emergency": "आपातकालीन सेवाएँ",
        "emergency_note": "लोगों को तत्काल खतरा हो तो भारत के आपातकालीन नंबर पर कॉल करें।",
    },
}


def tr(key: str) -> str:
    return TEXT[st.session_state.get("language", "en")].get(key, TEXT["en"].get(key, key))


LANG_CODES = {"en": "en", "te": "te", "hi": "hi"}
SYMPTOM_WORDS = {
    "yellow": {
        "en": ("yellow", "pale", "chlorosis"),
        "te": ("పసుపు", "ఆకులు పసుపు", "వాడిపోవడం"),
        "hi": ("पीला", "पत्ते पीले", "पीलापन"),
    },
    "spots": {
        "en": ("spot", "patch", "lesion", "brown", "black"),
        "te": ("మచ్చ", "గోధుమ", "నల్ల మచ్చ"),
        "hi": ("धब्बा", "भूरा", "काला धब्बा"),
    },
    "wilt": {
        "en": ("wilt", "wilting", "droop"),
        "te": ("వాడిపోవడం", "వాలిపోవడం"),
        "hi": ("मुरझाना", "झुकना"),
    },
    "pests": {
        "en": ("insect", "aphid", "bug", "mite", "caterpillar", "pest"),
        "te": ("పురుగు", "కీటకం"),
        "hi": ("कीट", "कीड़ा", "इल्ली"),
    },
    "holes": {
        "en": ("hole", "eaten", "chewed"),
        "te": ("రంధ్రం", "కొరికిన"),
        "hi": ("छेद", "कुतरा", "खाया"),
    },
    "fungus": {
        "en": ("mold", "mildew", "fungus", "fungal", "powdery", "rust"),
        "te": ("బూజు", "ఫంగస్"),
        "hi": ("फफूंदी", "कवक", "रस्ट"),
    },
    "growth": {
        "en": ("stunted", "not growing", "slow growth", "poor growth"),
        "te": ("పెరుగుదల లేదు", "నెమ్మదిగా పెరుగుదల"),
        "hi": ("विकास रुकना", "धीमी बढ़त"),
    },
    "rot": {
        "en": ("rot", "rotting", "rotten", "decay"),
        "te": ("కుళ్ళు", "కుళ్లిపోవడం"),
        "hi": ("सड़ना", "गलना"),
    },
}
GUIDANCE = {
    "yellow": {
        "en": ("Yellowing or pale leaves", "Water stress, nutrient imbalance, pests, or disease may look similar.", "Check soil moisture and leaf undersides. Avoid adding fertilizer without local guidance.", "Use steady, crop-appropriate watering and soil-test-based nutrients."),
        "te": ("ఆకులు పసుపు రంగులోకి మారడం", "నీటి ఒత్తిడి, పోషకాల అసమతుల్యత, పురుగులు లేదా వ్యాధి ఒకేలా కనిపించవచ్చు.", "మట్టి తేమ, ఆకుల వెనుక భాగం చూడండి. స్థానిక సూచన లేకుండా ఎరువు వేయవద్దు.", "పంటకు తగిన నీరు, మట్టి పరీక్ష ఆధారిత పోషకాలు వాడండి."),
        "hi": ("पत्तियों का पीला पड़ना", "पानी का तनाव, पोषक असंतुलन, कीट या रोग एक जैसे दिख सकते हैं।", "मिट्टी की नमी और पत्तियों के नीचे देखें। सलाह बिना उर्वरक न डालें।", "फसल के अनुसार पानी दें और मिट्टी जाँच के आधार पर पोषक दें।"),
    },
    "spots": {
        "en": ("Spots or patches on leaves", "Disease, sun or chemical injury, and nutrient stress can cause similar marks.", "Avoid handling wet plants; remove badly affected fallen leaves if safe.", "Use clean tools, healthy planting material, and suitable plant spacing."),
        "te": ("ఆకులపై మచ్చలు", "వ్యాధి, ఎండ/రసాయన గాయం, పోషక ఒత్తిడి ఒకేలా కనిపించవచ్చు.", "తడి మొక్కలను తాకవద్దు; సురక్షితమైతే తీవ్రంగా ప్రభావితమైన రాలిన ఆకులను తొలగించండి.", "శుభ్రమైన పనిముట్లు, ఆరోగ్యకరమైన నాట్లు, తగిన మొక్కల దూరం పాటించండి."),
        "hi": ("पत्तियों पर धब्बे", "रोग, धूप/रसायन से चोट और पोषक तनाव के निशान मिलते-जुलते हो सकते हैं।", "गीले पौधों को न छुएँ; सुरक्षित हो तो गिरी हुई बहुत प्रभावित पत्तियाँ हटाएँ।", "साफ औज़ार, स्वस्थ रोपण सामग्री और उचित दूरी रखें।"),
    },
    "wilt": {
        "en": ("Wilting or drooping plants", "Dry soil, waterlogged roots, heat, or disease may cause wilting.", "Check soil near the roots before watering; improve drainage if saturated.", "Maintain appropriate watering and avoid root injury."),
        "te": ("మొక్కలు వాడిపోవడం లేదా వాలిపోవడం", "ఎండిన మట్టి, నీరు నిలవడం, వేడి లేదా వ్యాధి కారణం కావచ్చు.", "నీరు పెట్టే ముందు వేర్ల దగ్గర మట్టి చూడండి; నీరు నిలిస్తే పారుదల మెరుగుపరచండి.", "తగిన నీరు ఇవ్వండి; వేర్లకు గాయం కాకుండా చూడండి."),
        "hi": ("पौधों का मुरझाना या झुकना", "सूखी मिट्टी, जलभराव, गर्मी या रोग इसका कारण हो सकते हैं।", "पानी देने से पहले जड़ों के पास मिट्टी देखें; जलभराव हो तो निकासी सुधारें।", "उचित सिंचाई करें और जड़ों को चोट से बचाएँ।"),
    },
    "pests": {
        "en": ("Possible insect or mite activity", "Feeding insects may be present, but text or color alone cannot identify the pest.", "Inspect leaf undersides and new growth; identify the pest before choosing a control.", "Monitor plants regularly and use locally approved pest management."),
        "te": ("పురుగులు లేదా మైట్ల ఉండే అవకాశం", "పురుగులు ఉండవచ్చు; వచనం లేదా రంగు మాత్రమే వాటిని గుర్తించలేవు.", "ఆకుల వెనుక, కొత్త పెరుగుదల చూడండి; నియంత్రణకు ముందు పురుగును గుర్తించండి.", "మొక్కలను తరచూ పరిశీలించి స్థానికంగా ఆమోదించిన నియంత్రణ వాడండి."),
        "hi": ("कीट या माइट की संभावना", "कीट हो सकते हैं, पर केवल पाठ या रंग से उनकी पहचान नहीं होती।", "पत्तियों के नीचे और नई बढ़त देखें; नियंत्रण चुनने से पहले कीट पहचानें।", "पौधों की नियमित जाँच करें और स्थानीय रूप से स्वीकृत उपाय अपनाएँ।"),
    },
    "holes": {
        "en": ("Holes or chewed leaf edges", "Caterpillars, insects, or other animals may be feeding on leaves.", "Inspect plants at different times for fresh damage, eggs, or larvae.", "Monitor regularly and use locally recommended barriers or controls."),
        "te": ("ఆకుల్లో రంధ్రాలు లేదా కొరికిన అంచులు", "గొంగళి పురుగులు, ఇతర కీటకాలు లేదా జంతువులు ఆకులను తింటుండవచ్చు.", "తాజా నష్టం, గుడ్లు లేదా లార్వాల కోసం వేర్వేరు సమయాల్లో చూడండి.", "తరచూ పరిశీలించి స్థానికంగా సిఫార్సు చేసిన అడ్డుకట్టలు వాడండి."),
        "hi": ("पत्तियों में छेद या कुतरे किनारे", "इल्ली, कीट या अन्य जीव पत्तियाँ खा सकते हैं।", "नए नुकसान, अंडों या लार्वा के लिए अलग-अलग समय पर जाँचें।", "नियमित निगरानी करें और स्थानीय रूप से सुझाए उपाय अपनाएँ।"),
    },
    "fungus": {
        "en": ("Possible mildew or fungal growth", "Fungal disease, dust, and spray residue can look alike.", "Improve airflow and avoid wetting leaves where practical; ask an expert before treatment.", "Use healthy planting material, clean tools, and suitable spacing."),
        "te": ("బూజు లేదా ఫంగస్ పెరుగుదల ఉండవచ్చు", "ఫంగస్ వ్యాధి, దుమ్ము, పిచికారీ అవశేషాలు ఒకేలా కనిపించవచ్చు.", "వీలైతే గాలి ప్రసరణ మెరుగుపరచి ఆకులు తడవకుండా చూడండి; మందుకు ముందు నిపుణుడిని అడగండి.", "ఆరోగ్యకరమైన నాట్లు, శుభ్రమైన పనిముట్లు, తగిన దూరం వాడండి."),
        "hi": ("फफूंदी या कवक की संभावना", "कवक रोग, धूल और छिड़काव के अवशेष एक जैसे दिख सकते हैं।", "हवा का आवागमन रखें और पत्तियाँ भिगोने से बचें; दवा से पहले विशेषज्ञ से पूछें।", "स्वस्थ रोपण सामग्री, साफ औज़ार और उचित दूरी रखें।"),
    },
    "growth": {
        "en": ("Slow or stunted growth", "Soil moisture, nutrients, roots, weather, pests, or disease may be involved.", "Compare healthy and affected plants; check drainage and roots before fertilizing.", "Use soil testing and locally recommended planting practices."),
        "te": ("పెరుగుదల నెమ్మదిగా లేదా ఆగిపోవడం", "మట్టి తేమ, పోషకాలు, వేర్లు, వాతావరణం, పురుగులు లేదా వ్యాధి కారణం కావచ్చు.", "ఆరోగ్యకరమైన మొక్కలతో పోల్చి చూడండి; ఎరువుకు ముందు నీటి పారుదల, వేర్లు చూడండి.", "మట్టి పరీక్ష, స్థానికంగా సిఫార్సు చేసిన సాగు పద్ధతులు పాటించండి."),
        "hi": ("धीमी या रुकी हुई बढ़त", "मिट्टी की नमी, पोषक, जड़ें, मौसम, कीट या रोग कारण हो सकते हैं।", "स्वस्थ पौधों से तुलना करें; खाद से पहले निकासी और जड़ें जाँचें।", "मिट्टी की जाँच और स्थानीय खेती की सलाह अपनाएँ।"),
    },
    "rot": {
        "en": ("Rot or decay", "Disease, excess moisture, or crop damage may be involved.", "Check drainage, handle produce gently, and ask for local advice before treatment.", "Maintain drainage and remove crop waste appropriately."),
        "te": ("కుళ్ళు లేదా పంట చెడిపోవడం", "వ్యాధి, అధిక తేమ లేదా పంటకు గాయం కారణం కావచ్చు.", "పారుదల చూడండి, పంటను జాగ్రత్తగా చేతబట్టండి; మందుకు ముందు స్థానిక సలహా తీసుకోండి.", "పారుదల మెరుగుపరచి పంట అవశేషాలను సక్రమంగా తొలగించండి."),
        "hi": ("सड़न या गलन", "रोग, अधिक नमी या फसल को चोट कारण हो सकते हैं।", "निकासी देखें, उपज सावधानी से रखें और उपचार से पहले स्थानीय सलाह लें।", "निकासी रखें और फसल अवशेष सही तरीके से हटाएँ।"),
    },
}


def inspect_image(image_data: bytes, language: str) -> tuple[list[str], list[str]]:
    with Image.open(BytesIO(image_data)) as image:
        image.thumbnail((320, 320))
        pixels = list(image.convert("RGB").getdata())

    yellow = sum(
        red >= 95 and green >= 80 and green >= blue * 1.25 and red >= green * 0.92
        for red, green, blue in pixels
    )
    brown = sum(
        red >= 55 and red >= green * 1.15 and green >= blue * 1.1 and red < 200
        for red, green, blue in pixels
    )
    total = len(pixels)
    observations = []
    symptoms = []
    if yellow / total * 100 >= 4:
        observations.append(TEXT[language]["image_yellow"].format(yellow / total * 100))
        symptoms.append("yellow")
    if brown / total * 100 >= 4:
        observations.append(TEXT[language]["image_brown"].format(brown / total * 100))
        symptoms.append("spots")
    if not observations:
        observations.append(TEXT[language]["image_none"])
    return observations, symptoms


@st.cache_data(ttl=900, show_spinner=False)
def lookup_locations(place: str) -> list[dict]:
    response = requests.get(
        "https://geocoding-api.open-meteo.com/v1/search",
        params={"name": place, "count": 10, "language": "en", "format": "json"},
        timeout=15,
    )
    response.raise_for_status()
    data = response.json()
    return [item for item in data.get("results", []) if item.get("country_code") == "IN"]


@st.cache_data(ttl=900, show_spinner=False)
def fetch_weather(latitude: float, longitude: float) -> dict:
    response = requests.get(
        "https://api.open-meteo.com/v1/forecast",
        params={
            "latitude": latitude,
            "longitude": longitude,
            "current": "temperature_2m,relative_humidity_2m,precipitation",
            "daily": "temperature_2m_max,precipitation_sum",
            "forecast_days": 5,
            "timezone": "auto",
        },
        timeout=20,
    )
    response.raise_for_status()
    return response.json()


@st.cache_data(ttl=3600, show_spinner=False)
def make_speech(text: str, language: str) -> bytes:
    audio = BytesIO()
    gTTS(text=text, lang=LANG_CODES[language]).write_to_fp(audio)
    return audio.getvalue()


def get_data_gov_key() -> str:
    key = os.getenv("DATA_GOV_IN_API_KEY", "")
    if key:
        return key
    try:
        return str(st.secrets.get("DATA_GOV_IN_API_KEY", ""))
    except StreamlitSecretNotFoundError:
        return ""


def fetch_mandi_prices(api_key: str, commodity: str, state: str, district: str) -> list[dict]:
    params = {
        "api-key": api_key,
        "format": "json",
        "limit": 30,
        "filters[commodity]": commodity,
        "filters[state]": state,
    }
    if district.strip():
        params["filters[district]"] = district.strip()
    response = requests.get(
        "https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070",
        params=params,
        timeout=20,
    )
    response.raise_for_status()
    return response.json().get("records", [])


def derive_vault_key(passphrase: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=600_000)
    return kdf.derive(passphrase.encode("utf-8"))


def encrypt_bytes(key: bytes, plaintext: bytes, associated_data: bytes) -> bytes:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    nonce = os.urandom(12)
    return nonce + AESGCM(key).encrypt(nonce, plaintext, associated_data)


def decrypt_bytes(key: bytes, encrypted: bytes, associated_data: bytes) -> bytes:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    return AESGCM(key).decrypt(encrypted[:12], encrypted[12:], associated_data)


def vault_directory(owner: str) -> Path:
    root = Path(
        os.getenv("AGRIHELP_VAULT_DIR", str(Path.home() / ".agrihelp_ai" / "vault"))
    )
    return root / owner


def navigate_to(page_id: str) -> None:
    st.session_state["current_page"] = page_id


def render_dashboard() -> None:
    st.title("🌱 " + tr("welcome"))
    st.caption(tr("tagline"))
    st.write(tr("welcome_text"))
    pages = [
        ("crop_help", "🩺"),
        ("weather", "🌦️"),
        ("schemes", "🏛️"),
        ("vault", "🔐"),
        ("tools", "🗓️"),
        ("prices", "📈"),
    ]
    for row in range(0, len(pages), 3):
        cols = st.columns(3)
        for col, (key, icon) in zip(cols, pages[row : row + 3]):
            with col:
                st.button(
                    f"{icon}  {tr(key)}",
                    key=f"dashboard_{key}",
                    on_click=navigate_to,
                    args=(key,),
                    use_container_width=True,
                )
    st.info(tr("disclaimer"))


def render_crop_help(language: str) -> None:
    st.title("🩺 " + tr("crop_help"))
    pending_transcript = st.session_state.pop("pending_crop_transcript", None)
    if pending_transcript is not None:
        st.session_state["crop_problem"] = pending_transcript
    crop = st.text_input(tr("crop"), key="crop_name", placeholder="Tomato / టమాటా / टमाटर")
    problem = st.text_area(tr("problem"), key="crop_problem", height=110)
    uploaded = st.file_uploader(
        tr("upload"),
        type=["png", "jpg", "jpeg", "webp"],
        help=tr("image_note"),
        key="crop_photo",
    )
    if uploaded is not None:
        st.image(uploaded, caption=tr("upload"), use_container_width=True)

    audio = st.audio_input("🎙️ " + tr("problem"))
    if audio is not None:
        if st.button("Transcribe voice", key="transcribe_voice"):
            try:
                recognizer = sr.Recognizer()
                with sr.AudioFile(BytesIO(audio.getvalue())) as source:
                    recorded_audio = recognizer.record(source)
                with st.spinner("Transcribing voice…"):
                    transcript = recognizer.recognize_google(
                        recorded_audio, language={"en": "en-IN", "te": "te-IN", "hi": "hi-IN"}[language]
                    )
                st.session_state["pending_crop_transcript"] = transcript
                st.rerun()
            except sr.UnknownValueError:
                st.warning("The recording was not clear enough to transcribe. Try again or type the symptoms.")
            except sr.RequestError as exc:
                st.error(f"Speech recognition service is unavailable: {exc}")
            except (OSError, ValueError) as exc:
                st.error(f"Could not read the recording: {exc}")
    st.caption(
        "Voice input sends the recording to Google's online speech-recognition service; "
        "reading advice aloud sends text to Google's text-to-speech service. Both need "
        "internet and may not work in every browser or language. Do not include sensitive details."
    )

    if st.button(tr("analyze"), type="primary", use_container_width=True):
        if not problem.strip() and uploaded is None:
            st.warning(tr("need_problem"))
            st.session_state.pop("crop_advice", None)
        else:
            image_observations = []
            image_symptoms = []
            if uploaded is not None:
                try:
                    image_observations, image_symptoms = inspect_image(
                        uploaded.getvalue(), language
                    )
                except (UnidentifiedImageError, OSError):
                    st.error(tr("image_error"))
                    st.session_state.pop("crop_advice", None)
                    return

            text = problem.casefold()
            matched = []
            for category, translations in GUIDANCE.items():
                words = SYMPTOM_WORDS[category][language]
                if category in image_symptoms or any(word in text for word in words):
                    matched.append(translations[language])
            st.session_state["crop_advice"] = {
                "crop": crop.strip() or tr("crop"),
                "observations": image_observations,
                "matched": matched,
                "text": text,
                "language": language,
            }

    result = st.session_state.get("crop_advice")
    if result and result["language"] == language:
        st.divider()
        st.subheader(f'{result["crop"]} — {tr("possible")}')
        if result["observations"]:
            st.markdown("**" + tr("photo_observations") + "**")
            st.caption(tr("image_note"))
            for note in result["observations"]:
                st.write("• " + note)
        st.warning(tr("possible"))
        speak_lines = [tr("possible")]
        for title, cause, care, prevention in result["matched"]:
            st.markdown("### " + title)
            st.markdown("**" + tr("causes") + ":** " + cause)
            st.markdown("**" + tr("care") + ":** " + care)
            st.markdown("**" + tr("prevention") + ":** " + prevention)
            speak_lines.extend([title, cause, care, prevention])
        if not result["matched"]:
            st.info(tr("no_match"))
            speak_lines.append(tr("no_match"))
        expert = {
            "en": "Contact a local agriculture expert if symptoms spread quickly, affect many plants, or cause major crop loss. Share clear photos and recent care details.",
            "te": "లక్షణాలు వేగంగా వ్యాపిస్తే, అనేక మొక్కలను ప్రభావితం చేస్తే లేదా పంట నష్టం ఎక్కువైతే స్థానిక వ్యవసాయ నిపుణుడిని సంప్రదించండి. ఫోటోలు, ఇటీవలి సంరక్షణ వివరాలు పంచుకోండి.",
            "hi": "लक्षण तेजी से फैलें, कई पौधे प्रभावित हों या फसल का बड़ा नुकसान हो तो स्थानीय कृषि विशेषज्ञ से संपर्क करें। साफ़ फ़ोटो और हाल की देखभाल की जानकारी दें।",
        }[language]
        st.markdown("**" + tr("expert") + ":** " + expert)
        speak_lines.append(expert)
        if st.button("🔊 " + ("Read advice aloud" if language == "en" else "సలహాను వినండి" if language == "te" else "सलाह सुनें"), key="speak_advice"):
            try:
                with st.spinner("Preparing audio…"):
                    audio_bytes = make_speech(" ".join(speak_lines), language)
                st.audio(audio_bytes, format="audio/mp3")
            except (gTTSError, AssertionError, OSError, ValueError) as exc:
                st.error(f"Could not generate speech. Check your internet connection. Details: {exc}")
        st.info(tr("disclaimer"))


def render_weather() -> None:
    st.title("🌦️ " + tr("weather_title"))
    place = st.text_input(tr("place"), value="Guntur")
    if st.button(tr("get_weather"), type="primary"):
        try:
            with st.spinner("Looking up the location and forecast…"):
                locations = lookup_locations(place.strip())
                if not locations:
                    st.warning(tr("place_error"))
                    return
                location = locations[0]
                weather = fetch_weather(location["latitude"], location["longitude"])
            st.subheader(", ".join(filter(None, [location.get("name"), location.get("admin1"), location.get("country")])))
            current = weather.get("current", {})
            units = weather.get("current_units", {})
            cols = st.columns(3)
            cols[0].metric(tr("temperature"), f'{current.get("temperature_2m", "—")} {units.get("temperature_2m", "°C")}')
            cols[1].metric(tr("humidity"), f'{current.get("relative_humidity_2m", "—")} {units.get("relative_humidity_2m", "%")}')
            cols[2].metric(tr("rain_now"), f'{current.get("precipitation", "—")} {units.get("precipitation", "mm")}')
            st.subheader(tr("forecast"))
            daily = weather.get("daily", {})
            daily_units = weather.get("daily_units", {})
            rows = [
                {
                    "Date": day,
                    "Max temperature": f"{high} {daily_units.get('temperature_2m_max', '°C')}",
                    "Precipitation": f"{rain} {daily_units.get('precipitation_sum', 'mm')}",
                }
                for day, high, rain in zip(
                    daily.get("time", []),
                    daily.get("temperature_2m_max", []),
                    daily.get("precipitation_sum", []),
                )
            ]
            st.dataframe(rows, use_container_width=True, hide_index=True)
            st.caption(f'{tr("source")}: Open-Meteo · {weather.get("timezone", "")}')
            st.caption("Forecasts are model estimates and may differ from local conditions.")
        except requests.RequestException as exc:
            st.error(f'{tr("weather_error")} ({exc})')
        except (KeyError, TypeError, ValueError) as exc:
            st.error(f'{tr("weather_error")} ({exc})')


SCHEMES = {
    "central": [
        {
            "name": "PM-KISAN",
            "eligible": {
                "en": "Potentially eligible landholding farmer families, subject to scheme exclusions and verification.",
                "te": "పథకం మినహాయింపులు, ధృవీకరణకు లోబడి భూమి కలిగిన రైతు కుటుంబాలు అర్హులు కావచ్చు.",
                "hi": "योजना की अपात्रता शर्तों और सत्यापन के अधीन भूमि रखने वाले किसान परिवार पात्र हो सकते हैं।",
            },
            "benefit": {
                "en": "Income support as specified by current scheme rules; verify current installment and status on the official portal.",
                "te": "ప్రస్తుత పథక నియమాల ప్రకారం ఆదాయ సహాయం; తాజా విడత, స్థితిని అధికారిక పోర్టల్‌లో తనిఖీ చేయండి.",
                "hi": "मौजूदा योजना नियमों के अनुसार आय सहायता; वर्तमान किस्त और स्थिति आधिकारिक पोर्टल पर जाँचें।",
            },
            "url": "https://pmkisan.gov.in/",
        },
        {
            "name": "Pradhan Mantri Fasal Bima Yojana (PMFBY)",
            "eligible": {
                "en": "Farmers growing notified crops in notified areas, subject to current enrollment rules and deadlines.",
                "te": "ప్రకటించిన ప్రాంతాల్లో ప్రకటించిన పంటలు సాగు చేసే రైతులు; ప్రస్తుత నమోదు నియమాలు, గడువులు వర్తిస్తాయి.",
                "hi": "अधिसूचित क्षेत्रों में अधिसूचित फसल उगाने वाले किसान; मौजूदा नामांकन नियम और समय-सीमा लागू।",
            },
            "benefit": {
                "en": "Crop insurance for covered risks under scheme rules; coverage, premium, and claim rules vary.",
                "te": "పథక నియమాల ప్రకారం కవర్ చేసిన ప్రమాదాలకు పంట బీమా; కవరేజ్, ప్రీమియం, క్లెయిమ్ నియమాలు మారవచ్చు.",
                "hi": "योजना के तहत शामिल जोखिमों के लिए फसल बीमा; कवरेज, प्रीमियम और दावा नियम अलग हो सकते हैं।",
            },
            "url": "https://pmfby.gov.in/",
        },
        {
            "name": "Kisan Credit Card (KCC)",
            "eligible": {
                "en": "Eligible farmers and other approved agricultural borrowers; the lending bank determines eligibility.",
                "te": "అర్హులైన రైతులు, ఆమోదించిన ఇతర వ్యవసాయ రుణగ్రహీతలు; అర్హతను రుణదాత బ్యాంకు నిర్ణయిస్తుంది.",
                "hi": "पात्र किसान और अन्य स्वीकृत कृषि उधारकर्ता; पात्रता ऋणदाता बैंक तय करता है।",
            },
            "benefit": {
                "en": "Access to approved agricultural credit; interest and credit terms depend on current rules and lender.",
                "te": "ఆమోదిత వ్యవసాయ రుణానికి అవకాశం; వడ్డీ, షరతులు ప్రస్తుత నియమాలు, రుణదాతపై ఆధారపడతాయి.",
                "hi": "स्वीकृत कृषि ऋण तक पहुँच; ब्याज और शर्तें मौजूदा नियमों और ऋणदाता पर निर्भर हैं।",
            },
            "url": "https://pmkisan.gov.in/KCC.aspx",
        },
    ],
    "state": [
        {
            "name": "Annadata Sukhibhava",
            "eligible": {
                "en": "Andhra Pradesh farmers who satisfy the current state scheme conditions and verification.",
                "te": "ప్రస్తుత రాష్ట్ర పథక షరతులు, ధృవీకరణకు అర్హత సాధించిన ఆంధ్రప్రదేశ్ రైతులు.",
                "hi": "मौजूदा राज्य योजना की शर्तें और सत्यापन पूरा करने वाले आंध्र प्रदेश के किसान।",
            },
            "benefit": {
                "en": "State farmer support as published under current rules. Confirm amounts, installments, and enrollment status at the official portal.",
                "te": "ప్రస్తుత నియమాల ప్రకారం రాష్ట్ర రైతు సహాయం. మొత్తం, విడతలు, నమోదును అధికారిక పోర్టల్‌లో నిర్ధారించండి.",
                "hi": "मौजूदा नियमों के अनुसार राज्य किसान सहायता। राशि, किस्तें और नामांकन आधिकारिक पोर्टल पर जाँचें।",
            },
            "url": "https://annadathasukhibhava.ap.gov.in/",
        },
        {
            "name": "Andhra Pradesh Agriculture Department",
            "eligible": {
                "en": "Eligibility depends on the specific current state program and local notifications.",
                "te": "ప్రత్యేక రాష్ట్ర కార్యక్రమం, స్థానిక ప్రకటనలపై అర్హత ఆధారపడి ఉంటుంది.",
                "hi": "पात्रता संबंधित राज्य कार्यक्रम और स्थानीय अधिसूचनाओं पर निर्भर करती है।",
            },
            "benefit": {
                "en": "Official department information on active agriculture programs, services, and announcements.",
                "te": "అమల్లో ఉన్న వ్యవసాయ కార్యక్రమాలు, సేవలు, ప్రకటనలపై శాఖ అధికారిక సమాచారం.",
                "hi": "चालू कृषि कार्यक्रमों, सेवाओं और घोषणाओं की विभागीय आधिकारिक जानकारी।",
            },
            "url": "https://apagrisnet.gov.in/",
        },
    ],
}


def render_schemes() -> None:
    st.title("🏛️ " + tr("schemes_title"))
    for section, heading in [("central", tr("central")), ("state", tr("state"))]:
        st.header(heading)
        cards = st.columns(2)
        for index, scheme in enumerate(SCHEMES[section]):
            with cards[index % 2]:
                with st.container(border=True):
                    st.subheader(scheme["name"])
                    st.markdown(f'**{tr("eligibility")}:** {scheme["eligible"][st.session_state.language]}')
                    st.markdown(f'**{tr("benefit")}:** {scheme["benefit"][st.session_state.language]}')
                    st.link_button(tr("open_official"), scheme["url"], use_container_width=True)
    st.warning(tr("verify"))
    st.caption(f'{tr("source")}: Official scheme portals linked above; information checked 16 October 2026.')


def render_vault() -> None:
    st.title("🔐 " + tr("vault_title"))
    st.info(tr("vault_note"))
    st.warning(tr("vault_storage_warning"))
    st.error(tr("vault_public_warning"))
    st.caption(
        "Vault files are encrypted before being written to disk using AES-GCM. "
        "Account names only separate storage; they are not user authentication. "
        "The passphrase is never saved. HTTPS is required when deployed online."
    )
    owner_name = st.text_input(tr("account"), key="vault_name").strip().casefold()
    if len(owner_name) < 3:
        st.caption("Use at least 3 characters for the vault name.")
        return
    owner = hashlib.sha256(owner_name.encode("utf-8")).hexdigest()
    folder = vault_directory(owner)
    salt_path = folder / "salt.bin"
    verifier_path = folder / "verifier.bin"
    unlocked = (
        st.session_state.get("vault_owner") == owner
        and isinstance(st.session_state.get("vault_key"), bytes)
    )

    if not unlocked:
        if salt_path.exists():
            st.caption("Enter your existing passphrase to unlock.")
        else:
            st.caption(tr("new_vault"))
        with st.form("vault_unlock_form", clear_on_submit=True):
            passphrase = st.text_input(tr("passphrase"), type="password")
            confirmation = ""
            if not salt_path.exists():
                confirmation = st.text_input(tr("confirm"), type="password")
            submitted = st.form_submit_button(tr("unlock"), type="primary")
        if submitted:
            if len(passphrase) < 12:
                st.error(tr("short_pass"))
                return
            if not salt_path.exists() and passphrase != confirmation:
                st.error(tr("pass_mismatch"))
                return
            try:
                folder.mkdir(parents=True, exist_ok=True, mode=0o700)
                if salt_path.exists():
                    salt = salt_path.read_bytes()
                    key = derive_vault_key(passphrase, salt)
                    decrypt_bytes(key, verifier_path.read_bytes(), b"vault-verifier")
                else:
                    salt = os.urandom(16)
                    key = derive_vault_key(passphrase, salt)
                    salt_path.write_bytes(salt)
                    verifier_path.write_bytes(
                        encrypt_bytes(key, b"AgriHelp private vault", b"vault-verifier")
                    )
                st.session_state["vault_owner"] = owner
                st.session_state["vault_key"] = key
                st.rerun()
            except InvalidTag:
                st.error(tr("wrong_pass"))
            except OSError as exc:
                st.error(f"Could not access private vault storage: {exc}")
        return

    key = st.session_state["vault_key"]
    st.success(tr("vault_open"))
    if st.button(tr("lock"), key="lock_vault"):
        st.session_state.pop("vault_key", None)
        st.session_state.pop("vault_owner", None)
        st.rerun()
    document = st.file_uploader(
        tr("choose_doc"),
        type=["pdf", "png", "jpg", "jpeg", "webp", "doc", "docx"],
        key="vault_document",
    )
    if st.button(tr("save_doc"), disabled=document is None, key="save_vault_doc"):
        if document is not None:
            raw = document.getvalue()
            if len(raw) > 10 * 1024 * 1024:
                st.error(tr("size_error"))
            else:
                safe_name = Path(document.name.replace("\\", "/")).name
                payload = json.dumps(
                    {
                        "name": safe_name,
                        "content": base64.b64encode(raw).decode("ascii"),
                    }
                ).encode("utf-8")
                target = folder / f"{uuid.uuid4().hex}.vault"
                try:
                    target.write_bytes(encrypt_bytes(key, payload, owner.encode("ascii")))
                    st.success(tr("saved"))
                except OSError as exc:
                    st.error(f"Could not save encrypted document: {exc}")

    st.subheader(tr("stored_docs"))
    stored = sorted(folder.glob("*.vault"))
    if not stored:
        st.caption(tr("empty_vault"))
    for path in stored:
        try:
            saved = json.loads(
                decrypt_bytes(key, path.read_bytes(), owner.encode("ascii")).decode("utf-8")
            )
            raw = base64.b64decode(saved["content"], validate=True)
        except (InvalidTag, OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
            st.error(f"Could not read encrypted document {path.name}: {exc}")
            continue
        left, middle, right = st.columns([3, 2, 1])
        left.write(f'📄 {saved["name"]}')
        middle.download_button(
            tr("download"),
            raw,
            file_name=saved["name"],
            key=f"download_{path.stem}",
        )
        if right.button(tr("delete"), key=f"delete_{path.stem}"):
            try:
                path.unlink()
                st.rerun()
            except OSError as exc:
                st.error(f"Could not delete document: {exc}")


def render_tools() -> None:
    st.title("🧰 " + tr("tools_title"))
    calendar_tab, irrigation_tab, fertilizer_tab = st.tabs(
        [tr("calendar"), tr("irrigation"), tr("fertilizer")]
    )
    with calendar_tab:
        st.subheader(tr("calendar"))
        crop = st.text_input(tr("crop_for_calendar"))
        planted = st.date_input(tr("sowing_date"), value=date.today())
        if st.button(tr("create_calendar"), key="make_calendar"):
            st.write(f"**{crop or tr('crop_for_calendar')}**")
            reminders = [
                (0, tr("sowing_date")),
                (7, tr("emergence")),
                (21, tr("weed_check")),
                (35, tr("field_check")),
            ]
            for days, label in reminders:
                st.write(f"- {planted + timedelta(days=days):%d %b %Y}: {label}")
            st.caption(tr("calendar_note"))
    with irrigation_tab:
        st.subheader(tr("irrigation"))
        irrigation_text = {
            "en": "Check moisture near the root zone before watering. Account for recent rain, soil type, crop stage, drainage, and local forecasts. Prefer watering when evaporation is lower where practical; avoid both waterlogging and crop stress. These are general tips, not a crop-specific schedule.",
            "te": "నీరు పెట్టే ముందు వేర్ల దగ్గర తేమ చూడండి. ఇటీవలి వర్షం, మట్టి రకం, పంట దశ, పారుదల, స్థానిక అంచనాలను పరిగణనలోకి తీసుకోండి. సాధ్యమైనప్పుడు ఆవిరి తక్కువగా ఉండే సమయంలో నీరు పెట్టండి; నీరు నిలవడం, పంట ఒత్తిడి రెండింటినీ నివారించండి. ఇవి సాధారణ సూచనలు మాత్రమే.",
            "hi": "सिंचाई से पहले जड़ों के पास नमी जाँचें। हाल की बारिश, मिट्टी, फसल की अवस्था, जल निकासी और स्थानीय पूर्वानुमान देखें। जहाँ संभव हो कम वाष्पीकरण के समय पानी दें; जलभराव और फसल तनाव दोनों से बचें। ये सामान्य सुझाव हैं, फसल-विशिष्ट समय-सारणी नहीं।",
        }
        st.write(irrigation_text[st.session_state.language])
    with fertilizer_tab:
        st.subheader(tr("fertilizer"))
        fertilizer_text = {
            "en": "Base fertilizer decisions on a soil test, crop, growth stage, and local agricultural recommendations. Do not guess a dose or mix products. Follow the label, use protective equipment, and keep fertilizer away from wells and waterways. Ask an extension officer if unsure.",
            "te": "మట్టి పరీక్ష, పంట, పెరుగుదల దశ, స్థానిక వ్యవసాయ సిఫార్సుల ఆధారంగా ఎరువు నిర్ణయించండి. మోతాదును ఊహించవద్దు, ఉత్పత్తులను కలపవద్దు. లేబుల్ పాటించి రక్షణ పరికరాలు వాడండి; బావులు, నీటి మార్గాల నుంచి దూరంగా ఉంచండి. సందేహమైతే వ్యవసాయ అధికారిని అడగండి.",
            "hi": "मिट्टी जाँच, फसल, बढ़त की अवस्था और स्थानीय कृषि सलाह के आधार पर उर्वरक चुनें। मात्रा का अनुमान न लगाएँ और उत्पाद न मिलाएँ। लेबल का पालन करें, सुरक्षा उपकरण पहनें और खाद को कुओं/जलस्रोतों से दूर रखें। संदेह हो तो कृषि अधिकारी से पूछें।",
        }
        st.write(fertilizer_text[st.session_state.language])


def render_prices() -> None:
    st.title("📈 " + tr("market_title"))
    st.caption(
        "Live reported mandi records from data.gov.in (Ministry of Agriculture & Farmers Welfare). "
        "Prices are not predictions; check the report date and local market before selling."
    )
    commodity = st.text_input(tr("commodity"), value="Tomato")
    state = st.text_input(tr("state_name"), value="Andhra Pradesh")
    district = st.text_input(tr("district"))
    if st.button(tr("load_prices"), type="primary"):
        api_key = get_data_gov_key()
        if not api_key:
            st.warning(tr("price_key_missing"))
        else:
            try:
                with st.spinner("Fetching reported market records…"):
                    records = fetch_mandi_prices(api_key, commodity, state, district)
                if records:
                    fields = [
                        "state", "district", "market", "commodity", "variety",
                        "arrival_date", "min_price", "max_price", "modal_price",
                    ]
                    rows = [{field: row.get(field, "") for field in fields if field in row} for row in records]
                    st.dataframe(rows, use_container_width=True, hide_index=True)
                    st.caption(f'{tr("source")}: data.gov.in · Report date appears in each record.')
                else:
                    st.info(tr("no_prices"))
            except requests.RequestException as exc:
                st.error(f"Market data could not be loaded: {exc}")
            except (ValueError, TypeError) as exc:
                st.error(f"Market data response was not valid: {exc}")
    st.link_button(
        "Open Agmarknet official portal",
        "https://agmarknet.gov.in/",
    )
    st.caption(
        "For API access, create a free account at data.gov.in, subscribe to the "
        "current daily mandi prices dataset, and configure DATA_GOV_IN_API_KEY as a secret."
    )


def render_contacts() -> None:
    st.title("☎️ " + tr("contacts_title"))
    st.subheader(tr("kcc"))
    st.markdown("**1800-180-1551**")
    st.write(tr("kcc_note"))
    st.link_button(
        "Kisan Call Centre official information",
        "https://mkisan.gov.in/Home/KCCDashboard",
    )
    st.divider()
    st.subheader(tr("emergency"))
    st.markdown("**112**")
    st.write(tr("emergency_note"))
    st.link_button(
        "Government of India emergency response support system",
        "https://112.gov.in/",
    )


with st.sidebar:
    st.markdown("## 🌱 AgriHelp AI")
    st.caption(
        'Background: [Ashikul Islam Anik](https://commons.wikimedia.org/wiki/File:Farmer_Working_in_Field_at_Dawn_Meherpur_3.jpg), '
        '[CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/) · cropped and optimized.'
    )
    language_label = st.selectbox(
        "Language / భాష / भाषा",
        list(LANGUAGES),
        index=0,
        key="language_selector",
    )
    selected_language = LANGUAGES[language_label]
    st.session_state["language"] = selected_language
    page_ids = [
        "dashboard", "crop_help", "weather", "schemes",
        "vault", "tools", "prices", "contacts",
    ]
    st.session_state.setdefault("current_page", "dashboard")
    st.markdown(f"**{tr('navigation')}**")
    page_icons = {
        "dashboard": "🏠",
        "crop_help": "🩺",
        "weather": "🌦️",
        "schemes": "🏛️",
        "vault": "🔐",
        "tools": "🗓️",
        "prices": "📈",
        "contacts": "☎️",
    }
    for page_id in page_ids:
        active_marker = "✓ " if st.session_state["current_page"] == page_id else ""
        st.button(
            f"{active_marker}{page_icons[page_id]}  {tr(page_id)}",
            key=f"sidebar_{page_id}",
            on_click=navigate_to,
            args=(page_id,),
            use_container_width=True,
        )
    page = st.session_state["current_page"]

if page == "dashboard":
    render_dashboard()
elif page == "crop_help":
    render_crop_help(selected_language)
elif page == "weather":
    render_weather()
elif page == "schemes":
    render_schemes()
elif page == "vault":
    render_vault()
elif page == "tools":
    render_tools()
elif page == "prices":
    render_prices()
elif page == "contacts":
    render_contacts()

st.info("ℹ️ " + tr("disclaimer"))
