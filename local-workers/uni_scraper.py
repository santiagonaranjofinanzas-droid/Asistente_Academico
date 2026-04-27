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

load_dotenv()

# Configuration
URL = os.getenv("CAMPUS_URL", "https://micampusvirtual.espe.edu.ec")
USERNAME = os.getenv("CAMPUS_USER")
PASSWORD = os.getenv("CAMPUS_PASS")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
OLLAMA_API = "http://127.0.0.1:11434/api/generate"

# --- Helper Functions ---

def generate_ai_summary(titulo: str, materia: str, descripcion: str, texto_extraido: str) -> str:
    """Generate an AI summary using local Ollama. Returns empty string on failure."""
    try:
        # Check if Ollama is running
        try:
            requests.get("http://127.0.0.1:11434/", timeout=2)
        except:
            print("  [IA] Ollama no está corriendo. Saltando resumen IA.")
            return ""
        
        context = texto_extraido[:2500] if texto_extraido else ""
        extra = f"\nContexto del documento adjunto:\n{context}" if context else ""
        
        prompt = f"""Eres un asistente académico experto. Resume brevemente de qué trata esta tarea y da 3 pasos sugeridos para realizarla rápidamente.
Tarea: {titulo}
Materia: {materia}
Descripción: {descripcion}
{extra}
Responde en español, sé directo, usa viñetas concisas y no más de 100 palabras en total."""

        response = requests.post(OLLAMA_API, json={
            "model": "llama3.2",
            "prompt": prompt,
            "stream": False
        }, timeout=120)
        
        if response.status_code == 200:
            data = response.json()
            summary = data.get("response", "").strip()
            if summary:
                print(f"  [IA] Resumen generado ({len(summary)} chars)")
                return summary
        return ""
    except Exception as e:
        print(f"  [IA] Error generando resumen: {e}")
        return ""


def detect_task_type(title: str) -> str:
    """Categorize task based on keywords in title."""
    t = title.lower()
    # Pruebas, Exámenes, Controles de lectura
    if any(w in t for w in ["prueba", "examen", "test", "evaluaci", "quiz", "control", "leccion", "lección"]):
        return "prueba"
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
    # Remove empty segments
    name = name.strip('._')
    if not name:
        name = f"documento_{datetime.datetime.now().strftime('%H%M%S')}"
    if fallback_ext and not os.path.splitext(name)[1]:
        name += fallback_ext
    return name


