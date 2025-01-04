from datetime import datetime
import random
import time

import pandas as pd
import schedule

from JobSpy.src.jobspy import Site
from JobSpy.src.jobspy import scrape_jobs
from JobSpy.src.jobspy.scrapers.utils import create_logger
from email_manager import send_email
from html_render import create_job_card, get_html_template
from llm import validate_job_title
from proxy_scraper import get_valid_proxies

logger = create_logger("main")


def find_jobs(site, search_term, location, prox_list):
    jobs = scrape_jobs(
        site_name=site,
        search_term=search_term,
        radius=15,
        google_search_term=f"{search_term} in {location}",
        location=location,
        results_wanted=20,
        hours_old=120,
        country_indeed='germany',
        proxies=prox_list,
        enforce_annual_salary=True
    )
    return jobs


def process_site_jobs(site, search_term, location, proxies):
    """Process job scraping for a single site, retry with different proxies if needed, and return a DataFrame."""
    max_retries = len(proxies)
    proxies_iter = iter(proxies)
    retries = 0

    while retries < max_retries:
        try:
            return find_jobs(site, search_term, location, next(proxies_iter))
        except Exception as err:
            logger.error(f"Exception while processing {site}: {err}")
            retries += 1
            logger.error(f"Retrying {retries}/{max_retries} with a new proxy...")
            time.sleep(random.randint(1, 5))  # Short wait before retrying
    return pd.DataFrame()  # Return an empty DataFrame if all retries fail


def preprocess_job(row, today):
    row['new_badge'] = row['date_posted'] == today
    row['has_salary'] = row.get('min_amount') or row.get('max_amount')
    return row


def process_and_notify_jobs(search_term, location, email):
    """Process job searches across sites and send notification email."""
    proxies = get_valid_proxies(['socks5'], 200, 2)
    if not proxies:
        raise Exception("Not enough proxies available.")

    time.sleep(10)  # Initial delay for proxy availability

    all_found_jobs = pd.DataFrame()

    for site in [Site.LINKEDIN, Site.INDEED, Site.GOOGLE]:
        found_jobs = process_site_jobs(site, search_term, location, proxies)
        all_found_jobs = pd.concat([all_found_jobs, found_jobs], ignore_index=True)
        time.sleep(random.randint(5, 10))

    if not all_found_jobs.empty:
        # Filter and render job listings
        filtered_jobs = all_found_jobs[
            all_found_jobs['title'].apply(lambda title: validate_job_title(title, search_term))]
        today = datetime.today().strftime('%Y-%m-%d')
        filtered_jobs_with_html_tags = filtered_jobs.apply(lambda row: preprocess_job(row, today), axis=1)
        html_content = ''.join(filtered_jobs_with_html_tags.apply(create_job_card, axis=1))
        html_template = get_html_template(html_content)
        send_email(html_template, email, is_html=True)
    else:
        logger.error("No jobs found based on the criteria.")


if __name__ == "__main__":
    schedule.every().day.at("16:00").do(
        lambda: process_and_notify_jobs())

    # Keep the script running
    while True:
        schedule.run_pending()
        time.sleep(60 * 60)
