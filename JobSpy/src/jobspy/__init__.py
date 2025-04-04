from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Tuple

import pandas as pd

from .jobs import JobType, Location
from .scrapers import SalarySource, ScraperInput, Site, JobResponse, Country
from .scrapers.exceptions import (
    LinkedInException,
    IndeedException,
    ZipRecruiterException,
    GlassdoorException,
    GoogleJobsException,
)
from .scrapers.glassdoor import GlassdoorScraper
from .scrapers.google import GoogleJobsScraper
from .scrapers.indeed import IndeedScraper
from .scrapers.linkedin import LinkedInScraper
from .scrapers.utils import set_logger_level, extract_salary, create_logger,get_enum_from_job_type
from .scrapers.ziprecruiter import ZipRecruiterScraper


def scrape_jobs(
    site_name: str | list[str] | Site | list[Site] | None = None,
    search_term: str | None = None,
    google_search_term: str | None = None,
    location: str | None = None,
    distance: int | None = 50,
    is_remote: bool = False,
    job_type: str | None = None,
    easy_apply: bool | None = None,
    results_wanted: int = 15,
    country_indeed: str = "usa",
    hyperlinks: bool = False,
    proxies: list[str] | str | None = None,
    ca_cert: str | None = None,
    description_format: str = "markdown",
    linkedin_fetch_description: bool | None = False,
    linkedin_company_ids: list[int] | None = None,
    offset: int | None = 0,
    hours_old: int = None,
    enforce_annual_salary: bool = False,
    verbose: int = 2,
    **kwargs,
) -> pd.DataFrame:
    """
    Simultaneously scrapes job data from multiple job sites.
    :return: pandas dataframe containing job data
    """
    SCRAPER_MAPPING = {
        Site.LINKEDIN: LinkedInScraper,
        Site.INDEED: IndeedScraper,
        Site.ZIP_RECRUITER: ZipRecruiterScraper,
        Site.GLASSDOOR: GlassdoorScraper,
        Site.GOOGLE: GoogleJobsScraper,
    }
    set_logger_level(verbose)

    def map_str_to_site(site_name: str) -> Site:
        return Site[site_name.upper()]


    job_type = get_enum_from_job_type(job_type)

    def get_site_type():
        site_types = list(Site)
        if isinstance(site_name, str):
            site_types = [map_str_to_site(site_name)]
        elif isinstance(site_name, Site):
            site_types = [site_name]
        elif isinstance(site_name, list):
            site_types = [
                map_str_to_site(site) if isinstance(site, str) else site
                for site in site_name
            ]
        return site_types

    country_enum = Country.from_string(country_indeed)

    scraper_input = ScraperInput(
        site_type=get_site_type(),
        country=country_enum,
        search_term=search_term,
        google_search_term=google_search_term,
        location=location,
        distance=distance,
        is_remote=is_remote,
        job_type=job_type,
        easy_apply=easy_apply,
        description_format=description_format,
        linkedin_fetch_description=linkedin_fetch_description,
        results_wanted=results_wanted,
        linkedin_company_ids=linkedin_company_ids,
        offset=offset,
        hours_old=hours_old,
    )

    def scrape_site(site: Site) -> Tuple[str, JobResponse]:
        scraper_class = SCRAPER_MAPPING[site]
        scraper = scraper_class(proxies=proxies, ca_cert=ca_cert)
        scraped_data: JobResponse = scraper.scrape(scraper_input)
        cap_name = site.value.capitalize()
        site_name = "ZipRecruiter" if cap_name == "Zip_recruiter" else cap_name
        create_logger(site_name).info(f"finished scraping")
        return site.value, scraped_data

    site_to_jobs_dict = {}

    def worker(site):
        site_val, scraped_info = scrape_site(site)
        return site_val, scraped_info

    with ThreadPoolExecutor() as executor:
        future_to_site = {
            executor.submit(worker, site): site for site in scraper_input.site_type
        }

        for future in as_completed(future_to_site):
            site_value, scraped_data = future.result()
            site_to_jobs_dict[site_value] = scraped_data

    def convert_to_annual(job_data: dict):
        if job_data["interval"] == "hourly":
            job_data["min_amount"] *= 2080
            job_data["max_amount"] *= 2080
        if job_data["interval"] == "monthly":
            job_data["min_amount"] *= 12
            job_data["max_amount"] *= 12
        if job_data["interval"] == "weekly":
            job_data["min_amount"] *= 52
            job_data["max_amount"] *= 52
        if job_data["interval"] == "daily":
            job_data["min_amount"] *= 260
            job_data["max_amount"] *= 260
        job_data["interval"] = "yearly"

    jobs_dfs: list[pd.DataFrame] = []

    for site, job_response in site_to_jobs_dict.items():
        for job in job_response.jobs:
            job_data = job.dict()
            job_url = job_data["job_url"]
            job_data["job_url_hyper"] = f'<a href="{job_url}">{job_url}</a>'
            job_data["site"] = site
            job_data["company"] = job_data["company_name"]
            job_data["job_type"] = (
                ", ".join(job_type.value[0] for job_type in job_data["job_type"])
                if job_data["job_type"]
                else None
            )
            job_data["emails"] = (
                ", ".join(job_data["emails"]) if job_data["emails"] else None
            )
            if job_data["location"]:
                job_data["location"] = Location(
                    **job_data["location"]
                ).display_location()

            compensation_obj = job_data.get("compensation")
            if compensation_obj and isinstance(compensation_obj, dict):
                job_data["interval"] = (
                    compensation_obj.get("interval").value
                    if compensation_obj.get("interval")
                    else None
                )
                job_data["min_amount"] = compensation_obj.get("min_amount")
                job_data["max_amount"] = compensation_obj.get("max_amount")
                job_data["currency"] = compensation_obj.get("currency", "USD")
                job_data["salary_source"] = SalarySource.DIRECT_DATA.value
                if enforce_annual_salary and (
                    job_data["interval"]
                    and job_data["interval"] != "yearly"
                    and job_data["min_amount"]
                    and job_data["max_amount"]
                ):
                    convert_to_annual(job_data)

            else:
                if country_enum == Country.USA:
                    (
                        job_data["interval"],
                        job_data["min_amount"],
                        job_data["max_amount"],
                        job_data["currency"],
                    ) = extract_salary(
                        job_data["description"],
                        enforce_annual_salary=enforce_annual_salary,
                    )
                    job_data["salary_source"] = SalarySource.DESCRIPTION.value

            job_data["salary_source"] = (
                job_data["salary_source"]
                if "min_amount" in job_data and job_data["min_amount"]
                else None
            )
            job_df = pd.DataFrame([job_data])
            jobs_dfs.append(job_df)

    if jobs_dfs:
        jobs_df = pd.concat(jobs_dfs, ignore_index=True)

        # Convert to datetime and handle NaT values when converting to date
        jobs_df['date_posted'] = pd.to_datetime(jobs_df['date_posted'], errors='coerce').dt.strftime('%Y-%m-%d')

        today = datetime.today().date()  # Get today's date in date format
        # Compare dates and handle NaT values
        jobs_df['new_badge'] = jobs_df['date_posted'].notna() & (jobs_df['date_posted'] == today)

        # Filter out all-NA columns from each DataFrame before concatenation
        filtered_dfs = [df.dropna(axis=1, how="all") for df in jobs_dfs]
        # Step 2: Concatenate the filtered DataFrames
        jobs_df = pd.concat(filtered_dfs, ignore_index=True)

        # Desired column order
        desired_order = [
            "id",
            "site",
            "job_url_hyper" if hyperlinks else "job_url",
            "job_url_direct",
            "title",
            "company",
            "location",
            "date_posted",
            "new_badge",
            "job_type",
            "salary_source",
            "interval",
            "has_salary",
            "min_amount",
            "max_amount",
            "currency",
            "is_remote",
            "job_level",
            "job_function",
            "listing_type",
            "emails",
            "description",
            "company_industry",
            "company_url",
            "company_logo",
            "company_url_direct",
            "company_addresses",
            "company_num_employees",
            "company_revenue",
            "company_description",
        ]

        # Step 3: Ensure all desired columns are present, adding missing ones as empty
        for column in desired_order:
            if column not in jobs_df.columns:
                jobs_df[column] = None  # Add missing columns as empty

        # Reorder the DataFrame according to the desired order
        jobs_df = jobs_df[desired_order]

        # Step 4: Sort the DataFrame as required
        return jobs_df.sort_values(
            by=["site", "date_posted"], ascending=[True, False]
        ).reset_index(drop=True)
    else:
        return pd.DataFrame()
