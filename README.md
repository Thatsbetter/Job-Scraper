# Job-Scraper

A web application and job scraping tool that helps users find relevant job opportunities based on their preferences.

## Overview

The Job-Scraper project consists of a Flask-based web application and a job scraping component. Users can register their job search preferences (position, location, job type) through the web application. The scraping tool then periodically searches various job sites (LinkedIn, Indeed, Google) for matching job postings and sends email notifications to the users with the new opportunities.

## Features

*   **User Registration:** Users can specify their desired job position, location, and job type.
*   **Job Scraping:** Scrapes job postings from LinkedIn, Indeed, and Google.
*   **Email Notifications:** Sends email notifications to users when new job opportunities matching their preferences are found.
*   **Job Filtering:** Filters job postings based on relevance to user's specified position.
*   **Welcome Email:** Sends a welcome email to new users upon registration.

## Architecture

The project includes the following main components:

*   **Flask Web Application (app.py):**
    *   Handles user registration and preference storage.
    *   Provides API endpoints for adding and deleting users.
    *   Uses Flask-CORS to handle Cross-Origin Resource Sharing.
*   **Job Scraping Tool (main.py):**
    *   Scrapes job postings from various job sites using the `JobSpy` library.
    *   Filters job postings based on user preferences and relevance.
    *   Sends email notifications to users using the `email_manager` module.
    *   Uses `schedule` to run the scraping and notification tasks periodically.
*   **Database (db/database\_service.py, db/models.py):**
    *   Stores user information and email history.
    *   Uses SQLAlchemy for database interactions.
    *   Uses Flask-Migrate for database migrations.
*   **Email Management (email\_manager.py):**
    *   Handles sending emails using SMTP.
*   **HTML Rendering (html\_render.py):**
    *   Generates HTML content for job postings and email notifications.
*   **LLM Integration (llm.py):**
    *   Uses a Language Model to validate job titles and locations for better accuracy.
*   **Configuration (credential.py):**
    *   Manages sensitive information like database URI.

## Requirements

*   Python 3.10+
*   Flask
*   Flask-CORS
*   SQLAlchemy
*   Flask-Migrate
*   pandas
*   schedule
*   JobSpy
*   python-dotenv

## Setup

1.  **Clone the repository:**

    ```bash
    git clone https://github.com/Thatsbetter/Job-Scraper.git
    cd Job-Scraper
    ```

2.  **Create a virtual environment:**

    ```bash
    python -m venv venv
    source venv/bin/activate  # On Linux/macOS
    venv\Scripts\activate  # On Windows
    ```

3.  **Install dependencies:**

    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure the database:**

    *   Set up a PostgreSQL database.
    *   Create a `.env` file with the following variables, replacing the values with your actual database credentials:

        ```
        DATABASE_USERNAME=<your_database_username>
        DATABASE_PASSWORD=<your_database_password>
        DATABASE_HOST=<your_database_host>
        DATABASE_PORT=<your_database_port>
        DATABASE_NAME=<your_database_name>
        ```

5.  **Run database migrations:**

    ```bash
    flask db init
    flask db migrate -m "Initial migration"
    flask db upgrade
    ```

6.  **Configure email settings:**

    *   Set up a gmail account for sending notifications.
    *   Update the .env file with your email credentials.

7.  **Run the application:**

    ```bash
    python main.py & python app.py
    ```

## Usage

1.  Use request in python or postman to create a user.
3.  The job scraper will run periodically (every day at 10:45) and send you email notifications when new job opportunities are found.

## Acknowledgments

The JobSpy package used in this project is based on the [cullenwatson/JobSpy](https://github.com/cullenwatson/JobSpy) repository.
