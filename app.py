from flask import Flask, request, jsonify
from flask_cors import CORS
from playwright.sync_api import sync_playwright
import time
import os
import uuid
import logging
from datetime import datetime, timedelta

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Use environment variables for credentials and API key
LINKEDIN_EMAIL = os.getenv("LINKEDIN_EMAIL", "henryshao2020@gmail.com")
LINKEDIN_PASSWORD = os.getenv("LINKEDIN_PASSWORD", "10shaoyan-")
API_KEY = os.getenv("API_KEY", str(uuid.uuid4()))
logger.info(f"当前 API Key: {API_KEY}")
logger.info(f"当前环境变量: {os.environ}")

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

def login_linkedin():
    """Login to LinkedIn and return the browser context"""
    try:
        logger.info("开始初始化 Playwright...")
        playwright = sync_playwright().start()
        
        logger.info("配置浏览器选项...")
        browser = playwright.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--window-size=1920,1080"
            ]
        )
        
        logger.info("创建浏览器上下文...")
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36"
        )
        page = context.new_page()
        
        logger.info("导航到 LinkedIn 登录页面...")
        page.goto("https://www.linkedin.com/login")
        
        logger.info("输入登录信息...")
        page.fill("#username", LINKEDIN_EMAIL)
        page.fill("#password", LINKEDIN_PASSWORD)
        
        logger.info("点击登录按钮...")
        page.click("button[type=submit]")
        
        logger.info("等待导航完成...")
        page.wait_for_selector("nav.global-nav", timeout=15000)
        
        logger.info("登录成功！")
        return {"playwright": playwright, "browser": browser, "page": page}
    except Exception as e:
        logger.error(f"LinkedIn 登录失败: {str(e)}")
        logger.error(f"错误类型: {type(e)}")
        logger.error(f"错误详情: {e.__dict__}")
        if 'browser' in locals():
            browser.close()
        if 'playwright' in locals():
            playwright.stop()
        return None

def scrape_jobs(job_title, location):
    """Scrape job information from LinkedIn"""
    logger.info(f"开始抓取职位信息: {job_title} in {location}")
    browser_ctx = login_linkedin()
    if browser_ctx is None:
        logger.error("登录失败，无法抓取职位")
        return {"error": "Login failed, cannot scrape jobs"}

    try:
        page = browser_ctx["page"]
        search_url = f"https://www.linkedin.com/jobs/search?keywords={job_title}&location={location}&f_E=1"
        logger.info(f"导航到搜索页面: {search_url}")
        page.goto(search_url)
        
        logger.info("等待职位列表加载...")
        page.wait_for_selector(".jobs-search__results-list", timeout=10000)

        jobs = []
        logger.info("查找职位卡片...")
        job_cards = page.query_selector_all(".jobs-search__results-list li")
        logger.info(f"找到 {len(job_cards)} 个职位卡片")

        for index, job in enumerate(job_cards[:5]):
            try:
                logger.info(f"正在处理第 {index + 1} 个职位...")
                title_elem = job.query_selector(".base-card__full-link")
                company_elem = job.query_selector(".base-search-card__subtitle")
                location_elem = job.query_selector(".job-search-card__location")

                jobs.append({
                    "title": title_elem.inner_text() if title_elem else "N/A",
                    "company": company_elem.inner_text() if company_elem else "N/A",
                    "location": location_elem.inner_text() if location_elem else "N/A",
                    "link": title_elem.get_attribute("href") if title_elem else "#"
                })
                logger.info(f"成功处理第 {index + 1} 个职位")
            except Exception as e:
                logger.error(f"处理职位时出错: {e}")
                continue

        logger.info(f"成功抓取 {len(jobs)} 个职位")
        return jobs
    except Exception as e:
        logger.error(f"抓取失败: {str(e)}")
        logger.error(f"错误类型: {type(e)}")
        logger.error(f"错误详情: {e.__dict__}")
        return {"error": "Scraping failed due to unexpected error"}
    finally:
        if browser_ctx:
            logger.info("清理浏览器资源...")
            browser_ctx["browser"].close()
            browser_ctx["playwright"].stop()

@app.route('/')
def home():
    return jsonify({
        "status": "API is running",
        "endpoints": [
            {
                "path": "/get-api-key",
                "method": "GET",
                "description": "Get the API key"
            },
            {
                "path": "/scrape",
                "method": "GET",
                "params": ["job_title", "location", "api_key"],
                "description": "Scrape job listings from LinkedIn"
            }
        ]
    })

@app.route('/get-api-key', methods=['GET'])
def get_api_key():
    return jsonify({"api_key": API_KEY})

@app.route('/scrape', methods=['GET'])
def scrape():
    try:
        logger.info("收到抓取请求")
        # Get request parameters
        job_title = request.args.get("job_title")
        location = request.args.get("location")
        api_key = request.args.get("api_key")

        logger.info(f"请求参数: job_title={job_title}, location={location}")

        # Validate required parameters
        if not job_title or not location:
            logger.error("缺少必要参数")
            return jsonify({"error": "Missing job_title or location"}), 400
        
        # Check API key
        if not api_key or api_key != API_KEY:
            logger.error("API key 无效")
            return jsonify({"error": "Invalid or missing API key"}), 403

        # Check rate limit
        if not check_rate_limit(api_key):
            logger.error("超出速率限制")
            return jsonify({
                "error": "Rate limit exceeded",
                "message": f"Maximum {MAX_REQUESTS_PER_HOUR} requests per hour allowed"
            }), 429

        logger.info("开始抓取职位...")
        jobs = scrape_jobs(job_title, location)
        logger.info("抓取完成")
        return jsonify(jobs)
    except Exception as e:
        logger.error(f"服务器错误: {str(e)}")
        logger.error(f"错误类型: {type(e)}")
        logger.error(f"错误详情: {e.__dict__}")
        return jsonify({"error": f"Server error: {str(e)}"}), 500

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
