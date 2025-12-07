
def _format_log_line(line):
    line = line.strip()
    if "ERROR" in line:
        return f'<span class="log-error">{line}</span>'
    elif "WARNING" in line:
        return f'<span class="log-warning">{line}</span>'
    elif "INFO" in line:
        return f'<span class="log-info">{line}</span>'
    return line

def get_log_data(path, line_limit : int = 1000):
    with open(path, 'r') as f:        
        lines = f.readlines()
        filtered = lines[-line_limit:]
        reversed_lines  = filtered[::-1]
        # Apply basic formatting for the display
        return [_format_log_line(line) for line in reversed_lines]

def clear_log_data(path):
    with open(path, 'w') as f:
        lines = f.write("")

