# LinkedIn Job Scraper API

A secure Flask API that scrapes job listings from LinkedIn using Selenium.

## Features

- Secure API key authentication
- Rate limiting (10 requests per hour)
- Headless Chrome browser support
- Error handling and logging
- CORS enabled

## API Endpoints

### GET /scrape
Scrapes job listings from LinkedIn.

**Parameters:**
- `job_title` (required): The job title to search for
- `location` (required): The location to search in
- `api_key` (required): Your API key for authentication

**Example Request:**
```
https://your-app.onrender.com/scrape?job_title=Software%20Engineer&location=New%20York&api_key=your-api-key
```

## Deployment

This API is designed to be deployed on Render.com.

### Environment Variables Required:
- `LINKEDIN_EMAIL`: Your LinkedIn account email
- `LINKEDIN_PASSWORD`: Your LinkedIn account password
- `API_KEY`: Your chosen API key for authentication

## Local Development

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set environment variables:
```bash
export LINKEDIN_EMAIL="your-email@example.com"
export LINKEDIN_PASSWORD="your-password"
export API_KEY="your-api-key"
```

3. Run the server:
```bash
python linkedin_scraper.py
```

## Security Notes

- The API is protected by an API key
- Rate limiting is enforced to prevent abuse
- Credentials are stored in environment variables
- CORS is enabled for cross-origin requests
