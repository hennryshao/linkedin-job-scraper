from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time
import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime, timedelta
import uuid

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Use environment variables for LinkedIn credentials and API key
LINKEDIN_EMAIL = os.getenv("LINKEDIN_EMAIL", "henryshao2020@gmail.com")
LINKEDIN_PASSWORD = os.getenv("LINKEDIN_PASSWORD", "10shaoyan-")
API_KEY = os.getenv("API_KEY", str(uuid.uuid4()))  # Generate a random API key if not set
print(f"当前 API Key: {API_KEY}")  # 打印 API Key 用于调试

# Rate limiting configuration
MAX_REQUESTS_PER_HOUR = 10
request_history = {}

def check_rate_limit(api_key):
    """Check if the API key has exceeded rate limits"""
    now = datetime.now()
    one_hour_ago = now - timedelta(hours=1)
    
    # Clean up old requests
    for key in list(request_history.keys()):
        request_history[key] = [time for time in request_history[key] if time > one_hour_ago]
    
    # Check current API key's request count
    if api_key not in request_history:
        request_history[api_key] = []
    
    if len(request_history[api_key]) >= MAX_REQUESTS_PER_HOUR:
        return False
    
    request_history[api_key].append(now)
    return True

# Configure ChromeDriver with enhanced stability
def get_chrome_options():
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--remote-debugging-port=9222")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)
    
    # Additional options for Render deployment
    if os.getenv("RENDER"):
        chrome_options.binary_location = os.getenv("CHROME_BIN", "/usr/bin/google-chrome")
    
    return chrome_options

def login_linkedin():
    """Login to LinkedIn and return the logged-in WebDriver"""
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=get_chrome_options())
        driver.get("https://www.linkedin.com/login")
        
        time.sleep(3)  # Wait for page load

        # Enter email
        email_input = driver.find_element(By.ID, "username")
        email_input.send_keys(LINKEDIN_EMAIL)

        # Enter password
        password_input = driver.find_element(By.ID, "password")
        password_input.send_keys(LINKEDIN_PASSWORD)
        password_input.send_keys(Keys.RETURN)

        time.sleep(5)  # Wait for redirect
        return driver
    except Exception as e:
        print(f" LinkedIn login failed: {e}")
        if 'driver' in locals():
            driver.quit()
        return None

def scrape_jobs(job_title, location):
    """Scrape job information from LinkedIn"""
    driver = login_linkedin()
    if driver is None:
        return {"error": "Login failed, cannot scrape jobs"}

    try:
        search_url = f"https://www.linkedin.com/jobs/search?keywords={job_title}&location={location}&f_E=1"
        driver.get(search_url)

        time.sleep(5)  # Wait for content to load

        jobs = []
        job_cards = driver.find_elements(By.CLASS_NAME, "base-card")

        for job in job_cards[:5]:  # Only scrape first 5 jobs
            try:
                title = job.find_element(By.CLASS_NAME, "base-card__full-link").text
                company = job.find_element(By.CLASS_NAME, "base-search-card__subtitle").text
                location = job.find_element(By.CLASS_NAME, "job-search-card__location").text
                link = job.find_element(By.CLASS_NAME, "base-card__full-link").get_attribute("href")

                jobs.append({
                    "title": title,
                    "company": company,
                    "location": location,
                    "link": link
                })
            except Exception as e:
                print(f" Skipping job due to error: {e}")
                continue

        return jobs
    except Exception as e:
        print(f" Scraping failed: {e}")
        return {"error": "Scraping failed due to unexpected error"}
    finally:
        if driver:
            driver.quit()  # Ensure browser is always closed

@app.route('/scrape', methods=['GET'])
def scrape():
    try:
        # Get request parameters
        job_title = request.args.get("job_title")
        location = request.args.get("location")
        api_key = request.args.get("api_key")

        # Validate required parameters
        if not job_title or not location:
            return jsonify({"error": "Missing job_title or location"}), 400
        
        # Check API key
        if not api_key or api_key != API_KEY:
            return jsonify({"error": "Invalid or missing API key"}), 403

        # Check rate limit
        if not check_rate_limit(api_key):
            return jsonify({
                "error": "Rate limit exceeded",
                "message": f"Maximum {MAX_REQUESTS_PER_HOUR} requests per hour allowed"
            }), 429

        jobs = scrape_jobs(job_title, location)
        return jsonify(jobs)
    except Exception as e:
        return jsonify({"error": f"Server error: {str(e)}"}), 500

@app.route('/get-api-key', methods=['GET'])
def get_api_key():
    return jsonify({"api_key": API_KEY})

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
