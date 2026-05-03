import os
import asyncio
import json
from playwright.async_api import async_playwright
from supabase import create_client, Client
from dotenv import load_dotenv
import datetime
import dateparser
from telegram_notifier import send_notification
import pdfplumber
import docx
import mimetypes
import requests
from ai_service import generate_response

load_dotenv()

# Configuration
URL = os.getenv("CAMPUS_URL", "https://micampusvirtual.espe.edu.ec")
USERNAME = os.getenv("CAMPUS_USER")
PASSWORD = os.getenv("CAMPUS_PASS")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

# --- Helper Functions ---

def generate_ai_summary(titulo: str, materia: str, descripcion: str, texto_extraido: str) -> str:
    """Generate an AI summary using NVIDIA AI API. Returns empty string on failure."""
    try:
        context = texto_extraido[:3000] if texto_extraido else ""
        extra = f"\nContexto del documento adjunto:\n{context}" if context else ""
        
        prompt = f"""Eres un asistente académico experto. Resume brevemente de qué trata esta tarea y da 3 pasos sugeridos para realizarla rápidamente.
Tarea: {titulo}
Materia: {materia}
Descripción: {descripcion}
{extra}
Responde en español, sé directo, usa viñetas concisas y no más de 120 palabras en total."""

        summary = generate_response(prompt)
        
        if summary and not summary.startswith("Error"):
            print(f"  [IA] Resumen generado ({len(summary)} chars)")
            return summary.strip()
        
        return ""
    except Exception as e:
        print(f"  [IA] Error generando resumen: {e}")
        return ""


def generate_ai_type(titulo: str, materia: str) -> str:
    """Use NVIDIA AI API to classify the task as 'prueba' or 'deber'."""
    try:
        prompt = f"""Clasifica la siguiente actividad académica en una de dos categorías: 'prueba' (si es un examen, test, lección o control de lectura) o 'deber' (si es una tarea, proyecto, ensayo o trabajo en casa).
Responde ÚNICAMENTE con la palabra 'prueba' o 'deber' en minúsculas.

Título: {titulo}
Materia: {materia}
"""
        ans = generate_response(prompt, system_prompt="Eres un clasificador de tareas académicas. Responde solo con la categoría.")
        
        if ans:
            ans = ans.lower()
            if "prueba" in ans or "examen" in ans:
                return "prueba"
            if "deber" in ans or "tarea" in ans:
                return "deber"
        return ""
    except Exception:
        return ""


def detect_task_type(title: str, materia: str) -> str:
    """Categorize task robustly using AI or keywords."""
    t = title.lower()
    
    # --- PRIORITY 1: Clear keywords for PRUEBAS ---
    prueba_keywords = ["prueba", "examen", "test", "quiz", "control de lectura", "leccion", "lección", "evaluación", "evaluacion", "cuestionario", "parcial"]
    if any(w in t for w in prueba_keywords):
        print(f"  [TYPE] Classified as 'prueba' by keyword: {title[:30]}")
        return "prueba"

    # --- PRIORITY 2: AI Classification ---
    ai_type = generate_ai_type(title, materia)
    if ai_type in ["prueba", "deber"]:
        print(f"  [IA-TYPE] Classified as: {ai_type}")
        return ai_type
        
    # --- PRIORITY 3: Fallback for Deberes ---
    print("  [TYPE] Fallback to 'deber'")
    return "deber"


def extract_text_from_file(file_path: str) -> str:
    """Extract text from PDF or DOCX files."""
    ext = os.path.splitext(file_path)[1].lower()
    try:
        if ext == '.pdf':
            with pdfplumber.open(file_path) as pdf:
                pages = [p.extract_text() for p in pdf.pages if p.extract_text()]
                return "\n".join(pages)
        elif ext == '.docx':
            doc = docx.Document(file_path)
            return "\n".join([para.text for para in doc.paragraphs if para.text.strip()])
    except Exception as e:
        print(f"  [EXTRACT] Error leyendo {file_path}: {e}")
    return ""


def sanitize_filename(raw_name: str, fallback_ext: str = "") -> str:
    """Clean a filename for cross-platform safety."""
    name = raw_name.strip().replace(" ", "_")
    for char in '<>:"/\\|?*\r\n\t':
        name = name.replace(char, '')
    name = name.strip('._')
    if not name:
        name = f"documento_{datetime.datetime.now().strftime('%H%M%S')}"
    if fallback_ext and not os.path.splitext(name)[1]:
        name += fallback_ext
    return name


