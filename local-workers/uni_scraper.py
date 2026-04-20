import os
import asyncio
from playwright.async_api import async_playwright
from supabase import create_client, Client
from dotenv import load_dotenv
import datetime
import dateparser
from telegram_notifier import send_notification
import pdfplumber
import docx
import mimetypes

load_dotenv()

# Configuration
URL = os.getenv("CAMPUS_URL", "https://micampusvirtual.espe.edu.ec")
USERNAME = os.getenv("CAMPUS_USER")
PASSWORD = os.getenv("CAMPUS_PASS")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

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
        print(f"Launching scraper for {URL}...")
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        try:
            # Login
            await page.goto(f"{URL}/login/index.php")
            await page.fill("#username", USERNAME)
            await page.fill("#password", PASSWORD)
            await page.click("#loginbtn")
            
            # Wait for dashboard
            await page.wait_for_load_state("networkidle")
            print("Logged in successfully.")

            # Navigate to Dashboard/Timeline
            await page.goto(f"{URL}/my/")
            try:
                await page.wait_for_selector('[data-region="event-list-item"]', timeout=30000)
            except:
                print("No active tasks found in Timeline.")
                await send_notification("ℹ️ *Scraper ESPE*: No hay tareas pendientes en la línea de tiempo.")
                return

            # Ensure timeline is set to "All" (Todos) to not miss distant deadlines
            try:
                # Some Moodle versions use data-filtername="all" inside the timeline dropdown
                all_filter = await page.query_selector('[data-filtername="all"]')
                if all_filter:
                    await all_filter.click()
                    await page.wait_for_timeout(2000)
                else:
                    # Alternative: Open the dropdown first
                    dropdown = await page.query_selector('[data-action="timeline-filter-dropdown"]')
                    if dropdown:
                        await dropdown.click()
                        await page.wait_for_timeout(500)
                        all_filter_alt = await page.query_selector('[data-filtername="all"]')
                        if all_filter_alt:
                            await all_filter_alt.click()
                            await page.wait_for_timeout(2000)
            except Exception as e:
                print(f"Filter audit skipped/failed: {e}")

            # Ensure all items are loaded by clicking "Show more" or scrolling
            for _ in range(3):
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                try:
                    more_btn = await page.query_selector('[data-action="more-events"]')
                    if more_btn and await more_btn.is_visible():
                        await more_btn.click()
                except:
                    pass
                await asyncio.sleep(1)

            events = await page.query_selector_all('[data-region="event-list-item"]')
            tasks_found = []

            for event in events:
                # Extract Title - Refined Selector
                title_elem = await event.query_selector("h6.event-name a")
                title = await title_elem.inner_text() if title_elem else "Sin título"
                
                # Extract and Clean Materia - Refined Selector (small.mb-0)
                materia_info = await event.query_selector("small.mb-0")
                materia_raw = await materia_info.inner_text() if materia_info else "General"
                
                # Parse: "Vencimiento de Tarea · 27823-FISICA"
                materia = "General"
                if "·" in materia_raw:
                    materia_part = materia_raw.split("·")[-1].strip()
                    if "-" in materia_part:
                        materia = materia_part.split("-")[-1].strip()
                    else:
                        materia = materia_part
                
                # Capture unique Moodle ID from the link
                link = await title_elem.get_attribute("href") if title_elem else ""
                moodle_id = "".join(filter(str.isdigit, link)) if link else "0"
                
                # Extract Date string from Timeline structure
                # The aria-label is the most reliable source
                aria_label = await title_elem.get_attribute("aria-label") if title_elem else ""
                fecha_str = ""
                
                # aria-label format: "Tarea ... está pendiente para 22 de abril de 2026, 23:50"
                if "para" in aria_label:
                    fecha_str = aria_label.split("para")[-1].strip()
                
                # Fallback to visual text if aria-label fails
                if not fecha_str:
                    fecha_elem = await event.query_selector("small:not(.mb-0)")
                    fecha_str = await fecha_elem.inner_text() if fecha_elem else ""
                
                # Date Cleanup logic
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

                # Detect Delivery Status
                action_btn = await event.query_selector("a.btn")
                btn_text = await action_btn.inner_text() if action_btn else ""
                is_delivered = "Editar entrega" in btn_text
                
                texto_extraido = ""
                archivos_adjuntos = []
                
                # Fetch deeper context and files if not delivered
                if link and "assign" in link and not is_delivered:
                    try:
                        task_page = await context.new_page()
                        await task_page.goto(link)
                        await task_page.wait_for_load_state("networkidle")
                        
                        desc_elem = await task_page.query_selector('.box.py-3.generalbox.boxaligncenter, .intro')
                        if desc_elem:
                            texto_extraido += await desc_elem.inner_text() + "\n\n"
                            
                        file_links = await task_page.query_selector_all('.attachments a')
                        for fle in file_links:
                            f_url = await fle.get_attribute('href')
                            f_name = await fle.inner_text()
                            if f_url and ("?forcedownload=1" in f_url or ".pdf" in f_url or ".docx" in f_url):
                                try:
                                    async with task_page.expect_download(timeout=10000) as download_info:
                                        await fle.click()
                                    download = await download_info.value
                                    ext = os.path.splitext(f_name)[1].lower()
                                    temp_path = os.path.join(os.getcwd(), download.suggested_filename)
                                    await download.save_as(temp_path)
                                    
                                    if ext == '.pdf':
                                        with pdfplumber.open(temp_path) as pdf:
                                            texto_extraido += f"[{f_name}]:\n" + "\n".join([p.extract_text() for p in pdf.pages if p.extract_text()]) + "\n"
                                    elif ext == '.docx':
                                        doc = docx.Document(temp_path)
                                        texto_extraido += f"[{f_name}]:\n" + "\n".join([para.text for para in doc.paragraphs]) + "\n"
                                        
                                    if supabase:
                                        with open(temp_path, "rb") as f:
                                            try:
                                                supabase.storage.from_("documentos_espe").upload(
                                                    path=f"{moodle_id}/{download.suggested_filename}",
                                                    file=f,
                                                    file_options={"content-type": mimetypes.guess_type(download.suggested_filename)[0]}
                                                )
                                            except Exception as up_e:
                                                if "Duplicate" not in str(up_e):
                                                    print(f"Storage upload error: {up_e}")
                                        public_url = supabase.storage.from_("documentos_espe").get_public_url(f"{moodle_id}/{download.suggested_filename}")
                                        archivos_adjuntos.append({"nombre": f_name, "url": public_url})
                                        
                                    os.remove(temp_path)
                                except Exception as inner_e:
                                    print(f"File extraction failed for {f_name}: {inner_e}")
                        await task_page.close()
                    except Exception as e:
                        print(f"Failed deep parsing {title}: {e}")
                
                # Truncate text for safety
                texto_extraido = texto_extraido[:3000]

                task_data = {
                    "id_moodle": moodle_id,
                    "titulo": title,
                    "materia": materia,
                    "descripcion": f"Fecha original: {fecha_str} | Info: {materia_raw}",
                    "estado": "entregada" if is_delivered else "por_empezar",
                    "archivada": is_delivered,
                    "fecha_entrega": fecha_entrega,
                }
                
                if supabase:
                    try:
                        # Try inserting with new columns
                        full_data = {**task_data, "texto_extraido": texto_extraido, "archivos_adjuntos": archivos_adjuntos}
                        supabase.table("tareas").upsert(full_data, on_conflict="id_moodle").execute()
                    except Exception as e:
                        if "column" in str(e).lower() and "does not exist" in str(e).lower():
                            print("Warning: Nuevas columnas (texto_extraido, archivos_adjuntos) no creadas aún en Supabase. Usando Schema Fallback.")
                            supabase.table("tareas").upsert(task_data, on_conflict="id_moodle").execute()
                        else:
                            print(f"Error guardando {title}: {e}")
                    status_log = "[ENTREGADA]" if is_delivered else "[PENDIENTE]"
                    print(f"Task synced {status_log}: {title} | Materia: {materia}")
                
                tasks_found.append(task_data)

            if tasks_found:
                await send_notification(f"✅ *Scraper ESPE*: Se sincronizaron {len(tasks_found)} tareas desde la Línea de Tiempo.")
            else:
                print("No upcoming tasks found (Check if Timeline filter is 'All').")

        except Exception as e:
            print(f"An error occurred: {e}")
            await send_notification(f"⚠️ *Error Scraper*: {str(e)[:100]}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(run_scraper())
