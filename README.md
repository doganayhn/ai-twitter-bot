# AI X (Twitter) Curation Bot 🤖

An automated AI-powered agent that fetches the latest tweets about AI, filters out hype/noise, and uses Google Gemini to curate and publish high-quality, informative threads to an X (Twitter) account.

## Features
- **Automated Data Gathering.** Uses Apify's Twitter Scraper to safely read timelines and search terms without expensive X API limits.
- **Smart AI Curation.** Passes tweets through a highly optimized system prompt using `gemini-2.5-flash` to evaluate if a topic is genuinely "worth covering" based on strict editorial standards (no memes, jokes, or low-effort hype).
- **Automated Publishing.** Uses `tweepy` to publish the AI's curated summary natively as a Tweet (or Thread) to an X account.
- **Daily Cron.** Includes a `.github/workflows/daily_cron.yml` to automatically run the bot every day for free using GitHub Actions.

## Setup
1. Clone the repository.
2. Initialize virtual environment: `py -m venv .venv` and activate it.
3. Install dependencies: `pip install -r requirements.txt`
4. Rename `.env.example` to `.env` and fill in your API keys (X API, Apify, Gemini).
5. Run locally via `py main.py` or let GitHub Actions run it daily.
