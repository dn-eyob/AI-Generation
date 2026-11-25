# Kaggle notebook: Wan 2.2 TI2V-5B image-to-video for the shots marked "wan".
#
# Setup in Kaggle: New Notebook -> Settings: Accelerator "GPU T4 x2", Internet ON
# -> Add Input -> your dataset "heritage-bundle" (made by `python -m pipeline.kaggle_io bundle`).
# Paste each "# %%" block into its own cell and run top to bottom.
#
# Sources (checked 2026-11-26):
#   https://huggingface.co/Wan-AI/Wan2.2-TI2V-5B  (Apache 2.0)
#   Official CLI: generate.py --task ti2v-5B --size 1280*704 --image ... ; "can run on a GPU
#   with at least 24GB VRAM" with --offload_model True --convert_model_dtype --t5_cpu.
#   A T4 has 16 GB, so this script splits the model over BOTH T4s with the documented
#   multi-GPU flags (--dit_fsdp --t5_fsdp --ulysses_size 2). UNVERIFIED on T4: T4 has no
#   native bf16, so expect slowness or a dtype error. Any failure is logged; the local
#   pipeline then falls back to Ken Burns automatically.

# %% 1. Check GPUs
import subprocess
print(subprocess.run(["nvidia-smi"], capture_output=True, text=True).stdout)

# %% 2. Install Wan 2.2 and download TI2V-5B weights (~20-30 min first time)
import os
os.chdir("/kaggle/working")
if not os.path.exists("Wan2.2"):
    subprocess.run(["git", "clone", "--depth", "1", "https://github.com/Wan-Video/Wan2.2.git"], check=True)
# flash_attn often fails to build on Kaggle; install everything else first.
reqs = [l for l in open("Wan2.2/requirements.txt").read().splitlines()
        if l.strip() and not l.startswith("flash_attn")]
subprocess.run(["pip", "install", "-q", *reqs], check=True)
subprocess.run(["pip", "install", "-q", "huggingface_hub[cli]"], check=True)
subprocess.run(["huggingface-cli", "download", "Wan-AI/Wan2.2-TI2V-5B",
                "--local-dir", "/kaggle/working/Wan2.2-TI2V-5B"], check=True)

# %% 3. Generate clips, timeboxed, logging every attempt
import glob, json, time, uuid
from datetime import datetime, timezone

BUNDLE = glob.glob("/kaggle/input/*/storyboard.json")[0].rsplit("/", 1)[0]
OUT = "/kaggle/working/out"; os.makedirs(f"{OUT}/wan", exist_ok=True)
LOG = f"{OUT}/wan_runs.jsonl"
sb = json.load(open(f"{BUNDLE}/storyboard.json", encoding="utf-8"))

TIME_BUDGET_MIN = 90      # stop starting new clips after this many minutes
SAMPLE_STEPS = 25         # draft quality (official default is higher)
FRAME_NUM = 81            # ~3.4 s at 24 fps; local pipeline slows/holds to fit the shot
SIZE = "1280*704"         # TI2V-5B 720p area; aspect follows the input image
N_GPUS = 2

def log(**kw):
    rec = {"timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "run_id": uuid.uuid4().hex[:12], "stage": "shots_wan", "provider": "kaggle",
           "model": "Wan2.2-TI2V-5B", **kw}
    open(LOG, "a", encoding="utf-8").write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(rec)

start_all = time.time()
for shot in [s for s in sb["shots"] if s.get("video_mode") == "wan"]:
    if (time.time() - start_all) / 60 > TIME_BUDGET_MIN:
        log(shot_id=shot["id"], status="skipped", error="time budget reached"); continue
    out_file = f"{OUT}/wan/{shot['id']}.mp4"
    prompt = f"{shot['motion_prompt']}. {sb['style']['style_block']}"
    params = {"size": SIZE, "frame_num": FRAME_NUM, "sample_steps": SAMPLE_STEPS, "gpus": N_GPUS}
    cmd = ["torchrun", f"--nproc_per_node={N_GPUS}", "generate.py", "--task", "ti2v-5B",
           "--size", SIZE, "--ckpt_dir", "/kaggle/working/Wan2.2-TI2V-5B",
           "--image", f"{BUNDLE}/keyframes/{shot['id']}.png", "--prompt", prompt,
           "--frame_num", str(FRAME_NUM), "--sample_steps", str(SAMPLE_STEPS),
           "--base_seed", str(shot["seed"]), "--save_file", out_file,
           "--dit_fsdp", "--t5_fsdp", "--ulysses_size", str(N_GPUS)]
    t0 = time.time()
    proc = subprocess.run(cmd, cwd="/kaggle/working/Wan2.2", capture_output=True, text=True)
    secs = round(time.time() - t0, 1)
    ok = proc.returncode == 0 and os.path.exists(out_file)
    log(shot_id=shot["id"], status="ok" if ok else "error", seed=shot["seed"], parameters=params,
        latency_sec=secs, gpu_minutes=round(secs * N_GPUS / 60, 2),
        output=f"outputs/wan/{shot['id']}.mp4" if ok else None,
        error=None if ok else proc.stderr[-800:], notes="Kaggle 2x T4")

# %% 4. Zip results -> download from the notebook's Output panel
import shutil
shutil.make_archive("/kaggle/working/wan_results", "zip", OUT)
print("Download /kaggle/working/wan_results.zip, then locally run:")
print("  python -m pipeline.kaggle_io import <path-to>/wan_results.zip")
