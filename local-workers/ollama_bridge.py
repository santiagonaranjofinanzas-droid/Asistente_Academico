import http.server
import json
import subprocess
import time
import threading
import requests
import os
import signal

PORT = 11435
OLLAMA_API = "http://127.0.0.1:11434/api/generate"
IDLE_TIMEOUT = 60 # Seconds before shutting down Ollama
last_activity = 0
ollama_process = None

def is_ollama_running():
    try:
        response = requests.get("http://127.0.0.1:11434/", timeout=1)
        return response.status_code == 200
    except:
        return False

def start_ollama():
    global ollama_process
    if not is_ollama_running():
        print("Starting Ollama serve...")
        # Use START to run it detached on Windows
        ollama_process = subprocess.Popen(["ollama", "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        # Wait for it to be ready
        for _ in range(10):
            if is_ollama_running():
                print("Ollama is ready.")
                return True
            time.sleep(1)
        return False
    return True

def stop_ollama():
    global ollama_process
    print("Stopping Ollama to save resources...")
    # On Windows, taskkill is more reliable for background processes
    subprocess.run(["taskkill", "/F", "/IM", "ollama.exe"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    ollama_process = None

def idle_monitor():
    global last_activity
    while True:
        time.sleep(10)
        if last_activity > 0 and (time.time() - last_activity) > IDLE_TIMEOUT:
            if is_ollama_running():
                stop_ollama()
                last_activity = 0

class OllamaBridgeHandler(http.server.BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_POST(self):
        global last_activity
        if self.path == '/summarize':
            last_activity = time.time()
            
            # Start Ollama demand
            if not start_ollama():
                self.send_error(500, "Failed to start Ollama")
                return

            # Read request body
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            try:
                # Proxy to real Ollama
                print("Proxying request to Ollama...")
                response = requests.post(OLLAMA_API, data=post_data, timeout=60)
                
                self.send_response(200)
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(response.content)
                
                # Update last activity
                last_activity = time.time()
            except Exception as e:
                print(f"Error proxying: {e}")
                self.send_error(500, str(e))
        else:
            self.send_error(404)

    def log_message(self, format, *args):
        return # Concise logs

def run_bridge():
    # Start idle monitor thread
    monitor_thread = threading.Thread(target=idle_monitor, daemon=True)
    monitor_thread.start()
    
    server = http.server.HTTPServer(('127.0.0.1', PORT), OllamaBridgeHandler)
    print(f"Ollama Automation Bridge running on http://127.0.0.1:{PORT}")
    server.serve_forever()

if __name__ == "__main__":
    run_bridge()
