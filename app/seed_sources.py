from app.db import get_cursor

SOURCES = [
    ("The Guardian", "theguardian.com", "left"),
    ("The New Yorker", "newyorker.com", "left"),
    ("Vox", "vox.com", "left"),
    ("ABC News", "abcnews.go.com", "left"),
    ("CBS News", "cbsnews.com", "left"),
    ("CNN", "edition.cnn.com", "left"),
    ("NBC News", "nbcnews.com", "left"),
    ("The New York Times", "nytimes.com", "left"),
    ("The Washington Post", "washingtonpost.com", "left"),
    ("Time", "time.com", "left"),

    ("BBC News", "bbc.com", "center"),
    ("Forbes", "forbes.com", "center"),
    ("Bloomberg", "bloomberg.com", "center"),
    ("Axios", "axios.com", "center"),
    ("The Wall Street Journal", "wsj.com", "center"),
    ("The Hill", "thehill.com", "center"),
    ("MarketWatch", "marketwatch.com", "center"),
    ("USA Today", "usatoday.com", "center"),
    ("Newsweek", "newsweek.com", "center"),
    ("Reuters", "reuters.com", "center"),

    ("Daily Mail", "dailymail.co.uk", "right"),
    ("Fox News", "foxnews.com", "right"),
    ("CBN", "www1.cbn.com", "right"),
    ("Newsmax", "newsmax.com", "right"),
    ("New York Post", "nypost.com", "right"),
    ("The Washington Times", "washingtontimes.com", "right"),
    ("Washington Examiner", "washingtonexaminer.com", "right"),
    ("The Daily Wire", "dailywire.com", "right"),
    ("The Federalist", "thefederalist.com", "right"),
    ("National Review", "nationalreview.com", "right"),
]


def seed_sources() -> None:
    with get_cursor() as cur:
        cur.executemany(
            "INSERT OR IGNORE INTO sources (name, domain, orientation) VALUES (?, ?, ?)",
            SOURCES,
        )


if __name__ == "__main__":
    seed_sources()
