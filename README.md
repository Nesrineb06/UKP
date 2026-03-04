# ReviewArena – Prototype

Minimal full-stack prototype for a **blind review comparison system**: two reviews side-by-side, vote A / Tie / B, leaderboard of models by votes.

## Requirements

- Python 3.8+
- (Optional) `venv` for a virtual environment

## Setup and run

1. **Backend (Flask + SQLite)**

   ```bash
   cd backend
   python -m venv venv
   venv\Scripts\activate    # Windows
   # source venv/bin/activate   # macOS/Linux
   pip install -r requirements.txt
   python app.py
   ```

   Server runs at **http://localhost:5000**. The app creates `reviewarena.db` and seeds it with sample models and comparisons on first run.

2. **Use the app**

   - Open **http://localhost:5000** in a browser.
   - **Compare**: You get a random blind comparison (Review A vs Review B). Click “A is better”, “Tie”, or “B is better”. Buttons disable and model names are revealed.
   - **Leaderboard**: Open “Leaderboard” to see models ranked by votes (descending).

## API (backend)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/comparison` | Returns one blind comparison: `comparison_id`, `review_a`, `review_b` |
| POST | `/vote` | Body: `{ "comparison_id": 1, "winner": "A" \| "B" \| "tie" }`. Returns updated leaderboard. |
| GET | `/leaderboard` | Returns ranked list: `[{ "model": "...", "votes": n }, ...]` |
| GET | `/comparison/<id>/reveal` | After voting, returns `model_a` and `model_b` for that comparison |

## Database (SQLite)

- **models** – id, name  
- **reviews** – id, model_id, text  
- **comparisons** – id, review_a_id, review_b_id  
- **votes** – id, comparison_id, winner (‘A’ \| ‘B’ \| ‘tie’)

Relationships: reviews belong to models; comparisons link two reviews; votes reference a comparison and a winner.

## Tech stack

- **Backend**: Flask, SQLite, flask-cors  
- **Frontend**: Plain HTML, CSS, JavaScript (no framework)
