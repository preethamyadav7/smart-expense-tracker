# Smart Expense Tracker

A local-first personal finance dashboard built with Python, Streamlit, SQLite, Pandas and Plotly.

## Features
- Monthly dashboard for income, expenses, net savings and savings rate
- Add, search/filter and delete transactions
- Custom income and expense categories
- Monthly category budgets with 80% and over-budget warnings
- Spending charts and monthly trends
- Date-range reports and CSV exports
- SQLite persistence

## Run locally
```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

The app creates `data/expenses.db` automatically. Do not commit this database: it contains personal financial records. This starter version is single-user and does not include authentication or bank integrations.
