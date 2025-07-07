import os

def reformate_print_output_to_markdown(file_path:str,save_to_file:bool=False) -> str:
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            contents = f.readlines()
    else:
        return ""
    result = []
    for line in contents:
        line = line.replace("â”ƒ", "")
        line = line.replace("â€¢ ", "- ")
        line = line.strip()
        result.append(line)
    if save_to_file:
        with open(file_path+".md", "w", encoding="utf-8") as f:
            f.write("\n".join(result))
    return "\n".join(result)

