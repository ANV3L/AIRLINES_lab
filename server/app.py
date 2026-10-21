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

ROOT_DIR = BASE_DIR.parent
RESOURCES_DIR = ROOT_DIR / "resources/processed"
FILES_MAP = {
    "ghosts.csv": ROOT_DIR / "src/find_ghosts/ghosts.csv",

    "shadow_groups.csv": RESOURCES_DIR / "shadow_groups.csv",
    "shadow_groups.md": ROOT_DIR / "src/shadow_groups_finder/SPIES.md",

    "discrepancy.csv":RESOURCES_DIR / "discrepancy.csv",

    "bad_document.csv": RESOURCES_DIR / "bad_document.csv",

    "artefacts.csv": RESOURCES_DIR / "artefacts.csv",

    "chart_age.svg":        ROOT_DIR / "src/static_an/chart_age.svg",
    "chart_arrivals.svg":   ROOT_DIR / "src/static_an/chart_arrivals.svg",
    "chart_departures.svg": ROOT_DIR / "src/static_an/chart_departures.svg",
}


@app.route("/api/files/<path:filename>")
def get_file(filename):
    real_path = FILES_MAP.get(filename)
    print("file:", real_path)
    if not real_path or not real_path.exists():
        abort(404)

    return send_from_directory(
        real_path.parent,
        real_path.name,
        as_attachment=True,
        download_name=filename,   # браузер сохранит под URL-именем
    )

if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)