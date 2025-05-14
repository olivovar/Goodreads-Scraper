# Goodreads Scraper

A Python-based scraper that collects book reviews and metadata from Goodreads using both static and dynamic scraping techniques. Built as part of a research co-op trial at the BACSS Lab, the scraper processes hundreds of books and tens of thousands of user reviews with reliability, efficiency, and ethical design.

---

## Features

- Matches books from a list using fuzzy title-author comparison
- Dynamically scrapes up to 100 user reviews per book
- Extracts reviewer ID, rating, date, text, upvotes, comments, and tags
- Saves output to a cumulative CSV file that supports pause/resume
- Logs missing data, handles pagination, and deduplicates reviews
- Resilient to login timeouts, missing buttons, and dynamic content loading

---

## Project Structure

```
Goodreads-Scraper/
├── scraperGoodreads.py        # Main scraping script
├── data/
│   ├── goodreads_list.csv     # Book list input
│   └── reviews_output.csv     # Review data output
├── docs/
│   └── Goodreads_Scraper_Task.pdf  # Methodology write-up
├── requirements.txt
├── .gitignore
└── README.md
```

---

## Getting Started

### 1. Clone the repo

```bash
git clone https://github.com/olivovar/Goodreads-Scraper.git
cd Goodreads-Scraper
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Prepare input data

Update `data/goodreads_list.csv` with your list of books (title, author, book ID).

### 4. Run the scraper

```bash
python scraperGoodreads.py
```

Reviews will be saved incrementally in `data/reviews_output.csv`.

---

## Methodology Summary

The scraper uses **fuzzy string matching** (via `rapidfuzz`) to identify the correct Goodreads page for each book. It filters out irrelevant results (e.g., summaries or guides) and navigates through paginated reviews using **Selenium** with waits and scroll events to handle dynamic content.

Progress is saved after every book, allowing the script to resume seamlessly even after interruptions. Duplicate reviews are avoided using reviewer IDs, and books that cannot be matched or scraped are logged and skipped.

For more detail, see the full [methodology write-up](docs/Goodreads_Scraper_Task.pdf).

---

## GenAI Usage

Generative AI (ChatGPT) was used in early stages to:
- Interpret dynamic HTML structure and identify selectors
- Refine architectural strategies for robustness and resumability
- Debug Selenium/browser session issues

As development progressed, AI was used less for low-level scraping and more as a second-opinion tool for improving reliability, efficiency, and design.

---

## Future Improvements

- Parallelization for faster scraping
- Enhanced exception logging and summary reporting
- Support for scraping ratings without reviews

---

## Author

**Olivia Pivovar**  
📍 Boston, MA  
[GitHub](https://github.com/olivovar) | [LinkedIn](https://linkedin.com/in/oliviapivovar)

---

## ⚠Disclaimer

This project is for **educational and research purposes only**. Always consult Goodreads' [robots.txt](https://www.goodreads.com/robots.txt) and terms of use before running any scraper.
