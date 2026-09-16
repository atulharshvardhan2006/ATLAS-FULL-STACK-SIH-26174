"""
BAS-APG — Zero-Shot Dynamic Procedure Parsing (Offline VLM)

Uses a highly quantized, tiny local LLM (e.g., Qwen 0.5B via Transformers)
running purely on CPU to parse a plain-text scientific manual into a
deterministic JSON Finite State Machine (FSM).

Usage:
    python app/engines/protocol_compiler.py --input data/manual.txt --output data/generated_procedure.json
"""

import argparse
import json
import os
import re
import sys

import logging
_compiler_logger = logging.getLogger(__name__)

try:
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline
except ImportError:
    _compiler_logger.warning("LLM tools unavailable (torch/transformers). Protocol compiler offline.")
    torch = None
    AutoModelForCausalLM = None
    AutoTokenizer = None
    pipeline = None


DEFAULT_MODEL = "Qwen/Qwen2.5-0.5B-Instruct"

SYSTEM_PROMPT = """You are an expert aerospace systems engineer programming an AI Guardian for the Bio-containment Awareness System (BAS).
Your job is to read a plain-text scientific manual and convert it into a deterministic JSON state machine.
You must output ONLY valid JSON, with absolutely no markdown formatting, no code blocks, and no conversational text.

## STRICT RULES

### 1. Action Vocabulary (CLOSED SET — use ONLY these)
Map every manual instruction to one of these actions:
- "PICK" — Lifting, grabbing, acquiring, retrieving, picking up any object
- "PLACE" — Putting down, setting, depositing an object onto a surface
- "OPEN" — Unsealing, uncapping, opening a lid or container
- "CLOSE" — Sealing, capping, closing a lid or container
- "TRANSFER" — Moving an object from one container to another while held
- "POUR" — Dispensing liquid from one container into another
- "STIR" — Mixing, agitating, swirling contents of a container
- "INSPECT" — Observing, examining, reading a measurement or indicator

If an instruction does not clearly map to any of these, use "INSPECT" as the default.

### 2. Object Name Normalization (map to YOLO classes)
The AI vision system recognizes EXACTLY these 5 object classes:
  main_box, red_box, yellow_box, sample, tweezers

Map manual references as follows:
- "containment unit", "primary container", "experiment box", "main container" → "main_box"
- "red container", "red beaker", "secondary container", "reaction vessel" → "red_box"
- "yellow container", "reagent bottle", "acid container", "hazardous container" → "yellow_box"
- "specimen", "sample", "regolith", "substrate", "material" → "sample"
- "tweezers", "forceps", "tongs", "grip tool", "extraction tool" → "tweezers"

If an object cannot be mapped to any of these 5 classes, use the closest match and append "_unmapped" (e.g., "pipette_unmapped").

### 3. Timeout Extraction from Natural Language
- "for X minutes" → timeout_seconds = X * 60
- "for X seconds" → timeout_seconds = X
- "briefly" or "quickly" → timeout_seconds = 15
- "carefully" or "slowly" → timeout_seconds = 45
- "wait until" or "allow to settle" → timeout_seconds = 120
- If no time reference is given → timeout_seconds = 30 (default)

### 4. Handling Ambiguous Steps
- If a step combines two actions (e.g., "Pick up and transfer"), split into TWO separate steps.
- If a step is purely observational (e.g., "Note the color change"), use action "INSPECT".
- If a step mentions safety equipment (e.g., "Put on gloves"), SKIP it — the FSM tracks objects, not PPE.

### 5. Hazardous Material Flag
- If a step involves "acid", "corrosive", "toxic", "hazardous", or "biohazard", add "containment_alert" to that step's recovery_options.
- If a step involves opening a hazardous container, set confidence_threshold to 0.90 (stricter detection required).

## OUTPUT SCHEMA

The JSON MUST follow this exact schema:
{
  "id": "string",
  "name": "string",
  "version": "1.0",
  "description": "string",
  "objects": ["main_box", "red_box", "yellow_box", "sample", "tweezers"],
  "steps": [
    {
      "step_id": "S01",
      "action": "PICK",
      "object": "main_box",
      "description": "Human-readable instruction for the operator",
      "timeout_seconds": 30,
      "next_step": "S02",
      "required_evidence": ["hand_contact"],
      "confidence_threshold": 0.85,
      "recovery_options": ["voice_prompt"]
    }
  ]
}

- step_id format: "S01", "S02", ..., "S10", "S11", etc.
- If a step is the final step, set next_step to null.
- required_evidence options: "hand_contact", "object_movement", "hand_interaction", "lid_state_change", "continuous_tracking", "spatial_translation", "timed_action", "tool_mediated"
- recovery_options: "voice_prompt", "highlight_object", "check_dropped", "containment_alert", "abort_procedure", "timer_display"
"""

def extract_json(text: str) -> str:
    """Extract JSON from the LLM's raw output in case it includes conversational text."""
    
    match = re.search(r"(\{.*\})", text, re.DOTALL)
    if match:
        return match.group(1)
    return text

def compile_manual(input_file: str, output_file: str, model_id: str = DEFAULT_MODEL):
    print("=" * 60)
    print("  BAS-APG Zero-Shot Protocol Compiler")
    print("=" * 60)

    if not os.path.exists(input_file):
        print(f"ERROR: Input manual not found at {input_file}")
        sys.exit(1)

    with open(input_file, "r") as f:
        manual_text = f.read()

    print(
        f"Loading local VLM/LLM: {model_id} (This may take a moment to download on first run)..."
    )

    try:
        
        tokenizer = AutoTokenizer.from_pretrained(model_id)
        model = AutoModelForCausalLM.from_pretrained(
            model_id,
            device_map="auto" if torch.cuda.is_available() else "cpu",
            torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
        )

        generator = pipeline("text-generation", model=model, tokenizer=tokenizer)
    except Exception as e:
        print(f"Failed to load model: {e}")
        sys.exit(1)

    print("\nParsing manual offline...")

    
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Manual:\n{manual_text}\n\nOutput only JSON:"},
    ]

    prompt = tokenizer.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True
    )

    outputs = generator(prompt, max_new_tokens=1024, do_sample=False, temperature=0.0)

    raw_output = outputs[0]["generated_text"][len(prompt) :]

    print("\nParsing LLM Output...")
    json_str = extract_json(raw_output)

    try:
        fsm_dict = json.loads(json_str)
        print("✅ Successfully parsed JSON!")
    except json.JSONDecodeError as e:
        print(f"❌ Failed to parse JSON. Raw output from LLM:\n{json_str}")
        print(f"Error: {e}")
        sys.exit(1)

    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, "w") as f:
        json.dump(fsm_dict, f, indent=4)

    print(f"\n✅ Dynamic Procedure compiled and saved to {output_file}")
    print(
        f"The BAS-APG system can now execute '{fsm_dict.get('procedure_name')}' natively."
    )

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input", default="data/manual.txt", help="Path to plain-text manual"
    )
    parser.add_argument(
        "--output",
        default="data/generated_procedure.json",
        help="Output path for FSM JSON",
    )
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Hugging Face model ID")
    args = parser.parse_args()

    compile_manual(args.input, args.output, args.model)

if __name__ == "__main__":
    main()