async def take_screenshot(page, name):
    """Helper to save a screenshot for debugging."""
    os.makedirs("debug_screenshots", exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%H%M%S")
    path = f"debug_screenshots/{name}_{timestamp}.png"
    await page.screenshot(path=path)
    print(f"  [DEBUG] Screenshot saved: {path}")

async def login_moodle(page):
    """Perform login on Moodle with verification."""
    print(f"[SCRAPER] Navigating to login...")
    await page.goto(f"{URL}/login/index.php", wait_until="networkidle")
    
    # Check if already logged in
    if await page.query_selector('.userpicture'):
        print("[SCRAPER] Already logged in.")
        return True

    await page.fill("#username", USERNAME)
    await page.fill("#password", PASSWORD)
    await page.click("#loginbtn")
    await page.wait_for_load_state("networkidle")
    
    if await page.query_selector('.userpicture'):
        print("[SCRAPER] Logged in successfully.")
        return True
    else:
        print("[SCRAPER] Login failed!")
        await take_screenshot(page, "login_failed")
        return False

async def run_scraper():
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("Supabase credentials missing. Scraper will run in dry-run mode.")
        supabase: Client = None
    else:
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

    async with async_playwright() as p:
        print(f"[SCRAPER] Launching for {URL}...")
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(accept_downloads=True)
        page = await context.new_page()

        try:
            # --- LOGIN ---
            await login_moodle(page)

            # --- POOL OF TASKS TO PROCESS ---
            task_links_pool = set()
            ids_moodle_encontrados = set()
            course_map = {} # course_id -> full_name

            # --- PHASE 1: TIMELINE ---
            print("\n[SCRAPER] PHASE 1: Scraping Dashboard Timeline...")
            await page.goto(f"{URL}/my/", wait_until="networkidle")
            
            try:
                filter_trigger = await page.query_selector('[data-region="timeline"] [data-action="filter-dropdown"]')
                if not filter_trigger: filter_trigger = await page.query_selector('[data-action="timeline-filter-dropdown"]')
                if filter_trigger:
                    await filter_trigger.click(force=True)
                    await page.wait_for_timeout(1000)
                    all_opt = await page.query_selector("[aria-label='Todos opción de filtro']") or await page.query_selector("text='Todos'")
                    if all_opt: 
                        await all_opt.click(force=True)
                        await page.wait_for_timeout(2000)
            except: pass

            while True:
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                more_btn = await page.query_selector('[data-action="more-events"]')
                if more_btn and await more_btn.is_visible():
                    await more_btn.click()
                    await page.wait_for_timeout(2000)
                else: break

            timeline_links = await page.query_selector_all('[data-region="event-list-item"] a[data-action="view-event"]')
            for tlink in timeline_links:
                href = await tlink.get_attribute("href")
                if href: task_links_pool.add(href)
            print(f"[SCRAPER] Found {len(timeline_links)} links in Timeline.")

            # --- PHASE 2: COURSES ---
            print("\n[SCRAPER] PHASE 2: Scraping all individual courses (Deep Scrape)...")
            try:
                await page.goto(f"{URL}/my/courses.php", wait_until="networkidle", timeout=30000)
                # Broader selectors for different Moodle themes
                selectors = [
                    '.course-listitem', 
                    '.coursebox', 
                    '[data-region="course-content"] [data-courseid]',
                    '.dashboard-card-deck .dashboard-card',
                    '#frontpage-course-list .coursebox'
                ]
                
                course_items = []
                for sel in selectors:
                    items = await page.query_selector_all(sel)
                    if items:
                        print(f"  [UI] Found {len(items)} course items using selector: {sel}")
                        course_items = items
                        break
                
                if not course_items:
                    print("  [WARNING] No course items found with primary selectors. Trying fallback links...")
                    course_items = await page.query_selector_all('a[href*="/course/view.php?id="]')

                for item in course_items:
                    # Try to find the link within the item, or the item itself if it's a link
                    link_elem = await item.query_selector('a.aalink, .title a, a[href*="/course/view.php?id="]')
                    if not link_elem and await item.get_attribute("href") and "/course/view.php?id=" in await item.get_attribute("href"):
                        link_elem = item
                    
                    if link_elem:
                        curl = await link_elem.get_attribute("href")
                        cname = await link_elem.inner_text()
                        
                        if curl and "id=" in curl:
                            cid = curl.split("id=")[1].split("&")[0]
                            # Robust cleaning: remove common prefixes/codes
                            clean_name = cname.strip().replace("\n", " ")
                            # Remove "Nombre del curso" if present
                            import re
                            clean_name = re.sub(r'^Nombre del curso\s*', '', clean_name, flags=re.IGNORECASE)
                            
                            # Remove typical patterns like [27817] or "202650 - "
                            clean_name = re.sub(r'\[\d+\]\s*', '', clean_name)
                            clean_name = re.sub(r'^\d+[-\s]+', '', clean_name)
                            
                            # Deduplicate if name appears twice (sentence level)
                            s_words = clean_name.split()
                            if len(s_words) >= 4:
                                mid = len(s_words) // 2
                                first_half = " ".join(s_words[:mid]).lower()
                                second_half = " ".join(s_words[mid:]).lower()
                                if first_half in second_half or second_half in first_half:
                                    clean_name = " ".join(s_words[mid:])
                            
                            if " - " in clean_name: clean_name = clean_name.split(" - ", 1)[-1]
                            
                            course_map[cid] = clean_name.strip()
                            # Print with utf-8 encoding for logs
                            print(f"    [MAP] {cid} -> {course_map[cid]}")
                
                print(f"[SCRAPER] Course Map ready with {len(course_map)} subjects.")
                
                # Scan each course for activities
                for cid in list(course_map.keys()):
                    curl = f"{URL}/course/view.php?id={cid}"
                    print(f"  [COURSE] Scanning: {course_map[cid]}...")
                    try:
                        await page.goto(curl, wait_until="domcontentloaded", timeout=15000)
                        # Extract all activity links
                        activity_links = await page.query_selector_all('a[href*="/mod/assign/view.php?id="], a[href*="/mod/quiz/view.php?id="]')
                        for alink in activity_links:
                            ahref = await alink.get_attribute("href")
                            if ahref: task_links_pool.add(ahref.split('#')[0])
                    except Exception as ce:
                        print(f"    [COURSE] Skip {cid}: {ce}")
            except Exception as e:
                print(f"[SCRAPER] Course phase failed: {e}")
                await take_screenshot(page, "course_phase_error")

            # --- PHASE 3: PROCESS ALL ---
            task_links_to_process = list(task_links_pool)
            print(f"\n[SCRAPER] TOTAL tasks to sync: {len(task_links_to_process)}")
            tasks_synced = []

            for idx, link in enumerate(task_links_to_process):
                try:
                    # Clean link
                    link = link.split('#')[0]
                    moodle_id = "".join(filter(str.isdigit, link.split("id=")[1].split("&")[0]))
                    if not moodle_id: continue
                    ids_moodle_encontrados.add(moodle_id)
                    
                    print(f"\n--- [{idx+1}/{len(task_links_to_process)}] Processing ID: {moodle_id} ---")
                    await page.goto(link, wait_until="networkidle", timeout=20000)
                    
                    # Basic Info
                    title = ""
                    title_elem = await page.query_selector("h2, .page-header-headings h1")
                    if title_elem: title = await title_elem.inner_text()
                    
                    if not title or "¿Desea acceder ahora" in title or "acceso" in title.lower():
                        print(f"  [SKIP] System message detected: {title[:30]}")
                        continue

                    # --- ROBUST MATERIA EXTRACTION ---
                    materia = "General"
                    
                    # Try to find course ID on the current page to use the map
                    current_course_id = ""
                    # 1. From breadcrumbs link
                    course_breadcrumb = await page.query_selector('li.breadcrumb-item a[href*="/course/view.php?id="]')
                    if course_breadcrumb:
                        cb_href = await course_breadcrumb.get_attribute("href")
                        if "id=" in cb_href:
                            current_course_id = cb_href.split("id=")[1].split("&")[0]
                    
                    # 2. From page body or other links if breadcrumb failed
                    if not current_course_id:
                        any_course_link = await page.query_selector('a[href*="/course/view.php?id="]')
                        if any_course_link:
                            ac_href = await any_course_link.get_attribute("href")
                            current_course_id = ac_href.split("id=")[1].split("&")[0]

                    # Use map if ID found
                    if current_course_id in course_map:
                        materia = course_map[current_course_id]
                    else:
                        # Fallback to breadcrumb text if ID not in map (should be rare)
                        breadcrumb = await page.query_selector(".breadcrumb")
                        if breadcrumb:
                            items = await breadcrumb.query_selector_all("li")
                            for i in range(len(items) - 2, -1, -1):
                                txt = (await items[i].inner_text()).strip()
                                if not txt or any(x in txt.lower() for x in ["principal", "área personal", "mis cursos", "dashboard", "home", "parcial", "unidad", "semana"]):
                                    continue
                                materia = txt
                                break
                    
                    # Final cleanup: remove tech codes if any still exist
                    if materia != "General":
                        if " - " in materia: materia = materia.split(" - ", 1)[-1].strip()
                        if "]" in materia: materia = materia.split("]", 1)[-1].strip()
                        if materia == title: materia = "General"

                    is_quiz = "/mod/quiz/" in link
                    date_text = ""
                    if is_quiz:
                        info = await page.query_selector(".quizinfo")
                        if info: date_text = await info.inner_text()
                    else:
                        table = await page.query_selector(".submissionstatustable")
                        if table: date_text = await table.inner_text()
                    
                    is_delivered = any(x in date_text for x in ["Enviado", "Calificado", "Finalizado", "Hecho", "Terminado"])
                    
                    # Date parsing
                    fecha_entrega = None
                    try:
                        clean_date_str = date_text.replace('\t', ' ').replace('\n', ' ').replace(',', '').strip()
                        now = datetime.datetime.now()
                        tomorrow = now + datetime.timedelta(days=1)
                        if "Hoy" in clean_date_str: clean_date_str = clean_date_str.replace("Hoy", now.strftime("%d %B %Y"))
                        elif "Mañana" in clean_date_str: clean_date_str = clean_date_str.replace("Mañana", tomorrow.strftime("%d %B %Y"))
                        if "202" not in clean_date_str: clean_date_str += f" {now.year}"
                        parsed_date = dateparser.parse(clean_date_str, languages=['es'], settings={'PREFER_DATES_FROM': 'future'})
                        if parsed_date: fecha_entrega = parsed_date.isoformat()
                    except: pass

                    description = ""
                    desc_elem = await page.query_selector(".box.py-3.generalbox, .instructions, #intro")
                    if desc_elem: description = await desc_elem.inner_text()
                    
                    # Upsert
                    task_data = {
                        "id_moodle": moodle_id,
                        "titulo": title or "Tarea",
                        "materia": materia,
                        "descripcion": description[:2000],
                        "estado": "entregada" if is_delivered else "por_empezar",
                        "archivada": is_delivered,
                        "fecha_entrega": fecha_entrega,
                        "tipo": detect_task_type(title, materia)
                    }
                    
                    if supabase:
                        supabase.table("tareas").upsert(task_data, on_conflict="id_moodle").execute()
                        print(f"  [DB] Synced: {title[:40]} | Materia: {materia}")
                    
                    tasks_synced.append(task_data)
                except Exception as e:
                    print(f"  [ERROR] ID {link}: {e}")

            # --- CLEANUP PHASE (Safe verification) ---
            num_limpiados = 0
            if supabase and len(ids_moodle_encontrados) > 0:
                print(f"\n[SYNC] Verifying deletions for tasks not found in this run...")
                res = supabase.table("tareas").select("id_moodle, titulo").eq("archivada", False).execute()
                for t_db in (res.data or []):
                    mid = t_db.get("id_moodle")
                    if mid and mid not in ids_moodle_encontrados and not mid.startswith("msg_"):
                        print(f"  [VERIFY] Checking if {mid} still exists...")
                        await page.goto(f"{URL}/mod/assign/view.php?id={mid}", wait_until="domcontentloaded")
                        if "No se pudo encontrar" in await page.content():
                            supabase.table("tareas").update({"archivada": True, "estado": "entregada"}).eq("id_moodle", mid).execute()
                            num_limpiados += 1
            
            if tasks_synced:
                await send_notification(f"✅ *Scraper ESPE*: {len(tasks_synced)} tareas sincronizadas.\n🧹 Limpieza: {num_limpiados} archivadas.")

        except Exception as e:
            print(f"[SCRAPER] Critical error: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(run_scraper())
