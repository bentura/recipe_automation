# AutoChef Data Pipeline

## Description
The **AutoChef Data Pipeline** is a robust, Dockerized automation solution designed to bridge the gap between your physical recipe collection and your digital recipe management system. Say goodbye to manual data entry! This pipeline intelligently processes scanned recipes (JPGs, PDFs), extracts all key information, validates it, and transforms it into structured JSON, ready for seamless integration.

## Key Features:

* **Intelligent Input Monitoring:** Watches a designated network folder (`data/input`) for new recipe images or PDFs, triggering automated processing.
* **High-Accuracy OCR:** Utilizes **Google Cloud Vision AI** (or a self-hosted Ollama LLM) for superior text extraction, accurately handling diverse fonts, layouts, and image qualities.
* **AI-Powered Semantic Parsing:** Employs a Large Language Model (Google Gemini or self-hosted Ollama) to understand the recipe content, generating highly structured JSON in two formats:
    * **Standard Schema.org Recipe JSON-LD:** For web compatibility and general-purpose recipe data.
    * **Custom Internal JSON:** Tailored precisely to your specific recipe management system's schema, ensuring compatibility with your downstream applications.
* **Granular Data Extraction:** Extracts detailed recipe components, including:
    * Recipe Name & Description
    * Categorized Keywords
    * **Intelligent Step Splitting:** Breaks down instructions into distinct, logical, and concise steps, even from complex paragraphs.
    * **Detailed Ingredient Parsing:** Extracts food name, unit, amount, and notes for each ingredient, nested within its relevant step.
* **Robust Data Validation & Post-Processing:**
    * Applies custom logic to validate and refine generated data (e.g., ensuring numerical amounts, handling specific text limits for fields like servings).
    * **Culinary Anomaly Detection:** Utilizes built-in culinary knowledge to identify and flag potentially unusual ingredient amounts (e.g., a tablespoon of cayenne pepper), sending alerts via Pushover for human review.
* **Automated API Integration:** Automatically `POST`s the processed custom JSON directly to your specified REST API endpoint with Basic Authentication, pushing recipes straight into your system.
* **Real-time Notifications:** Provides instant status updates and warnings via **Pushover**, keeping you informed of successes, failures, and detected anomalies.
* **Persistent Logging & Web Interface:** All processing activities, successes, and errors are meticulously logged to persistent files, easily monitored through a simple, auto-refreshing web UI dashboard.
* **Dockerized Deployment:** Designed for easy setup, portability, and consistent operation across environments using `docker-compose`.
