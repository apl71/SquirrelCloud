import hashlib
import os
from datetime import datetime
from flask import current_app
import requests, re
import subprocess, sys
import re

def hash_file(path: str) -> str:
    f = open(path, "rb")
    digest = hashlib.file_digest(f, "sha3-512")
    return digest.hexdigest()

def get_directory_size(path):
    total_size = 0
    for dirpath, _, filenames in os.walk(path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            total_size += os.path.getsize(fp)
    return total_size

def replace_prefix(text, prefix, new_prefix):
    if text.startswith(prefix):
        return new_prefix + text[len(prefix):]
    else:
        return text

LEVEL_DEBUG = 0
LEVEL_INFO = 1
LEVEL_WARNING = 2
LEVEL_CRITICAL = 3

def log_level_to_str(level: int) -> str:
    if level == LEVEL_DEBUG:
        return " DEBUG  "
    elif level == LEVEL_INFO:
        return "  INFO  "
    elif level == LEVEL_WARNING:
        return "WARNING "
    elif level == LEVEL_CRITICAL:
        return "CRITICAL"
    else:
        return "UNKNOWN"

def log(level: int, data: str):
    ## get log level
    sys_log_level = current_app.config["LOG_LEVEL"]
    if level < 1 and sys_log_level == "INFO":
        return
    elif level < 2 and sys_log_level == "WARNING":
        return
    elif level < 3 and sys_log_level == "CRITICAL":
        return
    
    now = datetime.now()
    log_file_time = now.strftime("%Y-%m-%d")
    log_time = now.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    log_file = "{}/LOG_{}.log".format(current_app.config["LOG_PATH"], log_file_time)

    try:
        # 尝试打开文件
        with open(log_file, 'a') as f:
            f.write("[{}][{}] {}\n".format(log_time, log_level_to_str(level), data))
    except FileNotFoundError:
        print("Warning: Cannot open log file: {} does not exist.".format(log_file))
    except PermissionError:
        print("Warning: Cannot open log file: {} permission denied.".format(log_file))
    except Exception as e:
        print("Warning: Cannot open log file: {} unknown error.".format(log_file))

def kill_program():
    ## use docker to restart programe
    ## so --restart=always is necessary
    if current_app.config["DEBUG"] == "ON":
        os.system("pkill python")
    else:
        os.system("pkill gunicorn")

def check_update() -> str:
    ## get latest version
    url = "{}/api/latest".format(current_app.config["UPDATE_SERVER"])
    latest = requests.get(url).json()["version"].strip()
    if bool(re.match(r'^.+\..+\..+$', latest)):
        return latest
    else:
        return None

def install_requirements(requirements_file: str) -> list[bool, str]:
    if not os.path.isfile(requirements_file):
        return False, "Requirements file not found."
    ## install requirements
    try:
        result = subprocess.run([sys.executable, "-m", "pip", "install", "-r", requirements_file], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode == 0:
            return True, None
        else:
            return False, result.stderr
    except Exception as e:
        return False, str(e)

## parser for search query language
TOKEN_REGEX = [
    ("LPAREN", r"\("),
    ("RPAREN", r"\)"),
    ("AND", r"\bAND\b"),
    ("OR", r"\bOR\b"),
    ("NOT", r"\bNOT\b"),
    ("GT", r">"),
    ("LT", r"<"),
    ("COLON", r":"),
    ('SIZE_LITERAL',   r'\d+(?:\.\d+)?(?:[kKmMgG][bB])'),
    ("TERM", r"[a-zA-Z0-9_]+"),
    ("SPACE", r"\s+"),
]

token_pattern = re.compile("|".join(f"(?P<{name}>{regex})" for name, regex in TOKEN_REGEX))

def tokenize(query: str):
    tokens = []
    for match in token_pattern.finditer(query):
        kind = match.lastgroup
        if kind != "SPACE":
            tokens.append((kind, match.group()))
    return tokens

class Node:
    pass

class AndNode(Node):
    def __init__(self, left, right):
        self.left = left
        self.right = right

class OrNode(Node):
    def __init__(self, left, right):
        self.left = left
        self.right = right

class NotNode(Node):
    def __init__(self, child):
        self.child = child

class FilterNode(Node):
    def __init__(self, field, op, value):
        self.field = field  # e.g. 'name', 'type', 'size', 'modified'
        self.op = op        # ':', '>', '<'
        self.value = value  # e.g. 'report', 'pdf', '1MB'

class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    def peek(self):
        return self.tokens[self.pos] if self.pos < len(self.tokens) else (None, None)

    def eat(self, expected_type=None):
        token = self.peek()
        if expected_type and token[0] != expected_type:
            raise SyntaxError(f"Expected {expected_type}, got {token}")
        self.pos += 1
        return token

    def parse(self):
        return self.parse_or()

    def parse_or(self):
        node = self.parse_and()
        while self.peek()[0] == 'OR':
            self.eat('OR')
            right = self.parse_and()
            node = OrNode(node, right)
        return node

    def parse_and(self):
        node = self.parse_not()
        while self.peek()[0] == 'AND':
            self.eat('AND')
            right = self.parse_not()
            node = AndNode(node, right)
        return node

    def parse_not(self):
        if self.peek()[0] == 'NOT':
            self.eat('NOT')
            return NotNode(self.parse_not())
        else:
            return self.parse_term()

    def parse_term(self):
        tok_type, tok_val = self.peek()
        if tok_type == 'LPAREN':
            self.eat('LPAREN')
            node = self.parse()
            self.eat('RPAREN')
            return node
        else:
            return self.parse_filter()

    def parse_filter(self):
        """
        Parse a single “field op value” expression, e.g.
        name:report
        size>1.2MB
        modified<=2023-01-01
        Returns a FilterNode(field, op, value).
        """

        # 1. Field name must be a bare TERM
        tok_type, tok_val = self.eat('TERM')  
        field = tok_val

        # 2. Operator can be COLON, GT, LT, GE, or LE
        next_type, next_val = self.peek()
        if next_type in ('COLON', 'GT', 'LT', 'GE', 'LE'):
            op_type, op = self.eat(next_type)
        else:
            raise SyntaxError(f"Expected :, >, <, >=, or <= after field {field!r}, got {next_type}")

        # 3. Value can be a TERM (names, types) or SIZE_LITERAL (e.g. 1.2MB)
        val_type, val = self.peek()
        if val_type in ('TERM', 'SIZE_LITERAL'):
            _, value = self.eat(val_type)
        else:
            raise SyntaxError(f"Expected TERM or SIZE_LITERAL after operator {op}, got {val_type}")

        return FilterNode(field, op, value)

def evaluate(node, file):
    if isinstance(node, AndNode):
        return evaluate(node.left, file) and evaluate(node.right, file)
    elif isinstance(node, OrNode):
        return evaluate(node.left, file) or evaluate(node.right, file)
    elif isinstance(node, NotNode):
        return not evaluate(node.child, file)
    elif isinstance(node, FilterNode):
        field_val = file.get(node.field)
        op = node.op
        value = node.value

        # Size comparison
        if node.field == 'size':
            num = parse_size(value)
            return (field_val > num if op == '>' else field_val < num)
        # Date comparison
        elif node.field == 'modified':
            date_val = datetime.fromisoformat(field_val)
            compare_val = datetime.fromisoformat(value)
            return (date_val > compare_val if op == '>' else date_val < compare_val)
        # Text comparison (name/type)
        else:
            if op == ':':
                return value.lower() in str(field_val).lower()
        return False

def parse_size(s):
    s = s.lower()
    if s.endswith("kb"):
        return int(float(s[:-2]) * 1024)
    elif s.endswith("mb"):
        return int(float(s[:-2]) * 1024**2)
    elif s.endswith("gb"):
        return int(float(s[:-2]) * 1024**3)
    else:
        return int(s)

def ast_to_sql(node, param_index=[0]):
    """
    Recursively walk the AST and return (sql_fragment, params_dict).
    `param_index` is a one‐element list so we can mutate it as we recurse.
    """
    if isinstance(node, AndNode):
        left_sql, left_params  = ast_to_sql(node.left,  param_index)
        right_sql, right_params = ast_to_sql(node.right, param_index)
        return f"({left_sql} AND {right_sql})", {**left_params, **right_params}

    if isinstance(node, OrNode):
        left_sql, left_params  = ast_to_sql(node.left,  param_index)
        right_sql, right_params = ast_to_sql(node.right, param_index)
        return f"({left_sql} OR {right_sql})", {**left_params, **right_params}

    if isinstance(node, NotNode):
        child_sql, child_params = ast_to_sql(node.child, param_index)
        return f"(NOT {child_sql})", child_params

    # FilterNode
    if isinstance(node, FilterNode):
        idx = param_index[0]
        param_index[0] += 1

        fld   = node.field.lower()
        op    = node.op
        value = node.value

        if fld == 'name':
            # ILIKE for case‐insensitive substring
            key = f"name_param_{idx}"
            return f"path ILIKE %({key})s", {key: f"%{value}%"}
        elif fld == 'type':
            key = f"type_param_{idx}"
            return f"type = %({key})s", {key: value}
        elif fld == 'size':
            num = parse_size(value)
            key = f"size_param_{idx}"
            sql_op = '>' if op == '>' else '<'
            return f"size {sql_op} %({key})s", {key: num}
        elif fld == 'modified':
            key = f"mod_param_{idx}"
            sql_op = '>' if op == '>' else '<'
            return f"modified {sql_op} %({key})s", {key: value}
        else:
            raise ValueError(f"Unknown field {fld!r}")

    raise ValueError(f"Unexpected AST node: {node}")

if __name__ == "__main__":
    query = "(type:pdf OR type:docx) AND name:report"
    query = "name:Z3 AND (type:TYPE_FILE AND size > 1.2MB)"
    tokens = tokenize(query)
    parser = Parser(tokens)
    ast = parser.parse()

    file = {
        "name": "report_final.pdf",
        "type": "pdf",
        "size": 1_200_000,
        "modified": "2023-12-01"
    }

    wheresql, params = ast_to_sql(ast)
    print(wheresql)
    print(params)