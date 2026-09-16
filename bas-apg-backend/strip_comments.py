import os
import glob
import tokenize
import io

def remove_comments(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        source = f.read()

    result = []
    try:
        # Use tokenize to parse and rewrite tokens, dropping COMMENT tokens
        # but keeping everything else intact (including docstrings, which are STRINGs).
        tokens = tokenize.generate_tokens(io.StringIO(source).readline)
        
        last_lineno = -1
        last_col = 0
        
        for tok in tokens:
            token_type = tok[0]
            token_string = tok[1]
            start_line, start_col = tok[2]
            end_line, end_col = tok[3]
            
            if start_line > last_lineno:
                last_col = 0
            if start_col > last_col:
                result.append(" " * (start_col - last_col))
                
            if token_type != tokenize.COMMENT:
                result.append(token_string)
                
            last_lineno = end_line
            last_col = end_col
            
        new_source = "".join(result)
        
        # Clean up excessive blank lines
        lines = new_source.split('\n')
        clean_lines = []
        consecutive_blanks = 0
        for line in lines:
            if line.strip() == '':
                consecutive_blanks += 1
                if consecutive_blanks <= 2:
                    clean_lines.append(line)
            else:
                consecutive_blanks = 0
                clean_lines.append(line)
                
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(clean_lines))
            
        return True
    except Exception as e:
        print(f"Error stripping {file_path}: {e}")
        return False

# Target directories
dirs = [
    "/Users/atulharshvardhan/Desktop/BAS-APG-Workspace/bas-apg-backend/app/core",
    "/Users/atulharshvardhan/Desktop/BAS-APG-Workspace/bas-apg-backend/app/engines",
    "/Users/atulharshvardhan/Desktop/BAS-APG-Workspace/bas-apg-backend/app/api",
    "/Users/atulharshvardhan/Desktop/BAS-APG-Workspace/bas-apg-backend/app"
]

count = 0
for d in dirs:
    for root, _, files in os.walk(d):
        for file in files:
            if file.endswith(".py"):
                path = os.path.join(root, file)
                if remove_comments(path):
                    count += 1

print(f"Successfully cleaned comments from {count} Python files!")
