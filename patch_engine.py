import os

path = '/Users/atulharshvardhan/Desktop/BAS-APG-Workspace/scratch_engine.py'
lines = open(path).readlines()

new_lines = []
for line in lines:
    if "step_age >=" in line and "8.0" in line:
        line = line.replace("8.0", "7.0")
    if "step need to perform." in line:
        line = line.replace("step need to perform.", "step need to complete.")
    
    if "if MissionState.demo_started and cur_state == \"IN_PROGRESS\" and current_step and current_step.object != \"procedure\":" in line:
        new_lines.append("        if hasattr(fsm, '_delayed_speak_time') and fsm._delayed_speak_time and time.time() >= fsm._delayed_speak_time:\n")
        new_lines.append("            speak(fsm._delayed_speak_msg)\n")
        new_lines.append("            fsm._delayed_speak_time = None\n")
        new_lines.append("\n")
    
    new_lines.append(line)

code = "".join(new_lines)
old_speak_logic = """            if cur_state == "IN_PROGRESS" and cur_step > last_voice_step and cur_step > 0:
                if cur_step <= len(STEP_NAMES):
                    msg = f"{STEP_NAMES[cur_step - 1]} complete. Proceeding to next step."
                    speak(msg)"""

new_speak_logic = """            if cur_state == "IN_PROGRESS" and cur_step > last_voice_step and cur_step > 0:
                if cur_step <= len(STEP_NAMES):
                    completed_step_name = STEP_NAMES[cur_step - 2] if cur_step > 1 else ""
                    if completed_step_name in ["Detect Red Box", "Detect Yellow Box"]:
                        fsm._delayed_speak_time = time.time() + 3.0
                        fsm._delayed_speak_msg = "show open boxes"
                    else:
                        msg = f"{completed_step_name} complete. Proceeding to next step." if completed_step_name else "Started."
                        speak(msg)"""

if old_speak_logic in code:
    code = code.replace(old_speak_logic, new_speak_logic)
    print("Replaced speak logic.")
else:
    print("Failed to find old speak logic.")

with open('/Users/atulharshvardhan/Desktop/BAS-APG-Workspace/bas-apg-backend/app/core/engine.py', 'w') as f:
    f.write(code)
print("Saved to engine.py")
