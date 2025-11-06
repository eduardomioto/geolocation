import sys
import os
import subprocess
import time
import psutil

# Simple console logger
def log(message, level="INFO", emoji=None):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    emoji_str = f"{emoji} " if emoji else ""
    print(f"{ts} [{level:<7}] {emoji_str}{message}", flush=True)


def get_file_size_mb(file_path):
    return round(os.path.getsize(file_path) / (1024 * 1024), 2) if os.path.exists(file_path) else None


def log_system_usage(tag):
    process = psutil.Process(os.getpid())
    memory = round(process.memory_info().rss / (1024 * 1024), 2)
    cpu = psutil.cpu_percent(interval=0.5)
    log(f"CPU {cpu}% | Memory {memory}MB ({tag})", "INFO", "🧠")


def run_osmium_extract(input_file, output_file):
    """Convert OSM PBF → GeoJSON using osmium-tool."""
    # ✅ Check if target file already exists
    if os.path.exists(output_file):
        existing_size = get_file_size_mb(output_file)
        log(f"📁 GeoJSON file already exists → {output_file} ({existing_size} MB)", "INFO", "⚠️")
        log("Skipping conversion step.", "INFO", "⏭️")
        return

    input_size = get_file_size_mb(input_file)
    log(
        f"Convert OSM PBF to GeoJSON → osmium export --progress --overwrite -o {output_file} {input_file} "
        f"(size: {input_size} MB)",
        "INFO",
        "🧩",
    )

    start_time = time.time()
    cmd = ["osmium", "export", "--progress", "--overwrite", "-o", output_file, input_file]

    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    for line in iter(process.stdout.readline, ""):
        if "%" in line or "Done" in line:
            print(line.strip(), flush=True)
    process.wait()

    if process.returncode != 0:
        log("Osmium export failed.", "ERROR", "❌")
        sys.exit(1)

    elapsed = round(time.time() - start_time, 1)
    output_size = get_file_size_mb(output_file)
    log(f"✅ Convert OSM PBF to GeoJSON completed in {elapsed}s (size: {output_size} MB)", "INFO", "✅")
    log_system_usage("after_osmium")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python convert_pbf.py <input.osm.pbf> <output_folder>")
        sys.exit(1)

    osm_file = sys.argv[1]
    output_folder = sys.argv[2]
    os.makedirs(output_folder, exist_ok=True)

    output_file = os.path.join(output_folder, os.path.basename(osm_file).replace(".osm.pbf", ".geojson"))
    log("🚀 Starting OSM → GeoJSON conversion", "INFO")
    log_system_usage("startup")

    run_osmium_extract(osm_file, output_file)
