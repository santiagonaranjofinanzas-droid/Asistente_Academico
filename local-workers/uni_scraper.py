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


async def login_moodle(page):
    """Perform login on Moodle."""
    await page.goto(f"{URL}/login/index.php")
    await page.fill("#username", USERNAME)
    await page.fill("#password", PASSWORD)
    await page.click("#loginbtn")
    await page.wait_for_load_state("networkidle")
    print("[SCRAPER] Logged in successfully.")

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

            # --- PHASE 1: TIMELINE ---
            print("\n[SCRAPER] PHASE 1: Scraping Dashboard Timeline...")
            await page.goto(f"{URL}/my/", wait_until="networkidle")
            
            # Set filter to "Todos"
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

            # Load all Timeline items
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
            print("\n[SCRAPER] PHASE 2: Scraping all individual courses (The 'Montón' fix)...")
            try:
                await page.goto(f"{URL}/my/courses.php", wait_until="networkidle")
                course_links = await page.query_selector_all('.course-listitem a.aalink, .coursebox .title a, [data-region="course-content"] a')
                course_urls = []
                for cl in course_links:
                    curl = await cl.get_attribute("href")
                    if curl and "/course/view.php?id=" in curl: course_urls.append(curl)
                
                course_urls = list(set(course_urls))
                print(f"[SCRAPER] Scanning {len(course_urls)} courses...")
                
                for curl in course_urls:
                    print(f"  [COURSE] Entering: {curl}")
                    await page.goto(curl, wait_until="domcontentloaded")
                    activity_links = await page.query_selector_all('a[href*="/mod/assign/view.php?id="], a[href*="/mod/quiz/view.php?id="]')
                    for alink in activity_links:
                        ahref = await alink.get_attribute("href")
                        if ahref: task_links_pool.add(ahref.split('#')[0])
            except Exception as e:
                print(f"[SCRAPER] Course phase failed: {e}")

            # --- PHASE 3: PROCESS ALL ---
            task_links_to_process = list(task_links_pool)
            print(f"\n[SCRAPER] TOTAL tasks to sync: {len(task_links_to_process)}")
            tasks_synced = []

                    # Clean link (remove fragment)
                    link = link.split('#')[0]
                    
                    # Determine Moodle ID from link
                    moodle_id = "".join(filter(str.isdigit, link.split("id=")[1].split("&")[0]))
                    if not moodle_id: continue
                    ids_moodle_encontrados.add(moodle_id)
                    
                    print(f"\n--- [{idx+1}/{len(task_links_to_process)}] Processing ID: {moodle_id} ---")
                    await page.goto(link, wait_until="networkidle", timeout=20000)
                    
                    # Basic Info
                    title = ""
                    title_elem = await page.query_selector("h2, .page-header-headings h1")
                    if title_elem: title = await title_elem.inner_text()
                    
                    # --- FILTER SYSTEM MESSAGES ---
                    if not title or "¿Desea acceder ahora" in title or "acceso" in title.lower():
                        print(f"  [SKIP] System message detected: {title[:30]}")
                        continue

                    # --- IMPROVED MATERIA EXTRACTION ---
                    materia = "General"
                    breadcrumb = await page.query_selector(".breadcrumb")
                    if breadcrumb:
                        items = await breadcrumb.query_selector_all("li")
                        # Usually: Home > Courses > Course Name > Task Name
                        # We want 'Course Name'. It's typically at index 2 or 3.
                        for i in range(len(items)):
                            txt = await items[i].inner_text()
                            # Skip common non-course breadcrumbs
                            if any(x in txt for x in ["Principal", "Área personal", "Mis cursos", "Dashboard", "Home", "Courses"]):
                                continue
                            if i < len(items) - 1: # The last one is the task itself
                                materia = txt.strip()
                                # Clean up common course codes (e.g. 27817-NAME -> NAME)
                                if "-" in materia:
                                    materia = materia.split("-", 1)[-1].strip()
                                break
                    
                    if materia == "General":
                        # Try page header as fallback
                        header = await page.query_selector(".page-header-headings h1")
                        if header:
                            h_txt = await header.inner_text()
                            if h_txt and h_txt != title:
                                materia = h_txt.strip()
                    
                    is_quiz = "/mod/quiz/" in link
                    date_text = ""
                    if is_quiz:
                        info = await page.query_selector(".quizinfo")
                        if info: date_text = await info.inner_text()
                    else:
                        table = await page.query_selector(".submissionstatustable")
                        if table: date_text = await table.inner_text()
                    
                    is_delivered = any(x in date_text for x in ["Enviado", "Calificado", "Finalizado", "Hecho", "Terminado"])
                    
                    # Description and Files (same logic as before but simplified for readability)
                    description = ""
                    desc_elem = await page.query_selector(".box.py-3.generalbox, .instructions, #intro")
                    if desc_elem: description = await desc_elem.inner_text()
                    
                    # --- DATE PARSING (Restored robust logic) ---
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
                        print(f"  [DB] Synced: {title[:40]}")
                    
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
