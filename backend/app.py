"""
ReviewArena - Blind review comparison backend.
Flask + SQLite. Endpoints: GET /comparison, POST /vote, GET /leaderboard.
"""
import os
import sqlite3
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")
app = Flask(__name__)
CORS(app)

DB_PATH = os.path.join(os.path.dirname(__file__), "reviewarena.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.executescript("""
        CREATE TABLE IF NOT EXISTS models (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL UNIQUE
        );
        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY,
            model_id INTEGER NOT NULL,
            text TEXT NOT NULL,
            FOREIGN KEY (model_id) REFERENCES models(id)
        );
        CREATE TABLE IF NOT EXISTS comparisons (
            id INTEGER PRIMARY KEY,
            review_a_id INTEGER NOT NULL,
            review_b_id INTEGER NOT NULL,
            FOREIGN KEY (review_a_id) REFERENCES reviews(id),
            FOREIGN KEY (review_b_id) REFERENCES reviews(id)
        );
        CREATE TABLE IF NOT EXISTS votes (
            id INTEGER PRIMARY KEY,
            comparison_id INTEGER NOT NULL,
            winner TEXT NOT NULL CHECK (winner IN ('A', 'B', 'tie')),
            FOREIGN KEY (comparison_id) REFERENCES comparisons(id)
        );
    """)
    conn.commit()
    conn.close()


def seed_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM models")
    if cur.fetchone()[0] > 0:
        conn.close()
        return
    cur.executemany(
        "INSERT INTO models (id, name) VALUES (?, ?)",
        [(1, "GPT-5"), (2, "Gemini-3 Pro"), (3, "Claude-4")]
    )
    reviews = [
        (1, 1, "This paper proposes a novel approach to few-shot learning. The methodology is sound and the experiments are well-designed. However, the baseline comparisons could be expanded."),
        (2, 1, "The contribution is incremental. While the writing is clear, the empirical section lacks ablation studies."),
        (3, 2, "The methodology is unclear in several places. The authors should clarify the training procedure and hyperparameters. Strong points: good related work."),
        (4, 2, "Solid work with reproducible code. The main limitation is the narrow set of benchmarks. I recommend acceptance with minor revisions."),
        (5, 3, "A well-motivated problem and a clean solution. The theoretical analysis in Section 3 is particularly compelling. I vote for acceptance."),
        (6, 3, "The paper would benefit from more comparison with concurrent work. The results are promising but the evaluation is limited to one domain."),
    ]
    cur.executemany(
        "INSERT INTO reviews (id, model_id, text) VALUES (?, ?, ?)",
        reviews
    )
    comparisons = [
        (1, 1, 3),
        (2, 2, 4),
        (3, 5, 2),
        (4, 6, 4),
        (5, 1, 5),
    ]
    cur.executemany(
        "INSERT INTO comparisons (id, review_a_id, review_b_id) VALUES (?, ?, ?)",
        comparisons
    )
    conn.commit()
    conn.close()


def _fetch_one_comparison(cur):
    cur.execute("""
        SELECT c.id AS comparison_id, ra.text AS review_a, rb.text AS review_b
        FROM comparisons c
        JOIN reviews ra ON c.review_a_id = ra.id
        JOIN reviews rb ON c.review_b_id = rb.id
        ORDER BY RANDOM()
        LIMIT 1
    """)
    return cur.fetchone()


@app.route("/comparison", methods=["GET"])
def get_comparison():
    for attempt in range(2):
        try:
            conn = get_db()
            cur = conn.cursor()
            row = _fetch_one_comparison(cur)
            conn.close()
            if row:
                return jsonify({
                    "comparison_id": row["comparison_id"],
                    "review_a": row["review_a"],
                    "review_b": row["review_b"],
                })
            if attempt == 0:
                init_db()
                seed_db()
        except sqlite3.OperationalError:
            if attempt == 0:
                init_db()
                seed_db()
            else:
                raise
    return jsonify({"error": "No comparisons available"}), 404


@app.route("/vote", methods=["POST"])
def post_vote():
    data = request.get_json()
    if not data or "comparison_id" not in data or "winner" not in data:
        return jsonify({"error": "comparison_id and winner required"}), 400
    raw = (data["winner"] or "").strip().upper()
    if raw not in ("A", "B", "TIE"):
        return jsonify({"error": "winner must be A, B, or tie"}), 400
    winner_db = "tie" if raw == "TIE" else raw
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO votes (comparison_id, winner) VALUES (?, ?)",
        (data["comparison_id"], winner_db)
    )
    conn.commit()
    cur.execute("""
        SELECT m.name, m.id,
            (SELECT COUNT(*) FROM votes v
             JOIN comparisons c ON v.comparison_id = c.id
             JOIN reviews r ON (r.id = c.review_a_id AND v.winner = 'A') OR (r.id = c.review_b_id AND v.winner = 'B')
             WHERE r.model_id = m.id) AS votes
        FROM models m
        ORDER BY votes DESC
    """)
    leaderboard = [{"model": r["name"], "votes": r["votes"]} for r in cur.fetchall()]
    conn.close()
    return jsonify({"updated_votes": leaderboard})


@app.route("/reset-votes", methods=["POST"])
def reset_votes():
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("DELETE FROM votes")
        conn.commit()
        conn.close()
        return jsonify({"ok": True, "message": "All votes reset to 0"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/leaderboard", methods=["GET"])
def get_leaderboard():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT m.name AS model,
            (SELECT COUNT(*) FROM votes v
             JOIN comparisons c ON v.comparison_id = c.id
             JOIN reviews r ON (r.id = c.review_a_id AND v.winner = 'A') OR (r.id = c.review_b_id AND v.winner = 'B')
             WHERE r.model_id = m.id) AS votes
        FROM models m
        ORDER BY votes DESC
    """)
    rows = cur.fetchall()
    conn.close()
    return jsonify([{"model": r["model"], "votes": r["votes"]} for r in rows])


@app.route("/")
def index_page():
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.route("/leaderboard.html")
def leaderboard_page():
    return send_from_directory(FRONTEND_DIR, "leaderboard.html")


@app.route("/comparison/<int:cid>/reveal", methods=["GET"])
def reveal_models(cid):
    """Reveal which model wrote review A and B for a given comparison (after vote)."""
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT ma.name AS model_a, mb.name AS model_b
        FROM comparisons c
        JOIN reviews ra ON c.review_a_id = ra.id
        JOIN reviews rb ON c.review_b_id = rb.id
        JOIN models ma ON ra.model_id = ma.id
        JOIN models mb ON rb.model_id = mb.id
        WHERE c.id = ?
    """, (cid,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return jsonify({"error": "Not found"}), 404
    return jsonify({"model_a": row["model_a"], "model_b": row["model_b"]})


@app.route("/<path:path>")
def frontend_static(path):
    """Serve frontend assets; must be last so API routes are matched first."""
    if path in ("index.html", "leaderboard.html", "style.css", "app.js"):
        return send_from_directory(FRONTEND_DIR, path)
    return jsonify({"error": "Not found"}), 404


# Ensure DB exists and is seeded as soon as the app loads (e.g. after DB was deleted)
init_db()
seed_db()

if __name__ == "__main__":
    app.run(port=5000, debug=True)
