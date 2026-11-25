# Kaggle notebook: ACE-Step 1.5 score candidates (instrumental) from storyboard.json.
#
# Setup in Kaggle: New Notebook -> Accelerator "GPU T4 x2" (uses one), Internet ON
# -> Add Input -> dataset "heritage-bundle". Paste each "# %%" block into its own cell.
#
# Sources (checked 2026-11-26):
#   https://github.com/ACE-Step/ACE-Step-1.5 (MIT; outputs usable commercially)
#   docs/en/INFERENCE.md: AceStepHandler, LLMHandler, GenerationParams, GenerationConfig,
#   generate_music(dit, llm, params, config, save_dir=...). Python 3.11-3.12.
#   GPU tier 12-16 GB: LM 0.6B/1.7B, batch <= 4, CPU offload. T4 not named in the docs.
#   Low-VRAM init flags (offload_to_cpu, int8) are UNVERIFIED, so they're tried, then dropped.

# %% 1. Install
import os, subprocess, sys
os.chdir("/kaggle/working")
if not os.path.exists("ACE-Step-1.5"):
    subprocess.run(["git", "clone", "--depth", "1", "https://github.com/ACE-Step/ACE-Step-1.5.git"], check=True)
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-e", "ACE-Step-1.5"], check=True)
print(sys.version)

# %% 2. Generate 3 candidates (one batch, fixed seeds), logging the call
import glob, json, time, uuid
from datetime import datetime, timezone
sys.path.insert(0, "/kaggle/working/ACE-Step-1.5")
from acestep.handler import AceStepHandler
from acestep.llm_inference import LLMHandler
from acestep.inference import GenerationParams, GenerationConfig, generate_music

BUNDLE = glob.glob("/kaggle/input/*/storyboard.json")[0].rsplit("/", 1)[0]
OUT = "/kaggle/working/out"; os.makedirs(f"{OUT}/music", exist_ok=True)
LOG = f"{OUT}/music_runs.jsonl"
sb = json.load(open(f"{BUNDLE}/storyboard.json", encoding="utf-8"))
m = sb["music"]
duration = int(sum(s["duration_sec"] for s in sb["shots"]) + 3)   # film + end card
seeds = [m.get("seed", 4242) + i for i in range(3)]
keyscale = " ".join(w.capitalize() for w in m.get("key", "E minor").split())

dit, llm = AceStepHandler(), LLMHandler()
try:
    dit.initialize_service(project_root="/kaggle/working/ACE-Step-1.5", config_path="acestep-v15-turbo",
                           device="cuda", offload_to_cpu=True)
except TypeError:   # flag not supported in this version -> documented minimal call
    dit.initialize_service(project_root="/kaggle/working/ACE-Step-1.5", config_path="acestep-v15-turbo",
                           device="cuda")
llm.initialize(checkpoint_dir="/kaggle/working/ACE-Step-1.5/checkpoints",
               lm_model_path="acestep-5Hz-lm-0.6B", backend="pt", device="cuda")

params = GenerationParams(caption=m["caption"], instrumental=True, bpm=m.get("tempo_bpm", 72),
                          keyscale=keyscale, duration=duration)
config = GenerationConfig(batch_size=3, seeds=seeds, use_random_seed=False, audio_format="wav")
t0 = time.time()
result = generate_music(dit, llm, params, config, save_dir=f"{OUT}/music")
secs = round(time.time() - t0, 1)

rec = {"timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"), "run_id": uuid.uuid4().hex[:12],
       "stage": "music", "shot_id": None, "provider": "kaggle", "model": "ACE-Step-1.5 acestep-v15-turbo + lm-0.6B",
       "status": "ok" if result.success else "error", "seed": seeds,
       "parameters": {"caption": m["caption"], "bpm": m.get("tempo_bpm"), "keyscale": keyscale,
                      "duration": duration, "batch_size": 3, "instrumental": True},
       "latency_sec": secs, "gpu_minutes": round(secs / 60, 2),
       "output": [a["path"].split("/")[-1] for a in result.audios] if result.success else None,
       "error": None if result.success else str(result.error)[:800], "notes": "Kaggle T4 (1 GPU)"}
open(LOG, "a", encoding="utf-8").write(json.dumps(rec, ensure_ascii=False) + "\n")
print(json.dumps(rec, indent=1, ensure_ascii=False))

# %% 3. Zip -> download from the Output panel, then locally:
#    python -m pipeline.kaggle_io import <path-to>/music_results.zip
import shutil
shutil.make_archive("/kaggle/working/music_results", "zip", OUT)
