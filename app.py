from pathlib import Path
import sqlite3
from datetime import date, timedelta
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Smart Expense Tracker", page_icon="💸", layout="wide")
DATA = Path(__file__).parent / "data"
DATA.mkdir(exist_ok=True)
DB = DATA / "expenses.db"

def connect():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    return con

def init_db():
    with connect() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS categories(name TEXT PRIMARY KEY COLLATE NOCASE, kind TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS transactions(id INTEGER PRIMARY KEY, kind TEXT NOT NULL, amount REAL NOT NULL CHECK(amount>0), category TEXT NOT NULL, description TEXT, tx_date TEXT NOT NULL, method TEXT);
        CREATE TABLE IF NOT EXISTS budgets(id INTEGER PRIMARY KEY, category TEXT NOT NULL, amount REAL NOT NULL, month INTEGER NOT NULL, year INTEGER NOT NULL, UNIQUE(category,month,year));
        """)
        for n in ["Food","Transportation","Education","Shopping","Healthcare","Entertainment","Bills","Travel","Others"]:
            c.execute("INSERT OR IGNORE INTO categories VALUES (?, 'expense')",(n,))
        for n in ["Salary","Allowance","Freelance","Investment","Other income"]:
            c.execute("INSERT OR IGNORE INTO categories VALUES (?, 'income')",(n,))

def categories(kind):
    with connect() as c:
        return [r["name"] for r in c.execute("SELECT name FROM categories WHERE kind=? ORDER BY name",(kind,))]
def transactions(start=None,end=None,kind=None):
    q="SELECT * FROM transactions WHERE 1=1"; p=[]
    if start: q+=" AND tx_date>=?"; p.append(str(start))
    if end: q+=" AND tx_date<=?"; p.append(str(end))
    if kind in ("income","expense"): q+=" AND kind=?"; p.append(kind)
    q+=" ORDER BY tx_date DESC,id DESC"
    with connect() as c: return pd.DataFrame([dict(r) for r in c.execute(q,p)])
def money(x): return f"₹{x:,.2f}"
def add_tx(kind,amount,category,description,when,method):
    if amount<=0: raise ValueError("Amount must be greater than zero.")
    with connect() as c:
        c.execute("INSERT INTO transactions(kind,amount,category,description,tx_date,method) VALUES(?,?,?,?,?,?)",(kind,amount,category,description,when.isoformat(),method))
def style():
    st.markdown("""<style>
    .stApp{background:#f5f7fb} [data-testid="stSidebar"]{background:#101d34}
    [data-testid="stSidebar"] *{color:#edf3ff!important}
    [data-testid="stMetric"]{background:white;border:1px solid #e7ecf4;padding:1rem;border-radius:14px}
    .block-container{max-width:1440px;padding-top:2rem}
    </style>""",unsafe_allow_html=True)

init_db(); style()
with st.sidebar:
    st.title("💸 SpendWise")
    st.caption("Personal finance, made clear.")
    page=st.radio("Navigation",["Dashboard","Transactions","Budgets","Analytics","Reports"])
    with st.expander("＋ Add category"):
        cn=st.text_input("Category name")
        ck=st.selectbox("Category type",["expense","income"])
        if st.button("Create category"):
            if cn.strip():
                try:
                    with connect() as c: c.execute("INSERT INTO categories VALUES (?,?)",(cn.strip(),ck))
                    st.success("Category created."); st.rerun()
                except sqlite3.IntegrityError: st.error("Category already exists.")
            else: st.error("Enter a category name.")
    st.caption("Records are stored in this app's SQLite database.")

today=date.today()
all_rows=transactions()
month_rows=transactions(today.replace(day=1),today)
if page=="Dashboard":
    st.title("Dashboard")
    st.caption("A clear picture of your personal finances.")
    inc=float(month_rows.loc[month_rows.kind=="income","amount"].sum()) if not month_rows.empty else 0
    exp=float(month_rows.loc[month_rows.kind=="expense","amount"].sum()) if not month_rows.empty else 0
    a,b,c,d=st.columns(4); a.metric("Income this month",money(inc)); b.metric("Expenses this month",money(exp)); c.metric("Net savings",money(inc-exp)); d.metric("Savings rate",f"{(inc-exp)/inc:.1%}" if inc else "0.0%")
    left,right=st.columns(2)
    with left:
        st.subheader("Spending by category")
        if not month_rows.empty:
            e=month_rows[month_rows.kind=="expense"].groupby("category",as_index=False).amount.sum()
            if not e.empty: st.plotly_chart(px.pie(e,names="category",values="amount",hole=.5),use_container_width=True)
            else: st.info("No expenses recorded this month.")
        else: st.info("Add transactions to see your spending.")
    with right:
        st.subheader("Recent transactions")
        if all_rows.empty: st.info("No transactions yet.")
        else: st.dataframe(all_rows.head(10),use_container_width=True,hide_index=True)
elif page=="Transactions":
    st.title("Transactions")
    with st.form("add_transaction",clear_on_submit=True):
        kind=st.selectbox("Type",["expense","income"])
        cat=st.selectbox("Category",categories(kind))
        amount=st.number_input("Amount (₹)",min_value=0.0,step=100.0)
        when=st.date_input("Date",value=today)
        method=st.selectbox("Payment method",["Cash","Debit card","Credit card","Bank transfer","UPI","Wallet","Other"])
        desc=st.text_input("Description",max_chars=200)
        if st.form_submit_button("Save transaction"):
            try: add_tx(kind,amount,cat,desc,when,method); st.success("Saved."); st.rerun()
            except Exception as e: st.error(str(e))
    st.subheader("History")
    f1,f2,f3=st.columns(3)
    start=f1.date_input("From",today-timedelta(days=30)); end=f2.date_input("To",today); k=f3.selectbox("Type",["All","expense","income"])
    if start<=end:
        rows=transactions(start,end,None if k=="All" else k)
        if rows.empty: st.info("No matching transactions.")
        else:
            st.dataframe(rows,use_container_width=True,hide_index=True)
            ids=rows.id.tolist()
            selected=st.selectbox("Delete transaction by ID",ids)
            if st.button("Delete selected transaction"):
                with connect() as c: c.execute("DELETE FROM transactions WHERE id=?",(int(selected),))
                st.success("Deleted."); st.rerun()
    else: st.error("Start date must not be after end date.")
elif page=="Budgets":
    st.title("Monthly budgets")
    m=st.selectbox("Month",range(1,13),index=today.month-1,format_func=lambda x:date(2000,x,1).strftime("%B"))
    y=st.number_input("Year",min_value=2000,max_value=2100,value=today.year)
    with st.form("budget"):
        cat=st.selectbox("Expense category",categories("expense"))
        limit=st.number_input("Monthly limit (₹)",min_value=1.0,step=500.0)
        if st.form_submit_button("Save budget"):
            with connect() as c: c.execute("INSERT INTO budgets(category,amount,month,year) VALUES(?,?,?,?) ON CONFLICT(category,month,year) DO UPDATE SET amount=excluded.amount",(cat,limit,m,int(y)))
            st.success("Budget saved."); st.rerun()
    start=date(int(y),int(m),1); end=date(int(y)+1,1,1)-timedelta(days=1) if m==12 else date(int(y),int(m)+1,1)-timedelta(days=1)
    spent=transactions(start,end,"expense")
    sums=spent.groupby("category").amount.sum().to_dict() if not spent.empty else {}
    with connect() as c: budgets=[dict(r) for r in c.execute("SELECT * FROM budgets WHERE month=? AND year=?",(m,int(y)))]
    for item in budgets:
        value=float(sums.get(item["category"],0)); ratio=value/item["amount"]
        st.markdown(f"**{item['category']}** · {money(value)} / {money(item['amount'])}")
        st.progress(min(ratio,1.0))
        if ratio>=1: st.error(f"Over budget by {money(value-item['amount'])}.")
        elif ratio>=.8: st.warning(f"{ratio:.0%} of budget used.")
        else: st.caption(f"{ratio:.0%} used · {money(item['amount']-value)} remaining")
        if st.button(f"Remove {item['category']}",key=f"remove{item['id']}"):
            with connect() as c: c.execute("DELETE FROM budgets WHERE id=?",(item["id"],))
            st.rerun()
elif page=="Analytics":
    st.title("Analytics")
    df=all_rows
    if df.empty: st.info("Add transactions to unlock analytics.")
    else:
        expenses=df[df.kind=="expense"]
        if not expenses.empty:
            cat=expenses.groupby("category",as_index=False).amount.sum()
            st.subheader("Expense by category"); st.plotly_chart(px.pie(cat,names="category",values="amount",hole=.5),use_container_width=True)
        df["month"]=pd.to_datetime(df.tx_date).dt.to_period("M").astype(str)
        monthly=df.pivot_table(index="month",columns="kind",values="amount",aggfunc="sum",fill_value=0).reset_index()
        st.subheader("Monthly income vs expenses")
        st.plotly_chart(px.bar(monthly,x="month",y=[x for x in ["income","expense"] if x in monthly],barmode="group"),use_container_width=True)
        if not expenses.empty:
            daily=expenses.groupby("tx_date",as_index=False).amount.sum()
            st.subheader("Daily expense trend"); st.plotly_chart(px.line(daily,x="tx_date",y="amount",markers=True),use_container_width=True)
else:
    st.title("Reports & exports")
    start=st.date_input("Start date",date(today.year,1,1)); end=st.date_input("End date",today)
    if start<=end:
        df=transactions(start,end)
        inc=float(df.loc[df.kind=="income","amount"].sum()) if not df.empty else 0
        exp=float(df.loc[df.kind=="expense","amount"].sum()) if not df.empty else 0
        a,b,c=st.columns(3); a.metric("Income",money(inc)); b.metric("Expenses",money(exp)); c.metric("Net",money(inc-exp))
        if not df.empty:
            st.dataframe(df,use_container_width=True,hide_index=True)
            st.download_button("Download transactions CSV",df.to_csv(index=False).encode("utf-8-sig"),"transactions.csv","text/csv")
            summary=pd.DataFrame([["Income",inc],["Expenses",exp],["Net balance",inc-exp]],columns=["Metric","Amount"])
            st.download_button("Download summary CSV",summary.to_csv(index=False).encode("utf-8-sig"),"summary.csv","text/csv")
    else: st.error("Start date must not be after end date.")
