import os
import time
from playwright.sync_api import sync_playwright

USER_DATA_DIR = "browser_context"

class NotebookLMBot:
    def __init__(self, headless=False):
        self.headless = headless

    def create_notebook_and_add_source(self, video_url):
        with sync_playwright() as p:
            # browser = p.chromium.launch(headless=self.headless)
            # Use launch_persistent_context to keep cookies/login
            # Try to connect to an existing Chrome instance on port 9222
            try:
                print("Connecting to existing Chrome instance on port 9222...")
                browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
                context = browser.contexts[0]
                page = context.new_page()
            except Exception as e:
                print(f"Could not connect to Chrome: {e}")
                print("Please make sure Chrome is running with --remote-debugging-port=9222")
                return False
            
            try:
                print("Navigating to NotebookLM...")
                page.goto("https://notebooklm.google.com/")
                
                # Check if logged in. If "Sign in" button exists, we need auth
                # Simple check: look for "New Notebook" or specific text.
                # If redirection to accounts.google.com happens, we need user intervention.
                
                # Wait for potential load
                time.sleep(3)
                
                if "accounts.google.com" in page.url:
                    print("Login required! Please log in to your Google Account in the browser window.")
                    print("Waiting for you to complete login...")
                    # Wait indefinitely or loop until redirected back
                    page.wait_for_url("https://notebooklm.google.com/**", timeout=0) 
                    print("Login detected. Proceeding...")

                # 1. Create New Notebook
                print("Creating new notebook...")
                # Button labels to try
                labels = [ "Crear cuaderno", "New notebook", "Nuevo","New Notebook", "Nuevo cuaderno"]
                
                clicked = False
                for label in labels:
                    try:
                        print(f"Looking for button: '{label}'")
                        # Use exact=False for partial matches (like "Crear nuevo cuaderno" if it changed)
                        page.get_by_text(label, exact=False).first.click(timeout=3000)
                        clicked = True
                        print(f"Clicked '{label}'")
                        break
                    except:
                        continue
                
                if not clicked:
                    print("Could not find 'New Notebook' button. Trying generic selector...")
                    # Fallback: look for a big div with role button or class that looks like a card
                    # This is risky but a last resort.
                    # As a backup, print the page content to debug? (Too much output)
                    raise Exception("Could not find create notebook button")
                
                # Wait for notebook to load. URL changes to /notebook/<id>
                page.wait_for_url("**/notebook/**")
                
                # 2. Add Source
                print(f"Adding source: {video_url}")
                
                # Try clicking YouTube first
                try:
                    page.locator("text=YouTube").click(timeout=3000)
                except:
                    # If failed, maybe we are already in the "Add source" state or it's named differently
                    print("Could not click YouTube source button, trying to find input directly...")

                time.sleep(1) # Wait for animation

                # Try to fill input using multiple strategies
                input_filled = False
                
                # List of potential placeholders or labels
                placeholders = [
                    "Pega los enlaces", 
                    "Paste YouTube URL", 
                    "Pegar URL", 
                    "youtube.com", 
                    "http",
                    "Enlace"
                ]
                
                for ph in placeholders:
                    try:
                        print(f"Trying input with placeholder matching '{ph}'...")
                        page.get_by_placeholder(ph, exact=False).fill(video_url)
                        input_filled = True
                        print("Input filled successfully.")
                        break
                    except:
                        continue
                
                if not input_filled:
                    print("Placeholder strategy failed. Trying generic inputs...")
                    try:
                        # Try the first text input visible
                        page.locator("input[type='text']").first.fill(video_url)
                        input_filled = True
                        print("Filled first generic text input.")
                    except:
                        print("Could not fill any input.")

                # Click Insert/Add
                # Try multiple button texts
                insert_buttons = ["Insertar", "Insert", "Añadir", "Agregar"]
                clicked_insert = False
                for btn_text in insert_buttons:
                    try:
                        page.get_by_text(btn_text, exact=True).click(timeout=2000)
                        clicked_insert = True
                        print(f"Clicked '{btn_text}'")
                        break
                    except:
                        continue
                
                if not clicked_insert:
                     # Try finding a button with an icon or generic button in the dialog
                     print("Could not find specific Insert button. Trying generic submit...")
                     # page.locator("button[type='submit']").click() # Risky
                
                # Wait for processing?
                # Usually it takes a few seconds. We can verify if the source appears in list.
                print("Source added (hopefully). Waiting 10s for stability/processing...")
                time.sleep(10)
                
                # 3. Click "Infografía"
                # The button appears after the source is fully processed. This varies by video length.
                print("Waiting for 'Infografía' button to appear...")
                
                # Retry loop for up to 30 seconds
                for i in range(6):
                    try:
                        print(f"Attempt {i+1}/6 to find 'Infografía'...")
                        # Look for button with text "Infografía" or "Infographic"
                        # Use first to avoid ambiguity if multiple exist
                        page.get_by_text("Infograf", exact=False).first.click(timeout=5000)
                        print("Clicked 'Infografía' successfully.")
                        break
                    except:
                        if i < 5:
                            print("Button not found yet, waiting 5s...")
                            time.sleep(5)
                        else:
                            print("Could not find or click 'Infografía' button after 30s.")
                            # We don't fail the whole process, just log it.
                            pass
                
                # Optional: Wait a bit to ensure the click registered
                time.sleep(2)

                return True

            except Exception as e:
                print(f"An error occurred: {e}")
                import traceback
                traceback.print_exc()
                # Keep browser open if not headless for debugging?
                return False
            finally:
                context.close()

if __name__ == "__main__":
    # Test
    bot = NotebookLMBot(headless=False)
    # Use a safe test video
    bot.create_notebook_and_add_source("https://www.youtube.com/watch?v=jNQXAC9IVRw")
