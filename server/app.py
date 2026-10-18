from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory, abort

from commands import COMMANDS

BASE_DIR = Path(__file__).resolve().parent
REPORT_PATH = BASE_DIR / "report.md"
PLOTS_DIR = BASE_DIR / "plots"

app = Flask(__name__, static_folder=None)


@app.route("/")
def index():
    return send_from_directory(BASE_DIR, "index.html")


@app.route("/api/command", methods=["POST"])
def api_command():
    data = request.get_json(silent=True) or {}
    command = data.get("command")

    if not command or command not in COMMANDS:
        return jsonify({"error": f"Unknown command: {command}"}), 400
    
    REPORT_PATH.write_text("", encoding="utf-8")

    try:
        status = COMMANDS[command]()
    except Exception:
        status = "1"

    return jsonify({"status": status})


@app.route("/report.md")
def get_report():
    if not REPORT_PATH.exists():
        REPORT_PATH.write_text(
            "# Report\n\n_No report generated yet._\n", encoding="utf-8"
        )
    response = send_from_directory(BASE_DIR, "report.md")
    response.headers["Cache-Control"] = "no-store"
    return response


@app.route("/plots/<path:filename>")
def get_plot(filename):
    if not (PLOTS_DIR / filename).exists():
        abort(404)
    response = send_from_directory(PLOTS_DIR, filename)
    response.headers["Cache-Control"] = "no-store"
    return response


if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)