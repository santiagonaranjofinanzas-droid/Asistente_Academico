import os
import asyncio
from playwright.async_api import async_playwright
from supabase import create_client, Client
from dotenv import load_dotenv
import datetime
import dateparser
from telegram_notifier import send_notification

load_dotenv()

# Configuration
URL = os.getenv("CAMPUS_URL", "https://micampusvirtual.espe.edu.ec")
USERNAME = os.getenv("CAMPUS_USER")
PASSWORD = os.getenv("CAMPUS_PASS")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

async def run_scraper():
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

            # Navigate to Timeline/Calendar or similar where tasks are listed
            # Note: This part is site-specific.
            # Usually 'https://micampusvirtual.espe.edu.ec/calendar/view.php?view=upcoming'
            await page.goto(f"{URL}/calendar/view.php?view=upcoming")
            await page.wait_for_selector(".eventlist", timeout=10000)
            
            # Scroll to ensure all lazy-loaded events are present if applicable
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(2)

            events = await page.query_selector_all(".event")
            tasks_found = []

            for event in events:
                title_elem = await event.query_selector("h3")
                title = await title_elem.inner_text() if title_elem else "Sin título"
                
                materia_elem = await event.query_selector(".course")
                materia = await materia_elem.inner_text() if materia_elem else "General"
                
                # Capture unique Moodle ID
                moodle_id = await event.get_attribute("data-event-id")
                
                # Targeted selector for date (Moodle structure)
                # The date is usually in the description row accompanied by a clock icon
                fecha_elem = await event.query_selector(".description .row .col-11")
                if not fecha_elem:
                    # Fallback to any col-11 in the description if the icon isn't found
                    fecha_elem = await event.query_selector(".description .col-11")
                
                fecha_str = await fecha_elem.inner_text() if fecha_elem else ""
                
                # Robust Parse date logic
                # Clean moodle string anomalies
                clean_fecha_str = fecha_str.replace('\t', ' ').replace('\n', ' ').replace(',', '').strip()
                
                # Handle relative dates before passing to dateparser
                now = datetime.datetime.now()
                tomorrow = now + datetime.timedelta(days=1)
                
                if "Hoy" in clean_fecha_str:
                    clean_fecha_str = clean_fecha_str.replace("Hoy", now.strftime("%d %B %Y"))
                elif "Maana" in clean_fecha_str or "Mañana" in clean_fecha_str:
                    clean_fecha_str = clean_fecha_str.replace("Maana", tomorrow.strftime("%d %B %Y")).replace("Mañana", tomorrow.strftime("%d %B %Y"))
                
                # Ensure year is present for absolute dates (e.g., "26 abril")
                if "202" not in clean_fecha_str:
                    clean_fecha_str += f" {now.year}"
                
                fecha_entrega = parsed_date.isoformat() if parsed_date else None
                
                # Clean description
                clean_desc = f"Fecha original: {fecha_str}"
                if not fecha_entrega:
                    clean_desc += " (Parse failed: " + clean_fecha_str + ")"

                # Upsert to Supabase
                task_data = {
                    "id_moodle": moodle_id,
                    "titulo": title,
                    "materia": materia,
                    "descripcion": clean_desc,
                    "estado": "por_empezar",
                    "archivada": False,
                    "fecha_entrega": fecha_entrega
                }
                
                if supabase:
                    # Upsert based on moodle_id to handle title changes gracefully
                    res = supabase.table("tareas").upsert(task_data, on_conflict="id_moodle").execute()
                    print(f"Task synced: {title} (ID: {moodle_id})")
                
                tasks_found.append(task_data)

            if tasks_found:
                await send_notification(f"✅ *Scraper ESPE*: Se encontraron {len(tasks_found)} tareas próximas.")
            else:
                print("No upcoming tasks found.")

        except Exception as e:
            print(f"An error occurred: {e}")
            await send_notification(f"⚠️ *Error Scraper*: {str(e)[:100]}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(run_scraper())
