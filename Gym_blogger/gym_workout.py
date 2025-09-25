# gym_workout.py
import os
import uuid
from datetime import datetime, date, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st

# ---------- Config ----------
DATA_DIR = Path("data")
DATA_FILE = DATA_DIR / "workouts.csv"
DEFAULT_WEEKS = 12
UNITS = ["kg", "lb"]

# ---------- Helpers ----------
def ensure_data_file():
    DATA_DIR.mkdir(exist_ok=True)
    if not DATA_FILE.exists():
        df = pd.DataFrame(columns=[
            "id", "timestamp", "date", "exercise", "set_num",
            "reps", "weight", "unit", "notes", "volume"
        ])
        df.to_csv(DATA_FILE, index=False)

@st.cache_data
def load_data() -> pd.DataFrame:
    ensure_data_file()
    df = pd.read_csv(DATA_FILE)
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"]).dt.date
        df["reps"] = pd.to_numeric(df["reps"], errors="coerce").fillna(0).astype(int)
        df["weight"] = pd.to_numeric(df["weight"], errors="coerce").fillna(0.0)
        df["volume"] = pd.to_numeric(df["volume"], errors="coerce").fillna(0.0)
    return df

def save_data(df: pd.DataFrame):
    df.to_csv(DATA_FILE, index=False)
    load_data.clear()

def add_workout_entry(entry_date: date, exercise: str, sets: list, unit: str, notes: str):
    df = load_data()
    ts = datetime.now().isoformat()
    rows = []
    for s in sets:
        volume = s["reps"] * float(s["weight"])
        rows.append({
            "id": str(uuid.uuid4()),
            "timestamp": ts,
            "date": entry_date.isoformat(),
            "exercise": exercise.strip(),
            "set_num": int(s["set_num"]),
            "reps": int(s["reps"]),
            "weight": float(s["weight"]),
            "unit": unit,
            "notes": notes.strip(),
            "volume": volume
        })
    if rows:
        df = pd.concat([df, pd.DataFrame(rows)], ignore_index=True)
        save_data(df)

def delete_rows_by_ids(ids: list):
    df = load_data()
    if df.empty:
        return
    df = df[~df["id"].isin(ids)]
    save_data(df)

def get_weekly_summary(df: pd.DataFrame, weeks:int=DEFAULT_WEEKS, exercise_filter: str=None):
    if df.empty:
        return pd.DataFrame()
    df2 = df.copy()
    df2["date"] = pd.to_datetime(df2["date"])
    df2["year_week"] = df2["date"].dt.strftime("%Y-W%V")
    if exercise_filter and exercise_filter != "All":
        df2 = df2[df2["exercise"] == exercise_filter]
    grouped = df2.groupby("year_week")["volume"].sum().reset_index()
    today = date.today()
    wk_list = [(today - timedelta(weeks=i)).strftime("%Y-W%V") for i in range(weeks-1, -1, -1)]
    df_weeks = pd.DataFrame({"year_week": wk_list})
    merged = df_weeks.merge(grouped, on="year_week", how="left").fillna(0)
    merged["volume"] = merged["volume"].astype(float)
    return merged

# ---------- Streamlit UI ----------
st.set_page_config(page_title="Gym Workout Logger 🏋️", layout="wide")

# --- Custom Green Background ---
st.markdown(
    """
    <style>
    .stApp {
        background-color: #d4f7d4;  /* light green */
    }
    </style>
    """,
    unsafe_allow_html=True
)

# --- Title ---
st.title("🏋️ Gym Workout Logger 💪🔥")

st.markdown(
    "Track your exercises (sets, reps, weight). "
    "Stay strong and motivated! 🏃‍♂️🥊🧘‍♀️"
)

# Sidebar
st.sidebar.header("⚙️ Settings")
unit = st.sidebar.selectbox("🏋️ Weight unit", UNITS, index=0)
weeks_to_show = st.sidebar.slider("📊 Weeks to show on chart", 4, 24, DEFAULT_WEEKS, 1)

df = load_data()