async def run_scraper():
    """
    SECURITY POLICY: READ-ONLY SCRAPER
    This scraper is strictly forbidden from:
    1. Clicking 'Submit', 'Delete', or 'Edit' buttons for assignments.
    2. Modifying any university files or data.
    3. Uploading content to the Moodle platform.
    It ONLY uses navigation and data extraction (innerText/getAttribute).
    """
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("Supabase credentials missing. Scraper will run in dry-run mode.")
        supabase: Client = None
    else:
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

    async with async_playwright() as p:
        print(f"[SCRAPER] Launching for {URL}...")
        browser = await p.chromium.launch(headless=True)
        # CRITICAL: accept_downloads must be True to download files
        context = await browser.new_context(accept_downloads=True)
        page = await context.new_page()

        try:
            # --- LOGIN ---
            await page.goto(f"{URL}/login/index.php")
            await page.fill("#username", USERNAME)
            await page.fill("#password", PASSWORD)
            await page.click("#loginbtn")
            await page.wait_for_load_state("networkidle")
            print("[SCRAPER] Logged in successfully.")

            # --- NAVIGATE TO TIMELINE ---
            await page.goto(f"{URL}/my/")
            try:
                await page.wait_for_selector('[data-region="event-list-item"]', timeout=30000)
            except:
                print("[SCRAPER] No active tasks found in Timeline.")
                await send_notification("ℹ️ *Scraper ESPE*: No hay tareas pendientes en la línea de tiempo.")
                return

            # --- FORCE "ALL" FILTER ---
            try:
                dropdown = await page.query_selector('[data-action="timeline-filter-dropdown"]')
                if dropdown:
                    await dropdown.click(force=True, timeout=5000)
                    await page.wait_for_timeout(500)
                all_filter = await page.query_selector('[data-filtername="all"]')
                if all_filter:
                    await all_filter.click(force=True, timeout=5000)
                    await page.wait_for_timeout(2000)
            except Exception as e:
                print(f"[SCRAPER] Filter audit skipped: {e}")

            # --- LOAD ALL ITEMS ---
            for _ in range(5):
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                try:
                    more_btn = await page.query_selector('[data-action="more-events"]')
                    if more_btn and await more_btn.is_visible():
                        await more_btn.click()
                        await page.wait_for_timeout(1500)
                except:
                    pass
                await asyncio.sleep(0.5)

            events = await page.query_selector_all('[data-region="event-list-item"]')
            tasks_found = []
            print(f"[SCRAPER] Found {len(events)} events in timeline.")

            for idx, event in enumerate(events):
                # --- EXTRACT TITLE ---
                title_elem = await event.query_selector("h6.event-name a")
                title = await title_elem.inner_text() if title_elem else "Sin título"
                print(f"\n--- [{idx+1}/{len(events)}] {title[:60]} ---")
                
                # --- EXTRACT MATERIA ---
                materia_info = await event.query_selector("small.mb-0")
                materia_raw = await materia_info.inner_text() if materia_info else "General"
                materia = "General"
                if "·" in materia_raw:
                    materia_part = materia_raw.split("·")[-1].strip()
                    materia = materia_part.split("-")[-1].strip() if "-" in materia_part else materia_part
                
                # --- EXTRACT MOODLE ID ---
                link = await title_elem.get_attribute("href") if title_elem else ""
                moodle_id = "".join(filter(str.isdigit, link)) if link else "0"
                
                # --- EXTRACT DATE ---
                aria_label = await title_elem.get_attribute("aria-label") if title_elem else ""
                fecha_str = ""
                if "para" in aria_label:
                    fecha_str = aria_label.split("para")[-1].strip()
                if not fecha_str:
                    fecha_elem = await event.query_selector("small:not(.mb-0)")
                    fecha_str = await fecha_elem.inner_text() if fecha_elem else ""
                
                clean_fecha_str = fecha_str.replace('\t', ' ').replace('\n', ' ').replace(',', '').strip()
                now = datetime.datetime.now()
                tomorrow = now + datetime.timedelta(days=1)
                if "Hoy" in clean_fecha_str:
                    clean_fecha_str = clean_fecha_str.replace("Hoy", now.strftime("%d %B %Y"))
                elif "Maana" in clean_fecha_str or "Mañana" in clean_fecha_str:
                    clean_fecha_str = clean_fecha_str.replace("Maana", tomorrow.strftime("%d %B %Y")).replace("Mañana", tomorrow.strftime("%d %B %Y"))
                if "202" not in clean_fecha_str:
                    clean_fecha_str += f" {now.year}"
                
                parsed_date = dateparser.parse(clean_fecha_str, languages=['es'], settings={'PREFER_DATES_FROM': 'future'})
                fecha_entrega = parsed_date.isoformat() if parsed_date else None

                # --- DETECT DELIVERY STATUS ---
                action_btn = await event.query_selector("a.btn")
                btn_text = await action_btn.inner_text() if action_btn else ""
                is_delivered = "Editar entrega" in btn_text
                
                texto_extraido = ""
                archivos_adjuntos = []
                resumen_ia = ""
                
                # --- DEEP PARSING: Visit task page for description & files ---
                if link and not is_delivered:
                    try:
                        task_page = await context.new_page()
                        await task_page.goto(link, wait_until="networkidle", timeout=15000)
                        
                        # Get full description text
                        for selector in ['.box.py-3.generalbox.boxaligncenter', '.intro', '#intro', '.submissionstatustable']:
                            desc_elem = await task_page.query_selector(selector)
                            if desc_elem:
                                desc_text = await desc_elem.inner_text()
                                if desc_text and len(desc_text.strip()) > 10:
                                    texto_extraido += desc_text.strip() + "\n\n"
                                    print(f"  [DESC] Extracted {len(desc_text)} chars from {selector}")
                                    break
                        
                        # Find downloadable file links (multiple Moodle selectors)
                        file_selectors = [
                            '.fileuploadsubmission a',
                            '.attachments a', 
                            '.mod_assign_intro a[href*="pluginfile"]',
                            'a[href*="pluginfile.php"]',
                            '.resourceworkaround a'
                        ]
                        
                        all_file_links = []
                        for sel in file_selectors:
                            links_found = await task_page.query_selector_all(sel)
                            all_file_links.extend(links_found)
                        
                        # Deduplicate by href
                        seen_urls = set()
                        for fle in all_file_links:
                            f_url = await fle.get_attribute('href')
                            if not f_url or f_url in seen_urls:
                                continue
                            seen_urls.add(f_url)
                            
                            f_name = await fle.inner_text()
                            f_name = f_name.strip() if f_name else ""
                            
                            # Only process actual document links
                            is_document = any(ext in f_url.lower() for ext in ['.pdf', '.docx', '.doc', '.pptx', '.xlsx'])
                            is_pluginfile = 'pluginfile.php' in f_url
                            
                            if not (is_document or is_pluginfile):
                                continue
                            
                            print(f"  [FILE] Found: {f_name or f_url[:60]}")
                            
                            try:
                                # Direct download via navigation (more reliable than click)
                                download_url = f_url
                                if 'forcedownload' not in download_url:
                                    separator = '&' if '?' in download_url else '?'
                                    download_url += f"{separator}forcedownload=1"
                                
                                async with task_page.expect_download(timeout=15000) as download_info:
                                    await task_page.evaluate(f'window.location.href = "{download_url}"')
                                download = await download_info.value
                                
                                # Build a clean filename
                                suggested = download.suggested_filename or ""
                                ext = os.path.splitext(suggested)[1].lower()
                                
                                if f_name and len(f_name) > 3:
                                    clean_fname = sanitize_filename(f_name, ext)
                                else:
                                    clean_fname = sanitize_filename(suggested)
                                
                                temp_path = os.path.join(os.getcwd(), "temp_downloads", clean_fname)
                                os.makedirs(os.path.dirname(temp_path), exist_ok=True)
                                await download.save_as(temp_path)
                                print(f"  [FILE] Downloaded: {clean_fname} ({os.path.getsize(temp_path)} bytes)")
                                
                                # Extract text
                                file_text = extract_text_from_file(temp_path)
                                if file_text:
                                    texto_extraido += f"\n[Archivo: {clean_fname}]:\n{file_text}\n"
                                    print(f"  [FILE] Extracted {len(file_text)} chars of text")
                                
                                # Upload to Supabase Storage
                                if supabase:
                                    storage_path = f"{moodle_id}/{clean_fname}"
                                    content_type = mimetypes.guess_type(clean_fname)[0] or "application/octet-stream"
                                    try:
                                        with open(temp_path, "rb") as f:
                                            supabase.storage.from_("documentos_espe").upload(
                                                path=storage_path,
                                                file=f,
                                                file_options={"content-type": content_type}
                                            )
                                        print(f"  [STORAGE] Uploaded to bucket: {storage_path}")
                                    except Exception as up_e:
                                        if "Duplicate" in str(up_e) or "already exists" in str(up_e).lower():
                                            print(f"  [STORAGE] Already exists: {storage_path}")
                                        else:
                                            print(f"  [STORAGE] Upload error: {up_e}")
                                    
                                    public_url = supabase.storage.from_("documentos_espe").get_public_url(storage_path)
                                    archivos_adjuntos.append({
                                        "nombre": clean_fname,
                                        "url": public_url
                                    })
                                
                                # Cleanup temp file
                                try:
                                    os.remove(temp_path)
                                except:
                                    pass
                                    
                            except Exception as dl_err:
                                print(f"  [FILE] Download failed: {dl_err}")
                                # Fallback: just store the URL directly
                                if f_url:
                                    archivos_adjuntos.append({
                                        "nombre": f_name or "Documento",
                                        "url": f_url
                                    })
                        
                        await task_page.close()
                    except Exception as e:
                        print(f"  [DEEP] Failed: {e}")
                
                # --- TRUNCATE TEXT FOR SAFETY ---
                texto_extraido = texto_extraido[:3000]
                
                # --- GENERATE AI SUMMARY LOCALLY ---
                if texto_extraido and not is_delivered:
                    resumen_ia = generate_ai_summary(title, materia, f"Fecha: {fecha_str}", texto_extraido)
                
                # --- BUILD TASK DATA ---
                task_data = {
                    "id_moodle": moodle_id,
                    "titulo": title,
                    "materia": materia,
                    "descripcion": f"Fecha original: {fecha_str} | Info: {materia_raw}",
                    "estado": "entregada" if is_delivered else "por_empezar",
                    "archivada": is_delivered,
                    "fecha_entrega": fecha_entrega,
                    "texto_extraido": texto_extraido,
                    "archivos_adjuntos": json.dumps(archivos_adjuntos) if archivos_adjuntos else "[]",
                    "resumen_ia": resumen_ia,
                    "tipo": detect_task_type(title),
                }
                
                # --- SAVE TO SUPABASE ---
                if supabase:
                    try:
                        # Check if task already exists
                        existing = supabase.table("tareas").select("estado, archivada, checklist, resumen_ia").eq("id_moodle", moodle_id).execute()
                        
                        if existing.data and len(existing.data) > 0:
                            old_task = existing.data[0]
                            # Preserve user state if not newly delivered in Moodle
                            if not is_delivered and old_task.get("estado") not in [None, "por_empezar"]:
                                task_data["estado"] = old_task.get("estado")
                                task_data["archivada"] = old_task.get("archivada")
                            
                            # Always preserve checklist if it exists
                            if old_task.get("checklist"):
                                task_data["checklist"] = old_task.get("checklist")
                                
                            # Preserve AI summary if we didn't generate a new one
                            if not resumen_ia and old_task.get("resumen_ia"):
                                task_data["resumen_ia"] = old_task.get("resumen_ia")

                        supabase.table("tareas").upsert(task_data, on_conflict="id_moodle").execute()
                        status = "ENTREGADA" if is_delivered else "PENDIENTE"
                        print(f"  [DB] Synced [{status}] | Materia: {materia}")
                    except Exception as e:
                        # Fallback: try without new columns
                        print(f"  [DB] Full save failed: {e}")
                        fallback = {k: v for k, v in task_data.items() if k not in ['texto_extraido', 'archivos_adjuntos', 'resumen_ia']}
                        try:
                            supabase.table("tareas").upsert(fallback, on_conflict="id_moodle").execute()
                            print(f"  [DB] Fallback save OK")
                        except Exception as e2:
                            print(f"  [DB] Fallback also failed: {e2}")
                
                tasks_found.append(task_data)

            # --- FINAL SUMMARY ---
            print(f"\n{'='*50}")
            print(f"[SCRAPER] Completed: {len(tasks_found)} tasks processed.")
            files_count = sum(len(json.loads(t.get('archivos_adjuntos', '[]'))) for t in tasks_found)
            ai_count = sum(1 for t in tasks_found if t.get('resumen_ia'))
            print(f"[SCRAPER] Files found: {files_count} | AI summaries: {ai_count}")
            
            if tasks_found:
                await send_notification(
                    f"✅ *Scraper ESPE*: {len(tasks_found)} tareas sincronizadas.\n"
                    f"📎 Archivos: {files_count} | 🤖 Resúmenes IA: {ai_count}"
                )

        except Exception as e:
            print(f"[SCRAPER] Critical error: {e}")
            import traceback
            traceback.print_exc()
            await send_notification(f"⚠️ *Error Scraper*: {str(e)[:100]}")
        finally:
            await browser.close()
            # Cleanup temp dir
            try:
                import shutil
                shutil.rmtree(os.path.join(os.getcwd(), "temp_downloads"), ignore_errors=True)
            except:
                pass

if __name__ == "__main__":
    asyncio.run(run_scraper())
