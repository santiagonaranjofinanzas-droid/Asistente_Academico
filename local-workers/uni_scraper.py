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
            # Note: This part is site-specific. I'll use common moodle selectors as placeholder logic.
            # Usually 'https://micampusvirtual.espe.edu.ec/calendar/view.php?view=upcoming'
            await page.goto(f"{URL}/calendar/view.php?view=upcoming")
            await page.wait_for_selector(".eventlist")

            events = await page.query_selector_all(".event")
            tasks_found = []

            for event in events:
                title_elem = await event.query_selector("h3")
                title = await title_elem.inner_text() if title_elem else "Sin título"
                
                materia_elem = await event.query_selector(".course")
                materia = await materia_elem.inner_text() if materia_elem else "General"
                
                fecha_elem = await event.query_selector(".date")
                fecha_str = await fecha_elem.inner_text() if fecha_elem else ""
                
                # Parse date logic
                parsed_date = dateparser.parse(fecha_str, languages=['es'])
                fecha_entrega = parsed_date.isoformat() if parsed_date else None

                # Upsert to Supabase
                task_data = {
                    "titulo": title,
                    "materia": materia,
                    "descripcion": f"Fecha detectada: {fecha_str}",
                    "estado": "por_empezar",
                    "archivada": False,
                    "fecha_entrega": fecha_entrega
                }
                
                if supabase:
                    # Upsert based on title and materia to avoid duplicates
                    res = supabase.table("tareas").upsert(task_data, on_conflict="titulo").execute()
                    print(f"Task upserted: {title}")
                
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