# --- Log workout ---
st.subheader("📝 Log a workout")
with st.form("log_form"):
    col1, col2 = st.columns([2,1])
    with col1:
        exercise = st.text_input("💪 Exercise name", placeholder="e.g., Bench Press 🏋️")
        entry_date = st.date_input("📅 Date", value=date.today())
        notes = st.text_input("🗒️ Notes (optional)", placeholder="e.g., felt strong, focus on form 💯")
    with col2:
        num_sets = st.number_input("🔢 Number of sets", 1, 12, 3, 1)
        st.markdown("**Enter reps & weights for each set 🏋️**")
        sets = []
        for i in range(1, int(num_sets)+1):
            c1, c2 = st.columns([1,1])
            reps = c1.number_input(f"Set {i} 🔄 reps", 0, 100, 8, 1, key=f"reps_{i}")
            weight = c2.number_input(f"Set {i} 🏋️ weight ({unit})", 0.0, 1000.0, 50.0, 0.5, key=f"weight_{i}")
            sets.append({"set_num": i, "reps": reps, "weight": weight})
    submitted = st.form_submit_button("➕ Add workout ✅")
    if submitted:
        if not exercise.strip():
            st.warning("⚠️ Please enter an exercise name.")
        else:
            add_workout_entry(entry_date, exercise, sets, unit, notes)
            st.success(f"🎉 Added {len(sets)} sets for {exercise} on {entry_date}. Keep pushing! 💪🔥")
            df = load_data()

# --- Today's summary ---
st.markdown("---")
st.subheader("📌 Today's summary 🗓️")
today = date.today()
today_df = df[df["date"] == today]
if today_df.empty:
    st.info("No entries for today yet. 💤")
else:
    agg = today_df.groupby("exercise").agg(
        sets=("set_num","count"),
        total_reps=("reps","sum"),
        total_volume=("volume","sum")
    ).reset_index()
    agg["total_volume"] = agg["total_volume"].round(2)
    st.table(agg)

# --- Full history ---
st.markdown("---")
st.subheader("📜 Full history 📊")
if df.empty:
    st.info("No workout history yet. Start logging today! 🏋️")
else:
    show_df = df.sort_values(by=["date","exercise","set_num"], ascending=[False,True,True])
    options = show_df.apply(
        lambda r: f"{r['date']} | {r['exercise']} | set {r['set_num']} | "
                  f"{r['reps']} reps x {r['weight']}{r['unit']} (vol {r['volume']}) | id:{r['id']}",
        axis=1
    ).tolist()
    selected = st.multiselect("❌ Select entries to delete 🗑️", options)
    if st.button("🗑️ Delete selected"):
        ids_to_del = [s.split("id:")[-1] for s in selected]
        delete_rows_by_ids(ids_to_del)
        st.success(f"✅ Deleted {len(ids_to_del)} rows.")
        df = load_data()
    st.dataframe(show_df.drop(columns=["id"]).rename(columns={
        "date":"Date","exercise":"Exercise","set_num":"Set#",
        "reps":"Reps","weight":"Weight","unit":"Unit","volume":"Volume","notes":"Notes"
    }))
    csv_bytes = df.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Download history (CSV)", csv_bytes, "workout_history.csv","text/csv")

# --- Weekly progress chart ---
st.markdown("---")
st.subheader("📈 Weekly progress (total volume = reps × weight) 📊")
exercise_list = ["All"] + sorted(df["exercise"].dropna().unique().tolist()) if not df.empty else ["All"]
selected_exercise = st.selectbox("🏋️ Select exercise", exercise_list)
weeks = st.number_input("🗓️ Weeks to include", 4, 52, weeks_to_show, 1)

summary_df = get_weekly_summary(df, weeks=weeks, exercise_filter=selected_exercise)
if summary_df.empty:
    st.info("No data to show in chart yet. Log some workouts first! 🏃‍♂️")
else:
    chart_df = summary_df.copy()
    chart_df = chart_df.set_index("year_week")
    chart_df.index.name = "Week"
    st.bar_chart(chart_df["volume"])
    display_table = chart_df.rename(columns={"volume":"Total Volume"})
    st.table(display_table.assign(**{"Total Volume": display_table["Total Volume"].round(2)}))

st.markdown("---")
st.caption("Made with ❤️🏋️ by Your Gym Logger — stay strong every week 💪🔥")
