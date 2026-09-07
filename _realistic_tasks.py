# Realistic 60-task bank ported from the pro kit.
# 14 multi-file assembly CLI tasks + 46 single-function tasks.
REALISTIC_TASKS = [
  {
    "id": "filter",
    "wiring_file": "run_filter.py",
    "task_desc": "Write a CLI tool that reads a CSV file, filters rows by a column value, and writes the matching rows as JSON. Accept args: --input <csv_path>, --column <name>, --value <val>, --output <json_path>. Print 'Filtered N rows' to stdout. Handle missing input file with a clear error message and exit code 1. Handle a column name that does not exist in the CSV the same way: a clear error message and a nonzero exit code, not a crash.",
    "siblings": [
      {
        "filename": "csv_reader.py",
        "source": "import csv, json\n\ndef read_csv(path):\n    with open(path, newline='', encoding='utf-8') as f:\n        reader = csv.DictReader(f)\n        return list(reader)\n\ndef write_json(rows, path):\n    with open(path, 'w', encoding='utf-8') as f:\n        json.dump(rows, f, indent=2)\n",
        "interfaces": "csv_reader.py: read_csv(path: str) -> list[dict], write_json(rows: list[dict], path: str) -> None"
      },
      {
        "filename": "filter_rows.py",
        "source": "def filter_by_column(rows, column, value):\n    if rows and column not in rows[0]:\n        raise KeyError(f'Column {column} not found')\n    return [r for r in rows if r.get(column) == value]\n\ndef filter_by_predicate(rows, predicate):\n    return [r for r in rows if predicate(r)]\n",
        "interfaces": "filter_rows.py: filter_by_column(rows: list[dict], column: str, value: str) -> list[dict], filter_by_predicate(rows: list[dict], predicate: callable) -> list[dict]"
      }
    ],
    "tests": [
      [
        "correct_filtering",
        "\nimport subprocess, json, csv, os, tempfile\nd = tempfile.mkdtemp()\ncsv_path = os.path.join(d, 'data.csv')\nwith open(csv_path, 'w', newline='') as f:\n    w = csv.DictWriter(f, fieldnames=['name', 'city'])\n    w.writeheader()\n    w.writerow({'name': 'Alice', 'city': 'NYC'})\n    w.writerow({'name': 'Bob', 'city': 'LA'})\n    w.writerow({'name': 'Carol', 'city': 'NYC'})\nout_path = os.path.join(d, 'out.json')\nr = subprocess.run([sys.executable, 'run_filter.py', '--input', csv_path, '--column', 'city', '--value', 'NYC', '--output', out_path],\n    capture_output=True, text=True, timeout=10, cwd=d)\nassert r.returncode == 0, f'exit {r.returncode}: {r.stderr}'\nwith open(out_path) as f:\n    data = json.load(f)\nassert len(data) == 2, f'expected 2 rows, got {len(data)}'\nassert all(r['city'] == 'NYC' for r in data)\nprint('PASS')\n"
      ],
      [
        "missing_file",
        "\nimport subprocess, tempfile, os\nd = tempfile.mkdtemp()\nr = subprocess.run([sys.executable, 'run_filter.py', '--input', 'nope.csv', '--column', 'x', '--value', 'y', '--output', 'out.json'],\n    capture_output=True, text=True, timeout=10, cwd=d)\nassert r.returncode == 1, f'expected exit 1, got {r.returncode}'\nassert 'Traceback' not in r.stderr, f'crashed instead of handling error: {r.stderr[:200]}'\nassert r.stderr.strip() or r.stdout.strip(), 'no error message printed'\nprint('PASS')\n"
      ],
      [
        "missing_column",
        "\nimport subprocess, csv, tempfile, os\nd = tempfile.mkdtemp()\ncsv_path = os.path.join(d, 'data.csv')\nwith open(csv_path, 'w', newline='') as f:\n    w = csv.DictWriter(f, fieldnames=['name'])\n    w.writeheader()\n    w.writerow({'name': 'Alice'})\nr = subprocess.run([sys.executable, 'run_filter.py', '--input', csv_path, '--column', 'missing', '--value', 'x', '--output', os.path.join(d, 'o.json')],\n    capture_output=True, text=True, timeout=10, cwd=d)\nassert r.returncode != 0, f'expected nonzero exit, got {r.returncode}'\nassert 'Traceback' not in r.stderr, f'crashed instead of handling error: {r.stderr[:200]}'\nprint('PASS')\n"
      ],
      [
        "empty_result",
        "\nimport subprocess, csv, json, tempfile, os\nd = tempfile.mkdtemp()\ncsv_path = os.path.join(d, 'data.csv')\nwith open(csv_path, 'w', newline='') as f:\n    w = csv.DictWriter(f, fieldnames=['name', 'city'])\n    w.writeheader()\n    w.writerow({'name': 'Alice', 'city': 'NYC'})\nout_path = os.path.join(d, 'out.json')\nr = subprocess.run([sys.executable, 'run_filter.py', '--input', csv_path, '--column', 'city', '--value', 'LA', '--output', out_path],\n    capture_output=True, text=True, timeout=10, cwd=d)\nassert r.returncode == 0, f'exit {r.returncode}: {r.stderr}'\nwith open(out_path) as f:\n    data = json.load(f)\nassert data == [], f'expected empty list, got {data}'\nprint('PASS')\n"
      ]
    ],
    "type": "assembly"
  },
  {
    "id": "report",
    "wiring_file": "run_report.py",
    "task_desc": "Write a CLI tool that loads records from a JSON file, groups them by a column, sums another column per group, and saves the report as JSON. The output JSON is a plain object mapping each group name to its sum — no wrapper keys — so an empty input file produces {}. Accept args: --input <json_path>, --group-by <column>, --sum <column>, --output <json_path>. Print 'Report saved with N groups' to stdout. Handle missing input file with exit code 1.",
    "siblings": [
      {
        "filename": "data_loader.py",
        "source": "import json\n\ndef load_records(path):\n    with open(path, encoding='utf-8') as f:\n        return json.load(f)\n\ndef save_report(data, path):\n    with open(path, 'w', encoding='utf-8') as f:\n        json.dump(data, f, indent=2)\n",
        "interfaces": "data_loader.py: load_records(path: str) -> list[dict], save_report(data: dict, path: str) -> None"
      },
      {
        "filename": "aggregator.py",
        "source": "def sum_by_key(records, key):\n    total = 0\n    for r in records:\n        total += r.get(key, 0)\n    return total\n\ndef group_by(records, key):\n    groups = {}\n    for r in records:\n        val = r.get(key, 'unknown')\n        groups.setdefault(val, []).append(r)\n    return groups\n",
        "interfaces": "aggregator.py: sum_by_key(records: list[dict], key: str) -> float, group_by(records: list[dict], key: str) -> dict[str, list[dict]]"
      }
    ],
    "tests": [
      [
        "correct_grouping_sum",
        "\nimport subprocess, json, tempfile, os\nd = tempfile.mkdtemp()\ninp = os.path.join(d, 'data.json')\njson.dump([{'group': 'A', 'amount': 10}, {'group': 'A', 'amount': 20}, {'group': 'B', 'amount': 5}], open(inp, 'w'))\nout = os.path.join(d, 'report.json')\nr = subprocess.run([sys.executable, 'run_report.py', '--input', inp, '--group-by', 'group', '--sum', 'amount', '--output', out],\n    capture_output=True, text=True, timeout=10, cwd=d)\nassert r.returncode == 0, f'exit {r.returncode}: {r.stderr}'\ndata = json.load(open(out))\nassert data.get('A') == 30, f'A should be 30, got {data.get(\"A\")}'\nassert data.get('B') == 5, f'B should be 5, got {data.get(\"B\")}'\nprint('PASS')\n"
      ],
      [
        "missing_file",
        "\nimport subprocess, tempfile, os\nd = tempfile.mkdtemp()\nr = subprocess.run([sys.executable, 'run_report.py', '--input', 'nope.json', '--group-by', 'x', '--sum', 'y', '--output', 'o.json'],\n    capture_output=True, text=True, timeout=10, cwd=d)\nassert r.returncode == 1, f'expected exit 1, got {r.returncode}'\nassert 'Traceback' not in r.stderr, f'crashed instead of handling error: {r.stderr[:200]}'\nassert r.stderr.strip() or r.stdout.strip(), 'no error message printed'\nprint('PASS')\n"
      ],
      [
        "empty_input",
        "\nimport subprocess, json, tempfile, os\nd = tempfile.mkdtemp()\ninp = os.path.join(d, 'data.json')\njson.dump([], open(inp, 'w'))\nout = os.path.join(d, 'report.json')\nr = subprocess.run([sys.executable, 'run_report.py', '--input', inp, '--group-by', 'group', '--sum', 'amount', '--output', out],\n    capture_output=True, text=True, timeout=10, cwd=d)\nassert r.returncode == 0, f'exit {r.returncode}: {r.stderr}'\ndata = json.load(open(out))\nassert data == {}, f'expected empty dict, got {data}'\nprint('PASS')\n"
      ]
    ],
    "type": "assembly"
  },
  {
    "id": "cache",
    "wiring_file": "run_cache.py",
    "task_desc": "Write a CLI key-value cache tool. Accept subcommands: --set key value, --get key, --delete key, --list. Values are serialized before storing and deserialized on retrieval. Print the result of --get and --list to stdout. If --get on a missing key, print 'Key not found' and exit 1.",
    "siblings": [
      {
        "filename": "store.py",
        "source": "import json, os\n\n_path = 'cache_store.json'\n\ndef _load():\n    if os.path.exists(_path):\n        with open(_path, encoding='utf-8') as f:\n            return json.load(f)\n    return {}\n\ndef _save(data):\n    with open(_path, 'w', encoding='utf-8') as f:\n        json.dump(data, f)\n\ndef get(key):\n    return _load().get(key)\n\ndef set(key, value):\n    data = _load()\n    data[key] = value\n    _save(data)\n\ndef delete(key):\n    data = _load()\n    if key in data:\n        del data[key]\n        _save(data)\n\ndef list_keys():\n    return sorted(_load().keys())\n",
        "interfaces": "store.py: get(key: str) -> str|None, set(key: str, value: str) -> None, delete(key: str) -> None, list_keys() -> list[str]"
      },
      {
        "filename": "serializer.py",
        "source": "import json\n\ndef serialize(obj):\n    return json.dumps(obj)\n\ndef deserialize(data):\n    return json.loads(data)\n",
        "interfaces": "serializer.py: serialize(obj) -> str, deserialize(data: str) -> obj"
      }
    ],
    "tests": [
      [
        "set_get_roundtrip",
        "\nimport subprocess, sys, tempfile, os\nd = tempfile.mkdtemp()\n# set a value\nr = subprocess.run([sys.executable, 'run_cache.py', '--set', 'mykey', 'myvalue'],\n    capture_output=True, text=True, timeout=10, cwd=d)\nassert r.returncode == 0, f'set failed: {r.stderr}'\n# get it back\nr = subprocess.run([sys.executable, 'run_cache.py', '--get', 'mykey'],\n    capture_output=True, text=True, timeout=10, cwd=d)\nassert r.returncode == 0, f'get failed: {r.stderr}'\nassert 'myvalue' in r.stdout, f'expected myvalue in stdout, got {r.stdout}'\nprint('PASS')\n"
      ],
      [
        "get_missing",
        "\nimport subprocess, sys, tempfile, os\nd = tempfile.mkdtemp()\nr = subprocess.run([sys.executable, 'run_cache.py', '--get', 'nonexistent'],\n    capture_output=True, text=True, timeout=10, cwd=d)\nassert r.returncode == 1, f'expected exit 1, got {r.returncode}'\nassert 'Traceback' not in r.stderr, f'crashed instead of handling error: {r.stderr[:200]}'\nassert 'Key not found' in r.stdout or 'Key not found' in r.stderr, f'expected Key not found message, got stdout={r.stdout!r} stderr={r.stderr!r}'\nprint('PASS')\n"
      ],
      [
        "delete",
        "\nimport subprocess, sys, tempfile, os\nd = tempfile.mkdtemp()\nr1 = subprocess.run([sys.executable, 'run_cache.py', '--set', 'k', 'v'], cwd=d, timeout=10, capture_output=True, text=True)\nassert r1.returncode == 0, f'set failed: {r1.stderr}'\nr2 = subprocess.run([sys.executable, 'run_cache.py', '--delete', 'k'], cwd=d, timeout=10, capture_output=True, text=True)\nassert r2.returncode == 0, f'delete failed: {r2.stderr}'\nr = subprocess.run([sys.executable, 'run_cache.py', '--get', 'k'],\n    capture_output=True, text=True, timeout=10, cwd=d)\nassert r.returncode == 1, f'expected exit 1 after delete, got {r.returncode}'\nassert 'Traceback' not in r.stderr, f'crashed on get after delete: {r.stderr[:200]}'\nassert 'Key not found' in r.stdout or 'Key not found' in r.stderr, f'expected Key not found after delete, got stdout={r.stdout!r} stderr={r.stderr!r}'\nprint('PASS')\n"
      ]
    ],
    "type": "assembly"
  },
  {
    "id": "validator",
    "wiring_file": "run_validator.py",
    "task_desc": "Write a CLI tool that loads a JSON file, validates it against a schema JSON file, and writes validation errors to an output file. Accept args: --input <json_path>, --schema <schema_path>, --output <error_path>. Exit 0 if valid, exit 1 if validation errors found. Always write the output file: the list of error strings, which is an empty list when the data is valid.",
    "siblings": [
      {
        "filename": "schema.py",
        "source": "_TYPE_MAP = {'str': str, 'int': int, 'float': (int, float), 'bool': bool, 'list': list, 'dict': dict}\n\ndef validate(data, schema):\n    errors = get_errors(data, schema)\n    return len(errors) == 0\n\ndef get_errors(data, schema):\n    errors = []\n    for field, field_type in schema.items():\n        if field not in data:\n            errors.append(f'Missing required field: {field}')\n        elif not isinstance(data[field], _TYPE_MAP.get(field_type, object)):\n            errors.append(f'Field {field} has wrong type: expected {field_type}')\n    return errors\n",
        "interfaces": "schema.py: validate(data: dict, schema: dict) -> bool, get_errors(data: dict, schema: dict) -> list[str]"
      },
      {
        "filename": "loader.py",
        "source": "import json\n\ndef load_json(path):\n    with open(path, encoding='utf-8') as f:\n        return json.load(f)\n\ndef save_json(data, path):\n    with open(path, 'w', encoding='utf-8') as f:\n        json.dump(data, f, indent=2)\n",
        "interfaces": "loader.py: load_json(path: str) -> dict, save_json(data, path: str) -> None"
      }
    ],
    "tests": [
      [
        "valid_data",
        "\nimport subprocess, json, tempfile, os\nd = tempfile.mkdtemp()\ninp = os.path.join(d, 'data.json')\njson.dump({'name': 'Alice', 'age': 30}, open(inp, 'w'))\nsch = os.path.join(d, 'schema.json')\njson.dump({'name': 'str', 'age': 'int'}, open(sch, 'w'))\nout = os.path.join(d, 'errors.json')\nr = subprocess.run([sys.executable, 'run_validator.py', '--input', inp, '--schema', sch, '--output', out],\n    capture_output=True, text=True, timeout=10, cwd=d)\nassert r.returncode == 0, f'expected exit 0, got {r.returncode}: {r.stderr}'\nassert os.path.exists(out), f'output file {out} was not created on valid case'\nprint('PASS')\n"
      ],
      [
        "missing_field",
        "\nimport subprocess, json, tempfile, os\nd = tempfile.mkdtemp()\ninp = os.path.join(d, 'data.json')\njson.dump({'name': 'Alice'}, open(inp, 'w'))\nsch = os.path.join(d, 'schema.json')\njson.dump({'name': 'str', 'age': 'int'}, open(sch, 'w'))\nout = os.path.join(d, 'errors.json')\nr = subprocess.run([sys.executable, 'run_validator.py', '--input', inp, '--schema', sch, '--output', out],\n    capture_output=True, text=True, timeout=10, cwd=d)\nassert r.returncode == 1, f'expected exit 1, got {r.returncode}'\nassert 'Traceback' not in r.stderr, f'crashed instead of handling error: {r.stderr[:200]}'\nerrors = json.load(open(out))\nassert any('age' in e for e in errors), f'expected age error, got {errors}'\nprint('PASS')\n"
      ],
      [
        "missing_input",
        "\nimport subprocess, tempfile, os\nd = tempfile.mkdtemp()\nsch = os.path.join(d, 'schema.json')\nimport json; json.dump({}, open(sch, 'w'))\nr = subprocess.run([sys.executable, 'run_validator.py', '--input', 'nope.json', '--schema', sch, '--output', os.path.join(d, 'e.json')],\n    capture_output=True, text=True, timeout=10, cwd=d)\nassert r.returncode != 0, f'expected nonzero exit, got {r.returncode}'\nassert 'Traceback' not in r.stderr, f'crashed instead of handling error: {r.stderr[:200]}'\nprint('PASS')\n"
      ]
    ],
    "type": "assembly"
  },
  {
    "id": "pipeline",
    "wiring_file": "run_pipeline.py",
    "task_desc": "Write a CLI tool that reads lines from a file, transforms each line, and writes the result to an output file. Accept args: --input <path>, --output <path>, --mode <upper|trim|reverse>. Print 'Processed N lines' to stdout.",
    "siblings": [
      {
        "filename": "reader.py",
        "source": "def read_lines(path):\n    with open(path, encoding='utf-8') as f:\n        return f.read().splitlines()\n\ndef write_lines(lines, path):\n    with open(path, 'w', encoding='utf-8') as f:\n        f.write('\\n'.join(lines) + '\\n')\n",
        "interfaces": "reader.py: read_lines(path: str) -> list[str], write_lines(lines: list[str], path: str) -> None"
      },
      {
        "filename": "transformer.py",
        "source": "def transform(line, mode):\n    if mode == 'upper':\n        return line.upper()\n    elif mode == 'trim':\n        return line.strip()\n    elif mode == 'reverse':\n        return line[::-1]\n    return line\n",
        "interfaces": "transformer.py: transform(line: str, mode: str) -> str  (modes: 'upper', 'trim', 'reverse')"
      }
    ],
    "tests": [
      [
        "upper_mode",
        "\nimport subprocess, tempfile, os\nd = tempfile.mkdtemp()\ninp = os.path.join(d, 'in.txt')\nopen(inp, 'w').write('hello\\nworld\\n')\nout = os.path.join(d, 'out.txt')\nr = subprocess.run([sys.executable, 'run_pipeline.py', '--input', inp, '--output', out, '--mode', 'upper'],\n    capture_output=True, text=True, timeout=10, cwd=d)\nassert r.returncode == 0, f'exit {r.returncode}: {r.stderr}'\nresult = open(out).read()\nassert 'HELLO' in result and 'WORLD' in result, f'expected uppercase, got {result}'\nprint('PASS')\n"
      ],
      [
        "trim_mode",
        "\nimport subprocess, tempfile, os\nd = tempfile.mkdtemp()\ninp = os.path.join(d, 'in.txt')\nopen(inp, 'w').write('  hello  \\n  world  \\n')\nout = os.path.join(d, 'out.txt')\nr = subprocess.run([sys.executable, 'run_pipeline.py', '--input', inp, '--output', out, '--mode', 'trim'],\n    capture_output=True, text=True, timeout=10, cwd=d)\nassert r.returncode == 0, f'exit {r.returncode}: {r.stderr}'\nresult = open(out).read().splitlines()\nassert result[0] == 'hello', f'expected trimmed, got {result}'\nprint('PASS')\n"
      ],
      [
        "reverse_mode",
        "\nimport subprocess, tempfile, os\nd = tempfile.mkdtemp()\ninp = os.path.join(d, 'in.txt')\nopen(inp, 'w').write('abc\\ndef\\n')\nout = os.path.join(d, 'out.txt')\nr = subprocess.run([sys.executable, 'run_pipeline.py', '--input', inp, '--output', out, '--mode', 'reverse'],\n    capture_output=True, text=True, timeout=10, cwd=d)\nassert r.returncode == 0, f'exit {r.returncode}: {r.stderr}'\nresult = open(out).read().splitlines()\nassert result[0] == 'cba', f'expected reversed, got {result}'\nprint('PASS')\n"
      ],
      [
        "empty_input",
        "\nimport subprocess, tempfile, os\nd = tempfile.mkdtemp()\ninp = os.path.join(d, 'empty.txt')\nopen(inp, 'w').write('')\nout = os.path.join(d, 'out.txt')\nr = subprocess.run([sys.executable, 'run_pipeline.py', '--input', inp, '--output', out, '--mode', 'upper'],\n    capture_output=True, text=True, timeout=10, cwd=d)\nassert r.returncode == 0, f'exit {r.returncode}: {r.stderr}'\nprint('PASS')\n"
      ]
    ],
    "type": "assembly"
  },
  {
    "id": "merger",
    "wiring_file": "run_merger.py",
    "task_desc": "Write a CLI tool that reads two sorted text files, merges them into one sorted output, removing duplicate lines. Accept args: --input1 <path>, --input2 <path>, --output <path>. Print 'Merged N lines' to stdout. If either input file is missing, print an error and exit 1.",
    "siblings": [
      {
        "filename": "file_io.py",
        "source": "def read_lines(path):\n    with open(path, encoding='utf-8') as f:\n        return [line.rstrip('\\n') for line in f if line.strip()]\n\ndef write_lines(lines, path):\n    with open(path, 'w', encoding='utf-8') as f:\n    for line in lines:\n        f.write(line + '\\n')\n",
        "interfaces": "file_io.py: read_lines(path: str) -> list[str], write_lines(lines: list[str], path: str) -> None"
      },
      {
        "filename": "merge_util.py",
        "source": "def merge_sorted(a, b):\n    result = []\n    i = j = 0\n    while i < len(a) and j < len(b):\n        if a[i] <= b[j]:\n            if not result or result[-1] != a[i]:\n                result.append(a[i])\n            i += 1\n        else:\n            if not result or result[-1] != b[j]:\n                result.append(b[j])\n            j += 1\n    for k in range(i, len(a)):\n        if not result or result[-1] != a[k]:\n            result.append(a[k])\n    for k in range(j, len(b)):\n        if not result or result[-1] != b[k]:\n            result.append(b[k])\n    return result\n",
        "interfaces": "merge_util.py: merge_sorted(a: list[str], b: list[str]) -> list[str]  (merges two sorted lists, removes duplicates)"
      }
    ],
    "tests": [
      [
        "correct_merge",
        "\nimport subprocess, tempfile, os\nd = tempfile.mkdtemp()\nf1 = os.path.join(d, 'a.txt')\nf2 = os.path.join(d, 'b.txt')\nopen(f1, 'w').write('apple\\ncherry\\nelderberry\\n')\nopen(f2, 'w').write('banana\\ncherry\\nfig\\n')\nout = os.path.join(d, 'out.txt')\nr = subprocess.run([sys.executable, 'run_merger.py', '--input1', f1, '--input2', f2, '--output', out],\n    capture_output=True, text=True, timeout=10, cwd=d)\nassert r.returncode == 0, f'exit {r.returncode}: {r.stderr}'\nresult = open(out).read().splitlines()\nassert result == ['apple', 'banana', 'cherry', 'elderberry', 'fig'], f'got {result}'\nprint('PASS')\n"
      ],
      [
        "dedup_same_file",
        "\nimport subprocess, tempfile, os\nd = tempfile.mkdtemp()\nf1 = os.path.join(d, 'a.txt')\nf2 = os.path.join(d, 'b.txt')\nopen(f1, 'w').write('a\\nb\\nc\\n')\nopen(f2, 'w').write('a\\nb\\nc\\n')\nout = os.path.join(d, 'out.txt')\nr = subprocess.run([sys.executable, 'run_merger.py', '--input1', f1, '--input2', f2, '--output', out],\n    capture_output=True, text=True, timeout=10, cwd=d)\nassert r.returncode == 0, f'exit {r.returncode}: {r.stderr}'\nresult = open(out).read().splitlines()\nassert result == ['a', 'b', 'c'], f'duplicates not removed: {result}'\nprint('PASS')\n"
      ],
      [
        "missing_file",
        "\nimport subprocess, tempfile, os\nd = tempfile.mkdtemp()\nf1 = os.path.join(d, 'a.txt')\nopen(f1, 'w').write('a\\n')\nout = os.path.join(d, 'out.txt')\nr = subprocess.run([sys.executable, 'run_merger.py', '--input1', f1, '--input2', 'nope.txt', '--output', out],\n    capture_output=True, text=True, timeout=10, cwd=d)\nassert r.returncode == 1, f'expected exit 1, got {r.returncode}'\nassert 'Traceback' not in r.stderr, f'crashed: {r.stderr[:200]}'\nprint('PASS')\n"
      ]
    ],
    "type": "assembly"
  },
  {
    "id": "counter",
    "wiring_file": "run_counter.py",
    "task_desc": "Write a CLI tool that counts word frequencies in a text file, excluding stop words. Accept args: --input <path>, --stop <path>, --output <json_path>. The stop words file has one word per line. Output a JSON object mapping word -> count, sorted by count descending. Print 'Counted N unique words' to stdout. Missing input → exit 1.",
    "siblings": [
      {
        "filename": "text_proc.py",
        "source": "import re\n\ndef tokenize(text):\n    return [w.lower() for w in re.findall(r'[a-zA-Z]+', text)]\n\ndef load_stopwords(path):\n    with open(path, encoding='utf-8') as f:\n        return set(line.strip().lower() for line in f if line.strip())\n",
        "interfaces": "text_proc.py: tokenize(text: str) -> list[str], load_stopwords(path: str) -> set[str]"
      },
      {
        "filename": "freq.py",
        "source": "from collections import Counter\n\ndef count_words(words, stopwords):\n    filtered = [w for w in words if w not in stopwords]\n    return Counter(filtered)\n\ndef sort_by_count(counter):\n    return dict(sorted(counter.items(), key=lambda x: (-x[1], x[0])))\n",
        "interfaces": "freq.py: count_words(words: list[str], stopwords: set[str]) -> Counter, sort_by_count(counter: Counter) -> dict[str, int]"
      }
    ],
    "tests": [
      [
        "correct_count",
        "\nimport subprocess, json, tempfile, os\nd = tempfile.mkdtemp()\ninp = os.path.join(d, 'text.txt')\nopen(inp, 'w').write('the cat sat on the mat\\nthe dog sat too\\n')\nstop = os.path.join(d, 'stop.txt')\nopen(stop, 'w').write('the\\non\\ntoo\\n')\nout = os.path.join(d, 'out.json')\nr = subprocess.run([sys.executable, 'run_counter.py', '--input', inp, '--stop', stop, '--output', out],\n    capture_output=True, text=True, timeout=10, cwd=d)\nassert r.returncode == 0, f'exit {r.returncode}: {r.stderr}'\ndata = json.load(open(out))\nassert data.get('cat') == 1, f'cat should be 1, got {data.get(\"cat\")}'\nassert data.get('sat') == 2, f'sat should be 2, got {data.get(\"sat\")}'\nassert 'the' not in data, f'the should be filtered as stop word'\nassert 'too' not in data, f'too should be filtered'\nprint('PASS')\n"
      ],
      [
        "sorted_descending",
        "\nimport subprocess, json, tempfile, os\nd = tempfile.mkdtemp()\ninp = os.path.join(d, 'text.txt')\nopen(inp, 'w').write('apple apple apple banana banana cherry\\n')\nstop = os.path.join(d, 'stop.txt')\nopen(stop, 'w').write('')\nout = os.path.join(d, 'out.json')\nr = subprocess.run([sys.executable, 'run_counter.py', '--input', inp, '--stop', stop, '--output', out],\n    capture_output=True, text=True, timeout=10, cwd=d)\nassert r.returncode == 0, f'exit {r.returncode}: {r.stderr}'\ndata = json.load(open(out))\nkeys = list(data.keys())\nassert keys[0] == 'apple', f'first should be apple (3), got {keys[0]}'\nassert keys[1] == 'banana', f'second should be banana (2), got {keys[1]}'\nprint('PASS')\n"
      ],
      [
        "missing_input",
        "\nimport subprocess, tempfile, os\nd = tempfile.mkdtemp()\nstop = os.path.join(d, 'stop.txt')\nopen(stop, 'w').write('')\nout = os.path.join(d, 'out.json')\nr = subprocess.run([sys.executable, 'run_counter.py', '--input', 'nope.txt', '--stop', stop, '--output', out],\n    capture_output=True, text=True, timeout=10, cwd=d)\nassert r.returncode == 1, f'expected exit 1, got {r.returncode}'\nassert 'Traceback' not in r.stderr, f'crashed: {r.stderr[:200]}'\nprint('PASS')\n"
      ]
    ],
    "type": "assembly"
  },
  {
    "id": "scheduler",
    "wiring_file": "run_scheduler.py",
    "task_desc": "Write a CLI tool that processes a list of tasks from a JSON file and outputs their execution schedule. Each task has: id, priority (1-3), depends_on (list of task ids). Output a JSON list of task ids in execution order: tasks with no dependencies first, then tasks whose dependencies are all done. Within each level, order by priority (1 highest). Accept args: --input <json_path>, --output <json_path>. If a task has a circular dependency, print 'Circular dependency detected' and exit 1. Missing input → exit 1.",
    "siblings": [
      {
        "filename": "task_loader.py",
        "source": "import json\n\ndef load_tasks(path):\n    with open(path, encoding='utf-8') as f:\n        return json.load(f)\n\ndef save_schedule(order, path):\n    with open(path, 'w', encoding='utf-8') as f:\n    json.dump(order, f, indent=2)\n",
        "interfaces": "task_loader.py: load_tasks(path: str) -> list[dict], save_schedule(order: list[str], path: str) -> None"
      },
      {
        "filename": "dependency.py",
        "source": "def has_circular_dep(tasks):\n    task_map = {t['id']: t for t in tasks}\n    visited = set()\n    stack = set()\n    def check(tid):\n        if tid in stack:\n            return True\n        if tid in visited:\n            return False\n        visited.add(tid)\n        stack.add(tid)\n        task = task_map.get(tid)\n        if task:\n            for dep in task.get('depends_on', []):\n                if check(dep):\n                    return True\n        stack.discard(tid)\n        return False\n    return any(check(t['id']) for t in tasks)\n\ndef topological_sort(tasks):\n    task_map = {t['id']: t for t in tasks}\n    done = set()\n    order = []\n    remaining = list(tasks)\n    while remaining:\n        ready = [t for t in remaining if all(d in done for d in t.get('depends_on', []))]\n        if not ready:\n            return None\n        ready.sort(key=lambda t: (t.get('priority', 3), t['id']))\n        for t in ready:\n            order.append(t['id'])\n            done.add(t['id'])\n            remaining.remove(t)\n    return order\n",
        "interfaces": "dependency.py: has_circular_dep(tasks: list[dict]) -> bool, topological_sort(tasks: list[dict]) -> list[str]|None  (returns task ids in execution order, or None if cycle)"
      }
    ],
    "tests": [
      [
        "correct_order",
        "\nimport subprocess, json, tempfile, os\nd = tempfile.mkdtemp()\ninp = os.path.join(d, 'tasks.json')\njson.dump([\n    {'id': 'c', 'priority': 2, 'depends_on': ['a', 'b']},\n    {'id': 'a', 'priority': 1, 'depends_on': []},\n    {'id': 'b', 'priority': 2, 'depends_on': ['a']},\n], open(inp, 'w'))\nout = os.path.join(d, 'out.json')\nr = subprocess.run([sys.executable, 'run_scheduler.py', '--input', inp, '--output', out],\n    capture_output=True, text=True, timeout=10, cwd=d)\nassert r.returncode == 0, f'exit {r.returncode}: {r.stderr}'\norder = json.load(open(out))\nassert order == ['a', 'b', 'c'], f'expected [a,b,c], got {order}'\nprint('PASS')\n"
      ],
      [
        "priority_ordering",
        "\nimport subprocess, json, tempfile, os\nd = tempfile.mkdtemp()\ninp = os.path.join(d, 'tasks.json')\njson.dump([\n    {'id': 'x', 'priority': 3, 'depends_on': []},\n    {'id': 'y', 'priority': 1, 'depends_on': []},\n    {'id': 'z', 'priority': 2, 'depends_on': []},\n], open(inp, 'w'))\nout = os.path.join(d, 'out.json')\nr = subprocess.run([sys.executable, 'run_scheduler.py', '--input', inp, '--output', out],\n    capture_output=True, text=True, timeout=10, cwd=d)\nassert r.returncode == 0, f'exit {r.returncode}: {r.stderr}'\norder = json.load(open(out))\nassert order == ['y', 'z', 'x'], f'priority order should be y(1),z(2),x(3), got {order}'\nprint('PASS')\n"
      ],
      [
        "circular_dep",
        "\nimport subprocess, json, tempfile, os\nd = tempfile.mkdtemp()\ninp = os.path.join(d, 'tasks.json')\njson.dump([\n    {'id': 'a', 'priority': 1, 'depends_on': ['b']},\n    {'id': 'b', 'priority': 1, 'depends_on': ['a']},\n], open(inp, 'w'))\nout = os.path.join(d, 'out.json')\nr = subprocess.run([sys.executable, 'run_scheduler.py', '--input', inp, '--output', out],\n    capture_output=True, text=True, timeout=10, cwd=d)\nassert r.returncode == 1, f'expected exit 1 for circular dep, got {r.returncode}'\nassert 'Circular' in r.stdout or 'Circular' in r.stderr, f'expected Circular message, got stdout={r.stdout!r}'\nprint('PASS')\n"
      ]
    ],
    "type": "assembly"
  },
  {
    "id": "converter",
    "wiring_file": "run_converter.py",
    "task_desc": "Write a CLI tool that converts a CSV file to JSONL (JSON Lines) format. For each row, infer the type of each value: if it's all digits, convert to int; if it looks like a float, convert to float; otherwise keep as string. Accept args: --input <csv_path>, --output <jsonl_path>. Print 'Converted N rows' to stdout. Empty CSV (header only) → write empty output. Missing input → exit 1.",
    "siblings": [
      {
        "filename": "csv_util.py",
        "source": "import csv\n\ndef read_csv(path):\n    with open(path, newline='', encoding='utf-8') as f:\n        reader = csv.DictReader(f)\n        return list(reader)\n",
        "interfaces": "csv_util.py: read_csv(path: str) -> list[dict]"
      },
      {
        "filename": "type_infer.py",
        "source": "def infer_type(value):\n    if value is None or value == '':\n        return ''\n    try:\n        return int(value)\n    except ValueError:\n        pass\n    try:\n        return float(value)\n    except ValueError:\n        pass\n    return value\n\ndef convert_row(row):\n    return {k: infer_type(v) for k, v in row.items()}\n",
        "interfaces": "type_infer.py: infer_type(value: str) -> int|float|str, convert_row(row: dict) -> dict"
      }
    ],
    "tests": [
      [
        "correct_types",
        "\nimport subprocess, json, tempfile, os\nd = tempfile.mkdtemp()\ninp = os.path.join(d, 'data.csv')\nopen(inp, 'w').write('name,age,score\\nAlice,30,95.5\\nBob,25,88.0\\n')\nout = os.path.join(d, 'out.jsonl')\nr = subprocess.run([sys.executable, 'run_converter.py', '--input', inp, '--output', out],\n    capture_output=True, text=True, timeout=10, cwd=d)\nassert r.returncode == 0, f'exit {r.returncode}: {r.stderr}'\nlines = open(out).read().strip().split('\\n')\nassert len(lines) == 2, f'expected 2 rows, got {len(lines)}'\nrow1 = json.loads(lines[0])\nassert row1['name'] == 'Alice', f'name should be string, got {row1}'\nassert row1['age'] == 30, f'age should be int 30, got {row1[\"age\"]} (type {type(row1[\"age\"]).__name__})'\nassert row1['score'] == 95.5, f'score should be float 95.5, got {row1[\"score\"]}'\nprint('PASS')\n"
      ],
      [
        "header_only",
        "\nimport subprocess, tempfile, os\nd = tempfile.mkdtemp()\ninp = os.path.join(d, 'data.csv')\nopen(inp, 'w').write('name,age\\n')\nout = os.path.join(d, 'out.jsonl')\nr = subprocess.run([sys.executable, 'run_converter.py', '--input', inp, '--output', out],\n    capture_output=True, text=True, timeout=10, cwd=d)\nassert r.returncode == 0, f'exit {r.returncode}: {r.stderr}'\ncontent = open(out).read().strip()\nassert content == '', f'expected empty output for header-only CSV, got {content!r}'\nprint('PASS')\n"
      ],
      [
        "missing_input",
        "\nimport subprocess, tempfile, os\nd = tempfile.mkdtemp()\nout = os.path.join(d, 'out.jsonl')\nr = subprocess.run([sys.executable, 'run_converter.py', '--input', 'nope.csv', '--output', out],\n    capture_output=True, text=True, timeout=10, cwd=d)\nassert r.returncode == 1, f'expected exit 1, got {r.returncode}'\nassert 'Traceback' not in r.stderr, f'crashed: {r.stderr[:200]}'\nprint('PASS')\n"
      ]
    ],
    "type": "assembly"
  },
  {
    "id": "indexer",
    "wiring_file": "run_indexer.py",
    "task_desc": "Write a CLI tool that builds an inverted index from a JSON file of documents. Each document has: id (str), text (str). The inverted index maps each word to a list of document ids that contain it (sorted, no duplicates). Accept args: --input <json_path>, --output <json_path>. Output a JSON object: {word: [doc_ids]}. Print 'Indexed N documents' to stdout. Missing input → exit 1.",
    "siblings": [
      {
        "filename": "doc_loader.py",
        "source": "import json\n\ndef load_docs(path):\n    with open(path, encoding='utf-8') as f:\n        return json.load(f)\n\ndef save_index(index, path):\n    with open(path, 'w', encoding='utf-8') as f:\n    json.dump(index, f, indent=2)\n",
        "interfaces": "doc_loader.py: load_docs(path: str) -> list[dict], save_index(index: dict, path: str) -> None"
      },
      {
        "filename": "index_util.py",
        "source": "import re\nfrom collections import defaultdict\n\ndef tokenize(text):\n    return [w.lower() for w in re.findall(r'[a-zA-Z]+', text)]\n\ndef build_index(docs):\n    index = defaultdict(set)\n    for doc in docs:\n        doc_id = doc['id']\n        for word in tokenize(doc.get('text', '')):\n            index[word].add(doc_id)\n    return {k: sorted(v) for k, v in index.items()}\n",
        "interfaces": "index_util.py: tokenize(text: str) -> list[str], build_index(docs: list[dict]) -> dict[str, list[str]]"
      }
    ],
    "tests": [
      [
        "correct_index",
        "\nimport subprocess, json, tempfile, os\nd = tempfile.mkdtemp()\ninp = os.path.join(d, 'docs.json')\njson.dump([\n    {'id': 'doc1', 'text': 'the quick brown fox'},\n    {'id': 'doc2', 'text': 'the lazy dog'},\n    {'id': 'doc3', 'text': 'quick brown dog'},\n], open(inp, 'w'))\nout = os.path.join(d, 'out.json')\nr = subprocess.run([sys.executable, 'run_indexer.py', '--input', inp, '--output', out],\n    capture_output=True, text=True, timeout=10, cwd=d)\nassert r.returncode == 0, f'exit {r.returncode}: {r.stderr}'\nindex = json.load(open(out))\nassert index.get('quick') == ['doc1', 'doc3'], f'quick should be in doc1,doc3, got {index.get(\"quick\")}'\nassert index.get('the') == ['doc1', 'doc2'], f'the should be in doc1,doc2, got {index.get(\"the\")}'\nassert index.get('fox') == ['doc1'], f'fox should be in doc1 only, got {index.get(\"fox\")}'\nprint('PASS')\n"
      ],
      [
        "no_duplicates",
        "\nimport subprocess, json, tempfile, os\nd = tempfile.mkdtemp()\ninp = os.path.join(d, 'docs.json')\njson.dump([\n    {'id': 'doc1', 'text': 'apple apple apple'},\n], open(inp, 'w'))\nout = os.path.join(d, 'out.json')\nr = subprocess.run([sys.executable, 'run_indexer.py', '--input', inp, '--output', out],\n    capture_output=True, text=True, timeout=10, cwd=d)\nassert r.returncode == 0, f'exit {r.returncode}: {r.stderr}'\nindex = json.load(open(out))\nassert index.get('apple') == ['doc1'], f'apple should appear once in list, got {index.get(\"apple\")}'\nprint('PASS')\n"
      ],
      [
        "missing_input",
        "\nimport subprocess, tempfile, os\nd = tempfile.mkdtemp()\nout = os.path.join(d, 'out.json')\nr = subprocess.run([sys.executable, 'run_indexer.py', '--input', 'nope.json', '--output', out],\n    capture_output=True, text=True, timeout=10, cwd=d)\nassert r.returncode == 1, f'expected exit 1, got {r.returncode}'\nassert 'Traceback' not in r.stderr, f'crashed: {r.stderr[:200]}'\nprint('PASS')\n"
      ]
    ],
    "type": "assembly"
  },
  {
    "id": "fix_offbyone",
    "task_type": "swe_lite",
    "wiring_file": "fix_bug.py",
    "task_desc": "The file pagination.py has a bug. Its paginate() function returns one extra item on each page (off-by-one in the end index). Write the CORRECTED version of pagination.py. The fix: the end index for slicing should be start + page_size, not start + page_size + 1. Write the complete fixed file.",
    "siblings": [
      {
        "filename": "pagination.py",
        "source": "def paginate(items, page_size):\n    pages = []\n    for i in range(0, len(items), page_size):\n        page = items[i:i + page_size + 1]  # BUG: +1 causes off-by-one\n        pages.append(page)\n    return pages\n",
        "interfaces": "pagination.py: paginate(items: list, page_size: int) -> list[list]  (BUG: returns one extra item per page)"
      }
    ],
    "tests": [
      [
        "correct_pagination",
        "\nimport subprocess, tempfile, os, sys\nd = tempfile.mkdtemp()\nr = subprocess.run([sys.executable, '-c', '''\nimport sys\nsys.path.insert(0, \".\")\nfrom fix_bug import paginate\nresult = paginate([1,2,3,4,5,6,7], 3)\nassert result == [[1,2,3],[4,5,6],[7]], f\"got {result}\"\nprint(\"PASS\")\n'''], capture_output=True, text=True, timeout=10, cwd=d)\nassert r.returncode == 0, f'failed: {r.stderr}'\nassert 'PASS' in r.stdout, f'assertion failed: {r.stdout} {r.stderr}'\n"
      ],
      [
        "empty_list",
        "\nimport subprocess, sys, tempfile, os\nd = tempfile.mkdtemp()\nr = subprocess.run([sys.executable, '-c', '''\nimport sys\nsys.path.insert(0, \".\")\nfrom fix_bug import paginate\nresult = paginate([], 3)\nassert result == [], f\"got {result}\"\nprint(\"PASS\")\n'''], capture_output=True, text=True, timeout=10, cwd=d)\nassert r.returncode == 0, f'failed: {r.stderr}'\nassert 'PASS' in r.stdout, f'failed: {r.stdout} {r.stderr}'\n"
      ],
      [
        "single_page",
        "\nimport subprocess, sys, tempfile, os\nd = tempfile.mkdtemp()\nr = subprocess.run([sys.executable, '-c', '''\nimport sys\nsys.path.insert(0, \".\")\nfrom fix_bug import paginate\nresult = paginate([1,2], 5)\nassert result == [[1,2]], f\"got {result}\"\nprint(\"PASS\")\n'''], capture_output=True, text=True, timeout=10, cwd=d)\nassert r.returncode == 0, f'failed: {r.stderr}'\nassert 'PASS' in r.stdout, f'failed: {r.stdout} {r.stderr}'\n"
      ]
    ],
    "type": "assembly"
  },
  {
    "id": "add_errorhandling",
    "task_type": "swe_lite",
    "wiring_file": "add_feature.py",
    "task_desc": "The file calculator.py works but crashes on invalid input (division by zero, non-numeric values). Add error handling: on division by zero, return the string 'Error: Division by zero'. On non-numeric input, return 'Error: Invalid input'. Do NOT change the existing function signatures. Write the complete file with the fix.",
    "siblings": [
      {
        "filename": "calculator.py",
        "source": "def add(a, b):\n    return a + b\n\ndef subtract(a, b):\n    return a - b\n\ndef multiply(a, b):\n    return a * b\n\ndef divide(a, b):\n    return a / b  # BUG: crashes on b=0\n\ndef parse_and_calc(op, a_str, b_str):\n    a = float(a_str)\n    b = float(b_str)\n    if op == 'add': return add(a, b)\n    if op == 'subtract': return subtract(a, b)\n    if op == 'multiply': return multiply(a, b)\n    if op == 'divide': return divide(a, b)\n    return 'Unknown operation'\n",
        "interfaces": "calculator.py: add(a,b), subtract(a,b), multiply(a,b), divide(a,b), parse_and_calc(op, a_str, b_str)  (crashes on invalid input)"
      }
    ],
    "tests": [
      [
        "division_by_zero",
        "\nimport subprocess, sys, tempfile, os\nd = tempfile.mkdtemp()\nr = subprocess.run([sys.executable, '-c', '''\nimport sys\nsys.path.insert(0, \".\")\nfrom add_feature import divide\nresult = divide(10, 0)\nassert result == \"Error: Division by zero\", f\"got {result!r}\"\nprint(\"PASS\")\n'''], capture_output=True, text=True, timeout=10, cwd=d)\nassert r.returncode == 0, f'failed: {r.stderr}'\nassert 'PASS' in r.stdout, f'failed: {r.stdout} {r.stderr}'\n"
      ],
      [
        "invalid_input",
        "\nimport subprocess, sys, tempfile, os\nd = tempfile.mkdtemp()\nr = subprocess.run([sys.executable, '-c', '''\nimport sys\nsys.path.insert(0, \".\")\nfrom add_feature import parse_and_calc\nresult = parse_and_calc(\"add\", \"abc\", \"5\")\nassert \"Error\" in str(result), f\"expected error, got {result!r}\"\nprint(\"PASS\")\n'''], capture_output=True, text=True, timeout=10, cwd=d)\nassert r.returncode == 0, f'failed: {r.stderr}'\nassert 'PASS' in r.stdout, f'failed: {r.stdout} {r.stderr}'\n"
      ],
      [
        "still_works_normally",
        "\nimport subprocess, sys, tempfile, os\nd = tempfile.mkdtemp()\nr = subprocess.run([sys.executable, '-c', '''\nimport sys\nsys.path.insert(0, \".\")\nfrom add_feature import add, subtract, multiply, divide, parse_and_calc\nassert add(2, 3) == 5\nassert subtract(5, 2) == 3\nassert multiply(3, 4) == 12\nassert divide(10, 2) == 5.0\nassert parse_and_calc(\"add\", \"1\", \"2\") == 3.0\nprint(\"PASS\")\n'''], capture_output=True, text=True, timeout=10, cwd=d)\nassert r.returncode == 0, f'failed: {r.stderr}'\nassert 'PASS' in r.stdout, f'failed: {r.stdout} {r.stderr}'\n"
      ]
    ],
    "type": "assembly"
  },
  {
    "id": "refactor_rename",
    "task_type": "swe_lite",
    "wiring_file": "refactor_names.py",
    "task_desc": "The file data_proc.py uses cryptic variable names (x, y, z, a, b). Refactor it to use descriptive names: x→items, y→threshold, z→result, a→current, b→is_valid. Do NOT change the logic or function behavior. Write the complete refactored file.",
    "siblings": [
      {
        "filename": "data_proc.py",
        "source": "def process(x, y):\n    z = []\n    for a in x:\n        b = a > y\n        if b:\n            z.append(a)\n    return z\n\ndef count_above(x, y):\n    z = 0\n    for a in x:\n        b = a > y\n        if b:\n            z = z + 1\n    return z\n",
        "interfaces": "data_proc.py: process(x: list, y: number) -> list, count_above(x: list, y: number) -> int  (uses cryptic names, works correctly)"
      }
    ],
    "tests": [
      [
        "process_works",
        "\nimport subprocess, sys, tempfile, os\nd = tempfile.mkdtemp()\nr = subprocess.run([sys.executable, '-c', '''\nimport sys\nsys.path.insert(0, \".\")\nfrom refactor_names import process\nresult = process([1, 5, 3, 8, 2], 4)\nassert result == [5, 8], f\"got {result}\"\nprint(\"PASS\")\n'''], capture_output=True, text=True, timeout=10, cwd=d)\nassert r.returncode == 0, f'failed: {r.stderr}'\nassert 'PASS' in r.stdout, f'failed: {r.stdout} {r.stderr}'\n"
      ],
      [
        "count_works",
        "\nimport subprocess, sys, tempfile, os\nd = tempfile.mkdtemp()\nr = subprocess.run([sys.executable, '-c', '''\nimport sys\nsys.path.insert(0, \".\")\nfrom refactor_names import count_above\nresult = count_above([1, 5, 3, 8, 2], 4)\nassert result == 2, f\"got {result}\"\nprint(\"PASS\")\n'''], capture_output=True, text=True, timeout=10, cwd=d)\nassert r.returncode == 0, f'failed: {r.stderr}'\nassert 'PASS' in r.stdout, f'failed: {r.stdout} {r.stderr}'\n"
      ],
      [
        "uses_descriptive_names",
        "\nimport subprocess, sys, tempfile, os\nd = tempfile.mkdtemp()\nr = subprocess.run([sys.executable, '-c', '''\nimport sys, inspect\nsys.path.insert(0, \".\")\nimport refactor_names\nsrc = inspect.getsource(refactor_names)\nassert \"items\" in src or \"threshold\" in src, f\"no descriptive names found in source\"\nassert \"def process\" in src, f\"process function missing\"\nprint(\"PASS\")\n'''], capture_output=True, text=True, timeout=10, cwd=d)\nassert r.returncode == 0, f'failed: {r.stderr}'\nassert 'PASS' in r.stdout, f'failed: {r.stdout} {r.stderr}'\n"
      ]
    ],
    "type": "assembly"
  },
  {
    "id": "api_client",
    "task_type": "wiring",
    "wiring_file": "wire_api.py",
    "task_desc": "Write a CLI tool that simulates an API client. It makes requests using the http_sim module, retries failed requests up to 3 times with the retry module, and logs results. Accept args: --url <url>, --method <GET|POST>, --output <path>. Make the request, retry on failure, write the response to the output file. Print 'Success' or 'Failed after 3 retries' to stdout. Exit 0 on success, 1 on failure.",
    "siblings": [
      {
        "filename": "http_sim.py",
        "source": "import random\n\n_fail_rate = 0.3\n\ndef request(url, method='GET'):\n    if random.random() < _fail_rate:\n        return {'status': 500, 'body': 'Internal Error'}\n    return {'status': 200, 'body': f'Response from {url} via {method}'}\n",
        "interfaces": "http_sim.py: request(url: str, method: str) -> dict  (returns {'status': int, 'body': str}, may fail with 500)"
      },
      {
        "filename": "retry.py",
        "source": "import time\n\ndef with_retry(func, max_retries=3, delay=0):\n    last_error = None\n    for attempt in range(max_retries):\n        try:\n            result = func()\n            if isinstance(result, dict) and result.get('status', 200) < 400:\n                return result\n            last_error = result\n        except Exception as e:\n            last_error = str(e)\n        if attempt < max_retries - 1 and delay > 0:\n            time.sleep(delay)\n    return last_error\n",
        "interfaces": "retry.py: with_retry(func: callable, max_retries: int, delay: float) -> dict  (retries on failure, returns last result)"
      },
      {
        "filename": "logger.py",
        "source": "def log_result(url, method, success, attempts, output_path):\n    with open(output_path, 'w') as f:\n        f.write(f'URL: {url}\\n')\n        f.write(f'Method: {method}\\n')\n        f.write(f'Success: {success}\\n')\n        f.write(f'Attempts: {attempts}\\n')\n",
        "interfaces": "logger.py: log_result(url: str, method: str, success: bool, attempts: int, output_path: str) -> None"
      }
    ],
    "tests": [
      [
        "success_writes_output",
        "\nimport subprocess, tempfile, os\nd = tempfile.mkdtemp()\nout = os.path.join(d, 'response.txt')\nr = subprocess.run([sys.executable, 'wire_api.py', '--url', 'http://example.com', '--method', 'GET', '--output', out],\n    capture_output=True, text=True, timeout=15, cwd=d)\nassert r.returncode == 0, f'exit {r.returncode}: {r.stderr}'\nassert os.path.exists(out), 'output file not created'\ncontent = open(out).read()\nassert 'example.com' in content or 'Response' in content, f'expected response content, got {content!r}'\nprint('PASS')\n"
      ],
      [
        "missing_args",
        "\nimport subprocess, tempfile, os\nd = tempfile.mkdtemp()\nr = subprocess.run([sys.executable, 'wire_api.py'],\n    capture_output=True, text=True, timeout=10, cwd=d)\nassert r.returncode != 0, f'expected nonzero exit for missing args, got {r.returncode}'\nprint('PASS')\n"
      ],
      [
        "prints_status",
        "\nimport subprocess, tempfile, os\nd = tempfile.mkdtemp()\nout = os.path.join(d, 'response.txt')\nr = subprocess.run([sys.executable, 'wire_api.py', '--url', 'http://test.com', '--method', 'GET', '--output', out],\n    capture_output=True, text=True, timeout=15, cwd=d)\nassert 'Success' in r.stdout or 'Failed' in r.stdout, f'expected status message, got stdout={r.stdout!r}'\nprint('PASS')\n"
      ]
    ],
    "type": "assembly"
  },
  {
    "id": "rle_decode",
    "filename": "rle_decode.py",
    "func_name": "rle_decode",
    "desc": "Build a Python module with a function rle_decode(s) that decodes a run-length encoded string. Letters are followed by an optional count (positive integer). rle_decode('a3b2') returns 'aaabb'. rle_decode('abc') returns 'abc'. rle_decode('') returns ''. Counts are only the digits immediately after a letter; a letter with no count means one occurrence.",
    "tests": [
      [
        "rle_decode('a3b2')",
        "'aaabb'"
      ],
      [
        "rle_decode('abc')",
        "'abc'"
      ],
      [
        "rle_decode('')",
        "''"
      ],
      [
        "rle_decode('a10')",
        "'aaaaaaaaaa'"
      ],
      [
        "rle_decode('x1y2z')",
        "'xyyz'"
      ]
    ],
    "type": "function"
  },
  {
    "id": "missing_ranges",
    "filename": "missing_ranges.py",
    "func_name": "find_missing_ranges",
    "desc": "Build a Python module with a function find_missing_ranges(nums, lower, upper) that returns a list of strings representing the ranges of numbers missing from the sorted unique list nums within [lower, upper] inclusive. A single missing number is reported as 'x', a range as 'x->y'. nums is sorted ascending and contains unique values inside the bounds.",
    "tests": [
      [
        "find_missing_ranges([0,1,3,50,75], 0, 99)",
        "['2','4->49','51->74','76->99']"
      ],
      [
        "find_missing_ranges([], 1, 1)",
        "['1']"
      ],
      [
        "find_missing_ranges([], 1, 3)",
        "['1->3']"
      ],
      [
        "find_missing_ranges([1,2,3], 1, 3)",
        "[]"
      ],
      [
        "find_missing_ranges([2], 1, 3)",
        "['1','3']"
      ]
    ],
    "type": "function"
  },
  {
    "id": "merge_intervals",
    "filename": "merge_intervals.py",
    "func_name": "merge",
    "desc": "Build a Python module with a function merge(intervals) that takes a list of [start, end] intervals and returns a new list of merged intervals covering the same ranges with no overlaps. Intervals may be unsorted. Empty list returns empty list. Touching intervals (e.g. [1,2] and [2,3]) should be merged.",
    "tests": [
      [
        "merge([[1,3],[2,6],[8,10],[15,18]])",
        "[[1,6],[8,10],[15,18]]"
      ],
      [
        "merge([[1,4],[4,5]])",
        "[[1,5]]"
      ],
      [
        "merge([])",
        "[]"
      ],
      [
        "merge([[1,4],[0,4]])",
        "[[0,4]]"
      ],
      [
        "merge([[1,4],[2,3]])",
        "[[1,4]]"
      ]
    ],
    "type": "function"
  },
  {
    "id": "normalize_path",
    "filename": "normalize_path.py",
    "func_name": "normalize",
    "desc": "Build a Python module with a function normalize(path) that simplifies a Unix-style absolute path. '.' is ignored, '..' goes up one level (but never above root), multiple slashes collapse, and the result always starts with '/'. normalize('/a/./b/../../c/') returns '/c'. normalize('/../') returns '/'.",
    "tests": [
      [
        "normalize('/a/./b/../../c/')",
        "'/c'"
      ],
      [
        "normalize('/../')",
        "'/'"
      ],
      [
        "normalize('/home//foo/')",
        "'/home/foo'"
      ],
      [
        "normalize('/a/b/c/./../../d/')",
        "'/a/d'"
      ],
      [
        "normalize('/')",
        "'/'"
      ]
    ],
    "type": "function"
  },
  {
    "id": "base_convert",
    "filename": "base_convert.py",
    "func_name": "to_base",
    "desc": "Build a Python module with a function to_base(n, b) that converts the integer n to a string in base b, where b is between 2 and 36 inclusive. Digits above 9 use lowercase letters, so 10 is 'a' and 35 is 'z'. to_base(0, 2) returns '0'. Negative numbers get a leading '-', so to_base(-5, 2) returns '-101'. There are no leading zeros otherwise.",
    "tests": [
      [
        "to_base(0, 2)",
        "'0'"
      ],
      [
        "to_base(-5, 2)",
        "'-101'"
      ],
      [
        "to_base(255, 16)",
        "'ff'"
      ],
      [
        "to_base(35, 36)",
        "'z'"
      ],
      [
        "to_base(1000, 7)",
        "'2626'"
      ]
    ],
    "reference": "\ndef to_base(n, b):\n    if n == 0:\n        return \"0\"\n    digits = \"0123456789abcdefghijklmnopqrstuvwxyz\"\n    neg = n < 0\n    n = abs(n)\n    out = []\n    while n:\n        out.append(digits[n % b])\n        n //= b\n    if neg:\n        out.append(\"-\")\n    return \"\".join(reversed(out))\n",
    "type": "function"
  },
  {
    "id": "spiral_order",
    "filename": "spiral_order.py",
    "func_name": "spiral_order",
    "desc": "Build a Python module with a function spiral_order(matrix) that returns all elements of a rectangular matrix (a list of equal-length lists) in clockwise spiral order, starting at the top-left and moving right first. spiral_order([]) returns []. The matrix may be any width and height, including a single row or a single column.",
    "tests": [
      [
        "spiral_order([[1,2,3],[4,5,6],[7,8,9]])",
        "[1,2,3,6,9,8,7,4,5]"
      ],
      [
        "spiral_order([])",
        "[]"
      ],
      [
        "spiral_order([[1,2,3,4]])",
        "[1,2,3,4]"
      ],
      [
        "spiral_order([[1],[2],[3]])",
        "[1,2,3]"
      ],
      [
        "spiral_order([[1,2],[3,4],[5,6]])",
        "[1,2,4,6,5,3]"
      ]
    ],
    "reference": "\ndef spiral_order(matrix):\n    if not matrix or not matrix[0]:\n        return []\n    out = []\n    top, bottom = 0, len(matrix) - 1\n    left, right = 0, len(matrix[0]) - 1\n    while top <= bottom and left <= right:\n        for c in range(left, right + 1):\n            out.append(matrix[top][c])\n        top += 1\n        for r in range(top, bottom + 1):\n            out.append(matrix[r][right])\n        right -= 1\n        if top <= bottom:\n            for c in range(right, left - 1, -1):\n                out.append(matrix[bottom][c])\n            bottom -= 1\n        if left <= right:\n            for r in range(bottom, top - 1, -1):\n                out.append(matrix[r][left])\n            left += 1\n    return out\n",
    "type": "function"
  },
  {
    "id": "word_wrap",
    "filename": "word_wrap.py",
    "func_name": "wrap",
    "desc": "Build a Python module with a function wrap(text, width) that greedily wraps text to lines of at most `width` characters and returns a list of lines. Split the text on whitespace into words; put as many words on a line as fit, joined by single spaces. A word longer than width goes on a line by itself and is not broken. wrap('', 5) returns []. Lines have no leading or trailing spaces.",
    "tests": [
      [
        "wrap('the quick brown fox', 10)",
        "['the quick', 'brown fox']"
      ],
      [
        "wrap('', 5)",
        "[]"
      ],
      [
        "wrap('extraordinarily long', 5)",
        "['extraordinarily', 'long']"
      ],
      [
        "wrap('a b c', 1)",
        "['a', 'b', 'c']"
      ],
      [
        "wrap('aa bb cc dd', 5)",
        "['aa bb', 'cc dd']"
      ]
    ],
    "reference": "\ndef wrap(text, width):\n    words = text.split()\n    if not words:\n        return []\n    lines = []\n    cur = words[0]\n    for w in words[1:]:\n        if len(cur) + 1 + len(w) <= width:\n            cur += \" \" + w\n        else:\n            lines.append(cur)\n            cur = w\n    lines.append(cur)\n    return lines\n",
    "type": "function"
  },
  {
    "id": "roman_to_int",
    "filename": "roman_to_int.py",
    "func_name": "roman_to_int",
    "desc": "Build a Python module with a function roman_to_int(s) that converts a valid uppercase Roman numeral string to an integer. The symbols are I=1, V=5, X=10, L=50, C=100, D=500, M=1000. A symbol placed before a larger one is subtracted, so 'IV' is 4 and 'CM' is 900. roman_to_int('') returns 0.",
    "tests": [
      [
        "roman_to_int('IV')",
        "4"
      ],
      [
        "roman_to_int('')",
        "0"
      ],
      [
        "roman_to_int('MCMXCIV')",
        "1994"
      ],
      [
        "roman_to_int('III')",
        "3"
      ],
      [
        "roman_to_int('LVIII')",
        "58"
      ]
    ],
    "reference": "\ndef roman_to_int(s):\n    vals = {\"I\": 1, \"V\": 5, \"X\": 10, \"L\": 50, \"C\": 100, \"D\": 500, \"M\": 1000}\n    total = 0\n    for i, ch in enumerate(s):\n        v = vals[ch]\n        if i + 1 < len(s) and vals[s[i + 1]] > v:\n            total -= v\n        else:\n            total += v\n    return total\n",
    "type": "function"
  },
  {
    "id": "int_to_roman",
    "filename": "int_to_roman.py",
    "func_name": "int_to_roman",
    "desc": "Build a Python module with a function int_to_roman(n) that converts an integer between 1 and 3999 inclusive to its uppercase Roman numeral string, using the standard subtractive forms IV, IX, XL, XC, CD and CM. int_to_roman(4) returns 'IV'.",
    "tests": [
      [
        "int_to_roman(4)",
        "'IV'"
      ],
      [
        "int_to_roman(1994)",
        "'MCMXCIV'"
      ],
      [
        "int_to_roman(3999)",
        "'MMMCMXCIX'"
      ],
      [
        "int_to_roman(1)",
        "'I'"
      ],
      [
        "int_to_roman(40)",
        "'XL'"
      ]
    ],
    "reference": "\ndef int_to_roman(n):\n    table = [(1000, \"M\"), (900, \"CM\"), (500, \"D\"), (400, \"CD\"),\n             (100, \"C\"), (90, \"XC\"), (50, \"L\"), (40, \"XL\"),\n             (10, \"X\"), (9, \"IX\"), (5, \"V\"), (4, \"IV\"), (1, \"I\")]\n    out = []\n    for v, sym in table:\n        while n >= v:\n            out.append(sym)\n            n -= v\n    return \"\".join(out)\n",
    "type": "function"
  },
  {
    "id": "balanced_brackets",
    "filename": "balanced_brackets.py",
    "func_name": "is_balanced",
    "desc": "Build a Python module with a function is_balanced(s) that returns True if every bracket in the string is closed by the matching kind in the correct order, and False otherwise. The bracket kinds are (), [] and {}. Any other character is ignored. is_balanced('') returns True. An unclosed opener returns False.",
    "tests": [
      [
        "is_balanced('a(b[c]{d})e')",
        "True"
      ],
      [
        "is_balanced('')",
        "True"
      ],
      [
        "is_balanced('([)]')",
        "False"
      ],
      [
        "is_balanced('(')",
        "False"
      ],
      [
        "is_balanced(')(')",
        "False"
      ]
    ],
    "reference": "\ndef is_balanced(s):\n    pairs = {\")\": \"(\", \"]\": \"[\", \"}\": \"{\"}\n    stack = []\n    for ch in s:\n        if ch in \"([{\":\n            stack.append(ch)\n        elif ch in pairs:\n            if not stack or stack.pop() != pairs[ch]:\n                return False\n    return not stack\n",
    "type": "function"
  },
  {
    "id": "longest_common_prefix",
    "filename": "longest_common_prefix.py",
    "func_name": "common_prefix",
    "desc": "Build a Python module with a function common_prefix(strs) that returns the longest string that is a prefix of every string in the list strs. Return '' if there is no common prefix, if the list is empty, or if any string is empty. Comparison is case-sensitive.",
    "tests": [
      [
        "common_prefix(['flower','flow','flight'])",
        "'fl'"
      ],
      [
        "common_prefix([])",
        "''"
      ],
      [
        "common_prefix(['dog','racecar'])",
        "''"
      ],
      [
        "common_prefix(['same','same'])",
        "'same'"
      ],
      [
        "common_prefix(['abc',''])",
        "''"
      ]
    ],
    "reference": "\ndef common_prefix(strs):\n    if not strs:\n        return \"\"\n    out = []\n    for chars in zip(*strs):\n        if len(set(chars)) == 1:\n            out.append(chars[0])\n        else:\n            break\n    return \"\".join(out)\n",
    "type": "function"
  },
  {
    "id": "compress_ranges",
    "filename": "compress_ranges.py",
    "func_name": "compress",
    "desc": "Build a Python module with a function compress(nums) that takes a sorted list of unique integers and returns a list of strings describing consecutive runs. A run of one number is reported as 'x'; a run of two or more as 'x->y' using its first and last values. compress([]) returns []. Negative numbers are allowed.",
    "tests": [
      [
        "compress([0,1,2,4,5,7])",
        "['0->2','4->5','7']"
      ],
      [
        "compress([])",
        "[]"
      ],
      [
        "compress([5])",
        "['5']"
      ],
      [
        "compress([-3,-2,-1,1])",
        "['-3->-1','1']"
      ],
      [
        "compress([1,3,5])",
        "['1','3','5']"
      ]
    ],
    "reference": "\ndef compress(nums):\n    if not nums:\n        return []\n    out = []\n    start = prev = nums[0]\n    for n in nums[1:]:\n        if n == prev + 1:\n            prev = n\n            continue\n        out.append(str(start) if start == prev else str(start) + \"->\" + str(prev))\n        start = prev = n\n    out.append(str(start) if start == prev else str(start) + \"->\" + str(prev))\n    return out\n",
    "type": "function"
  },
  {
    "id": "camel_to_snake",
    "filename": "camel_to_snake.py",
    "func_name": "to_snake",
    "desc": "Build a Python module with a function to_snake(name) that converts a CamelCase or camelCase identifier to snake_case. Insert an underscore before each uppercase letter that follows a lowercase letter or a digit, and before the last uppercase letter of a run of uppercase letters that is followed by a lowercase letter. Then lowercase everything. to_snake('HTTPServer') returns 'http_server'. to_snake('') returns ''.",
    "tests": [
      [
        "to_snake('CamelCase')",
        "'camel_case'"
      ],
      [
        "to_snake('HTTPServer')",
        "'http_server'"
      ],
      [
        "to_snake('')",
        "''"
      ],
      [
        "to_snake('parseHTTP2Response')",
        "'parse_http2_response'"
      ],
      [
        "to_snake('already_snake')",
        "'already_snake'"
      ]
    ],
    "reference": "\nimport re\n\n\ndef to_snake(name):\n    s = re.sub(r\"([A-Z]+)([A-Z][a-z])\", r\"\\1_\\2\", name)\n    s = re.sub(r\"([a-z0-9])([A-Z])\", r\"\\1_\\2\", s)\n    return s.lower()\n",
    "type": "function"
  },
  {
    "id": "flatten_dict",
    "filename": "flatten_dict.py",
    "func_name": "flatten",
    "desc": "Build a Python module with a function flatten(d) that flattens a nested dictionary into a single-level dictionary whose keys are the paths joined by '.'. Only dict values are recursed into; lists and every other value are left as they are. An empty dict as a value disappears entirely, contributing no key. flatten({}) returns {}.",
    "tests": [
      [
        "flatten({'a': {'b': 1}, 'c': 2})",
        "{'a.b': 1, 'c': 2}"
      ],
      [
        "flatten({})",
        "{}"
      ],
      [
        "flatten({'a': {'b': {'c': 3}}})",
        "{'a.b.c': 3}"
      ],
      [
        "flatten({'a': {}, 'b': 1})",
        "{'b': 1}"
      ],
      [
        "flatten({'a': [1, {'b': 2}]})",
        "{'a': [1, {'b': 2}]}"
      ]
    ],
    "reference": "\ndef flatten(d, prefix=\"\"):\n    out = {}\n    for k, v in d.items():\n        key = prefix + str(k)\n        if isinstance(v, dict):\n            out.update(flatten(v, key + \".\"))\n        else:\n            out[key] = v\n    return out\n",
    "type": "function"
  },
  {
    "id": "parse_query",
    "filename": "parse_query.py",
    "func_name": "parse_query",
    "desc": "Build a Python module with a function parse_query(qs) that parses a URL query string into a dict. Pairs are separated by '&' and key from value by the first '=' only, so 'a=b=c' gives the value 'b=c'. A key with no '=' maps to ''. A repeated key keeps the LAST value. Empty segments are skipped, so 'a=1&&b=2' has two keys. No percent-decoding is performed. parse_query('') returns {}.",
    "tests": [
      [
        "parse_query('a=1&b=2')",
        "{'a': '1', 'b': '2'}"
      ],
      [
        "parse_query('')",
        "{}"
      ],
      [
        "parse_query('a=b=c')",
        "{'a': 'b=c'}"
      ],
      [
        "parse_query('flag&x=1')",
        "{'flag': '', 'x': '1'}"
      ],
      [
        "parse_query('k=1&&k=2')",
        "{'k': '2'}"
      ]
    ],
    "reference": "\ndef parse_query(qs):\n    out = {}\n    for part in qs.split(\"&\"):\n        if not part:\n            continue\n        k, sep, v = part.partition(\"=\")\n        out[k] = v if sep else \"\"\n    return out\n",
    "type": "function"
  },
  {
    "id": "next_permutation",
    "filename": "next_permutation.py",
    "func_name": "next_permutation",
    "desc": "Build a Python module with a function next_permutation(nums) that returns a NEW list holding the next lexicographically greater permutation of the list nums. If no greater permutation exists, return the list sorted ascending (the lowest permutation). The input list must not be modified. next_permutation([]) returns [].",
    "tests": [
      [
        "next_permutation([1,2,3])",
        "[1,3,2]"
      ],
      [
        "next_permutation([3,2,1])",
        "[1,2,3]"
      ],
      [
        "next_permutation([1,1,5])",
        "[1,5,1]"
      ],
      [
        "next_permutation([])",
        "[]"
      ],
      [
        "next_permutation([2,3,1])",
        "[3,1,2]"
      ]
    ],
    "reference": "\ndef next_permutation(nums):\n    a = list(nums)\n    i = len(a) - 2\n    while i >= 0 and a[i] >= a[i + 1]:\n        i -= 1\n    if i < 0:\n        return sorted(a)\n    j = len(a) - 1\n    while a[j] <= a[i]:\n        j -= 1\n    a[i], a[j] = a[j], a[i]\n    a[i + 1:] = reversed(a[i + 1:])\n    return a\n",
    "type": "function"
  },
  {
    "id": "group_anagrams",
    "filename": "group_anagrams.py",
    "func_name": "group_anagrams",
    "desc": "Build a Python module with a function group_anagrams(words) that groups words that are anagrams of each other. Return a list of groups; each group is a list of words in the order they appeared in the input, and the groups themselves are ordered by where their first member appeared. Comparison is case-sensitive. group_anagrams([]) returns [].",
    "tests": [
      [
        "group_anagrams(['eat','tea','tan','ate','nat','bat'])",
        "[['eat','tea','ate'],['tan','nat'],['bat']]"
      ],
      [
        "group_anagrams([])",
        "[]"
      ],
      [
        "group_anagrams([''])",
        "[['']]"
      ],
      [
        "group_anagrams(['a'])",
        "[['a']]"
      ],
      [
        "group_anagrams(['ab','ba','AB'])",
        "[['ab','ba'],['AB']]"
      ]
    ],
    "reference": "\ndef group_anagrams(words):\n    groups = {}\n    order = []\n    for w in words:\n        key = \"\".join(sorted(w))\n        if key not in groups:\n            groups[key] = []\n            order.append(key)\n        groups[key].append(w)\n    return [groups[k] for k in order]\n",
    "type": "function"
  },
  {
    "id": "search_insert",
    "filename": "search_insert.py",
    "func_name": "search_insert",
    "desc": "Build a Python module with a function search_insert(nums, target) that returns the index of target in the sorted list nums, or, if target is absent, the index where it would be inserted to keep the list sorted. If nums contains duplicates of target, return the index of the FIRST occurrence. search_insert([], 1) returns 0.",
    "tests": [
      [
        "search_insert([1,3,5,6], 5)",
        "2"
      ],
      [
        "search_insert([1,3,5,6], 2)",
        "1"
      ],
      [
        "search_insert([], 1)",
        "0"
      ],
      [
        "search_insert([1,3,5,6], 7)",
        "4"
      ],
      [
        "search_insert([2,2,2], 2)",
        "0"
      ]
    ],
    "reference": "\ndef search_insert(nums, target):\n    lo, hi = 0, len(nums)\n    while lo < hi:\n        mid = (lo + hi) // 2\n        if nums[mid] < target:\n            lo = mid + 1\n        else:\n            hi = mid\n    return lo\n",
    "type": "function"
  },
  {
    "id": "rle_encode",
    "filename": "rle_encode.py",
    "func_name": "rle_encode",
    "desc": "Build a Python module with a function rle_encode(s) that run-length encodes a string. Each run of the same character becomes the character followed by its count, but a run of length 1 is written as the bare character with no count. rle_encode('aaabb') returns 'a3b2'. rle_encode('abc') returns 'abc'. rle_encode('') returns ''.",
    "tests": [
      [
        "rle_encode('aaabb')",
        "'a3b2'"
      ],
      [
        "rle_encode('abc')",
        "'abc'"
      ],
      [
        "rle_encode('')",
        "''"
      ],
      [
        "rle_encode('aaaaaaaaaa')",
        "'a10'"
      ],
      [
        "rle_encode('aabaa')",
        "'a2ba2'"
      ]
    ],
    "reference": "\ndef rle_encode(s):\n    if not s:\n        return \"\"\n    out = []\n    prev, count = s[0], 1\n    for ch in s[1:]:\n        if ch == prev:\n            count += 1\n        else:\n            out.append(prev if count == 1 else prev + str(count))\n            prev, count = ch, 1\n    out.append(prev if count == 1 else prev + str(count))\n    return \"\".join(out)\n",
    "type": "function"
  },
  {
    "id": "valid_ipv4",
    "filename": "valid_ipv4.py",
    "func_name": "is_valid_ipv4",
    "desc": "Build a Python module with a function is_valid_ipv4(s) that returns True if s is a valid dotted-quad IPv4 address. There must be exactly four parts separated by '.', each part must be all digits, each must be between 0 and 255 inclusive, and no part may have a leading zero unless the part is exactly '0'. Anything else returns False.",
    "tests": [
      [
        "is_valid_ipv4('192.168.0.1')",
        "True"
      ],
      [
        "is_valid_ipv4('256.1.1.1')",
        "False"
      ],
      [
        "is_valid_ipv4('01.1.1.1')",
        "False"
      ],
      [
        "is_valid_ipv4('1.1.1')",
        "False"
      ],
      [
        "is_valid_ipv4('0.0.0.0')",
        "True"
      ]
    ],
    "reference": "\ndef is_valid_ipv4(s):\n    parts = s.split(\".\")\n    if len(parts) != 4:\n        return False\n    for p in parts:\n        if not p or not p.isdigit():\n            return False\n        if len(p) > 1 and p[0] == \"0\":\n            return False\n        if int(p) > 255:\n            return False\n    return True\n",
    "type": "function"
  },
  {
    "id": "rotate_matrix",
    "filename": "rotate_matrix.py",
    "func_name": "rotate",
    "desc": "Build a Python module with a function rotate(matrix) that returns a NEW square matrix rotated 90 degrees clockwise. The input is a list of equal-length lists and must not be modified. rotate([]) returns []. A 1x1 matrix is returned unchanged.",
    "tests": [
      [
        "rotate([[1,2],[3,4]])",
        "[[3,1],[4,2]]"
      ],
      [
        "rotate([])",
        "[]"
      ],
      [
        "rotate([[5]])",
        "[[5]]"
      ],
      [
        "rotate([[1,2,3],[4,5,6],[7,8,9]])",
        "[[7,4,1],[8,5,2],[9,6,3]]"
      ],
      [
        "rotate([[1,2],[3,4],[5,6]])",
        "[[5,3,1],[6,4,2]]"
      ]
    ],
    "reference": "\ndef rotate(matrix):\n    if not matrix or not matrix[0]:\n        return []\n    return [list(row) for row in zip(*matrix[::-1])]\n",
    "type": "function"
  },
  {
    "id": "my_atoi",
    "filename": "my_atoi.py",
    "func_name": "my_atoi",
    "desc": "Build a Python module with a function my_atoi(s) that parses a leading integer out of a string. Skip leading whitespace, then read an optional single '+' or '-' sign, then read digits until a non-digit or the end. Return the resulting integer. If there are no digits after the optional sign, return 0. Clamp the result to the 32-bit signed range, so anything above 2147483647 returns 2147483647 and anything below -2147483648 returns -2147483648.",
    "tests": [
      [
        "my_atoi('   -42abc')",
        "-42"
      ],
      [
        "my_atoi('words 99')",
        "0"
      ],
      [
        "my_atoi('')",
        "0"
      ],
      [
        "my_atoi('91283472332')",
        "2147483647"
      ],
      [
        "my_atoi('+-12')",
        "0"
      ]
    ],
    "reference": "\ndef my_atoi(s):\n    i, n = 0, len(s)\n    while i < n and s[i].isspace():\n        i += 1\n    sign = 1\n    if i < n and s[i] in \"+-\":\n        sign = -1 if s[i] == \"-\" else 1\n        i += 1\n    start = i\n    while i < n and s[i].isdigit():\n        i += 1\n    if i == start:\n        return 0\n    val = sign * int(s[start:i])\n    return max(-2147483648, min(2147483647, val))\n",
    "type": "function"
  },
  {
    "id": "count_islands",
    "filename": "count_islands.py",
    "func_name": "count_islands",
    "desc": "Build a Python module with a function count_islands(grid) that counts connected groups of the integer 1 in a rectangular grid of 0s and 1s. Cells are connected only horizontally and vertically, never diagonally. The grid must not be modified. count_islands([]) returns 0.",
    "tests": [
      [
        "count_islands([[1,1,0],[0,1,0],[0,0,1]])",
        "2"
      ],
      [
        "count_islands([])",
        "0"
      ],
      [
        "count_islands([[0,0],[0,0]])",
        "0"
      ],
      [
        "count_islands([[1,0,1],[0,0,0],[1,0,1]])",
        "4"
      ],
      [
        "count_islands([[1,1],[1,1]])",
        "1"
      ]
    ],
    "reference": "\ndef count_islands(grid):\n    if not grid or not grid[0]:\n        return 0\n    rows, cols = len(grid), len(grid[0])\n    seen = set()\n    count = 0\n    for r in range(rows):\n        for c in range(cols):\n            if grid[r][c] != 1 or (r, c) in seen:\n                continue\n            count += 1\n            stack = [(r, c)]\n            seen.add((r, c))\n            while stack:\n                y, x = stack.pop()\n                for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):\n                    ny, nx = y + dy, x + dx\n                    if 0 <= ny < rows and 0 <= nx < cols:\n                        if grid[ny][nx] == 1 and (ny, nx) not in seen:\n                            seen.add((ny, nx))\n                            stack.append((ny, nx))\n    return count\n",
    "type": "function"
  },
  {
    "id": "longest_unique_substring",
    "filename": "longest_unique_substring.py",
    "func_name": "longest_unique",
    "desc": "Build a Python module with a function longest_unique(s) that returns the length of the longest substring of s containing no repeated character. longest_unique('') returns 0. Characters are compared case-sensitively, and whitespace counts as a character.",
    "tests": [
      [
        "longest_unique('abcabcbb')",
        "3"
      ],
      [
        "longest_unique('')",
        "0"
      ],
      [
        "longest_unique('bbbbb')",
        "1"
      ],
      [
        "longest_unique('pwwkew')",
        "3"
      ],
      [
        "longest_unique('aAbB')",
        "4"
      ]
    ],
    "reference": "\ndef longest_unique(s):\n    last = {}\n    best = start = 0\n    for i, ch in enumerate(s):\n        if ch in last and last[ch] >= start:\n            start = last[ch] + 1\n        last[ch] = i\n        best = max(best, i - start + 1)\n    return best\n",
    "type": "function"
  },
  {
    "id": "merge_k_sorted",
    "filename": "merge_k_sorted.py",
    "func_name": "merge_sorted",
    "desc": "Build a Python module with a function merge_sorted(lists) that merges any number of ascending-sorted integer lists into a single ascending-sorted list containing every element, duplicates included. Empty inner lists are allowed and contribute nothing. merge_sorted([]) returns [].",
    "tests": [
      [
        "merge_sorted([[1,4,5],[1,3,4],[2,6]])",
        "[1,1,2,3,4,4,5,6]"
      ],
      [
        "merge_sorted([])",
        "[]"
      ],
      [
        "merge_sorted([[],[]])",
        "[]"
      ],
      [
        "merge_sorted([[1]])",
        "[1]"
      ],
      [
        "merge_sorted([[2,2],[2]])",
        "[2,2,2]"
      ]
    ],
    "reference": "\ndef merge_sorted(lists):\n    out = []\n    for lst in lists:\n        out.extend(lst)\n    return sorted(out)\n",
    "type": "function"
  },
  {
    "id": "eval_rpn",
    "filename": "eval_rpn.py",
    "func_name": "eval_rpn",
    "desc": "Build a Python module with a function eval_rpn(tokens) that evaluates a list of reverse-Polish-notation tokens and returns an integer. Operators are '+', '-', '*' and '/'; every other token is an integer literal, possibly negative. Division truncates toward zero, so 7/-2 is -3. The expression is always valid. eval_rpn([]) returns 0.",
    "tests": [
      [
        "eval_rpn(['2','1','+','3','*'])",
        "9"
      ],
      [
        "eval_rpn([])",
        "0"
      ],
      [
        "eval_rpn(['4','13','5','/','+'])",
        "6"
      ],
      [
        "eval_rpn(['7','-2','/'])",
        "-3"
      ],
      [
        "eval_rpn(['-5'])",
        "-5"
      ]
    ],
    "reference": "\ndef eval_rpn(tokens):\n    if not tokens:\n        return 0\n    stack = []\n    for t in tokens:\n        if t in (\"+\", \"-\", \"*\", \"/\"):\n            b = stack.pop()\n            a = stack.pop()\n            if t == \"+\":\n                stack.append(a + b)\n            elif t == \"-\":\n                stack.append(a - b)\n            elif t == \"*\":\n                stack.append(a * b)\n            else:\n                stack.append(int(a / b))\n        else:\n            stack.append(int(t))\n    return stack[-1]\n",
    "type": "function"
  },
  {
    "id": "edit_distance",
    "filename": "edit_distance.py",
    "func_name": "edit_distance",
    "desc": "Build a Python module with a function edit_distance(a, b) that returns the Levenshtein distance between two strings: the least number of single-character insertions, deletions or substitutions needed to turn a into b. edit_distance('', '') returns 0 and edit_distance('abc', '') returns 3.",
    "tests": [
      [
        "edit_distance('kitten','sitting')",
        "3"
      ],
      [
        "edit_distance('','')",
        "0"
      ],
      [
        "edit_distance('abc','')",
        "3"
      ],
      [
        "edit_distance('same','same')",
        "0"
      ],
      [
        "edit_distance('a','b')",
        "1"
      ]
    ],
    "reference": "\ndef edit_distance(a, b):\n    prev = list(range(len(b) + 1))\n    for i, ca in enumerate(a, 1):\n        cur = [i]\n        for j, cb in enumerate(b, 1):\n            cur.append(min(prev[j] + 1, cur[j - 1] + 1,\n                           prev[j - 1] + (ca != cb)))\n        prev = cur\n    return prev[-1]\n",
    "type": "function"
  },
  {
    "id": "chunk_list",
    "filename": "chunk_list.py",
    "func_name": "chunk",
    "desc": "Build a Python module with a function chunk(items, size) that splits a list into consecutive chunks of length `size`, returned as a list of lists. The final chunk may be shorter if the list does not divide evenly. chunk([], 3) returns []. If size is less than 1, return [].",
    "tests": [
      [
        "chunk([1,2,3,4,5], 2)",
        "[[1,2],[3,4],[5]]"
      ],
      [
        "chunk([], 3)",
        "[]"
      ],
      [
        "chunk([1,2,3], 5)",
        "[[1,2,3]]"
      ],
      [
        "chunk([1,2,3], 0)",
        "[]"
      ],
      [
        "chunk([1,2,3,4], 4)",
        "[[1,2,3,4]]"
      ]
    ],
    "reference": "\ndef chunk(items, size):\n    if size < 1:\n        return []\n    return [list(items[i:i + size]) for i in range(0, len(items), size)]\n",
    "type": "function"
  },
  {
    "id": "sort_by_frequency",
    "filename": "sort_by_frequency.py",
    "func_name": "by_frequency",
    "desc": "Build a Python module with a function by_frequency(items) that returns the distinct items ordered by how often they appear, most frequent first. Items with the same count keep the order in which they first appeared in the input. by_frequency([]) returns [].",
    "tests": [
      [
        "by_frequency(['a','b','a','c','b','a'])",
        "['a','b','c']"
      ],
      [
        "by_frequency([])",
        "[]"
      ],
      [
        "by_frequency([1,2,3])",
        "[1,2,3]"
      ],
      [
        "by_frequency([3,3,1,1,2])",
        "[3,1,2]"
      ],
      [
        "by_frequency(['x'])",
        "['x']"
      ]
    ],
    "reference": "\ndef by_frequency(items):\n    counts = {}\n    order = []\n    for it in items:\n        if it not in counts:\n            counts[it] = 0\n            order.append(it)\n        counts[it] += 1\n    return sorted(order, key=lambda x: -counts[x])\n",
    "type": "function"
  },
  {
    "id": "product_except_self",
    "filename": "product_except_self.py",
    "func_name": "product_except_self",
    "desc": "Build a Python module with a function product_except_self(nums) that returns a list where each position holds the product of every other element of nums. Do not use division. product_except_self([]) returns []. A single-element list returns [1]. Zeros in the input are handled by the same rule as any other value.",
    "tests": [
      [
        "product_except_self([1,2,3,4])",
        "[24,12,8,6]"
      ],
      [
        "product_except_self([])",
        "[]"
      ],
      [
        "product_except_self([5])",
        "[1]"
      ],
      [
        "product_except_self([0,4,0])",
        "[0,0,0]"
      ],
      [
        "product_except_self([1,0,3])",
        "[0,3,0]"
      ]
    ],
    "reference": "\ndef product_except_self(nums):\n    n = len(nums)\n    if n == 0:\n        return []\n    out = [1] * n\n    left = 1\n    for i in range(n):\n        out[i] = left\n        left *= nums[i]\n    right = 1\n    for i in range(n - 1, -1, -1):\n        out[i] *= right\n        right *= nums[i]\n    return out\n",
    "type": "function"
  },
  {
    "id": "interval_intersection",
    "filename": "interval_intersection.py",
    "func_name": "intersect",
    "desc": "Build a Python module with a function intersect(a, b) that takes two lists of [start, end] intervals, each list already sorted by start and internally non-overlapping, and returns the list of intervals covered by both. Intervals are inclusive, so [1,3] and [3,5] intersect at [3,3]. Return [] if either list is empty.",
    "tests": [
      [
        "intersect([[0,2],[5,10]], [[1,5],[8,12]])",
        "[[1,2],[5,5],[8,10]]"
      ],
      [
        "intersect([], [[1,2]])",
        "[]"
      ],
      [
        "intersect([[1,3]], [[3,5]])",
        "[[3,3]]"
      ],
      [
        "intersect([[1,2]], [[3,4]])",
        "[]"
      ],
      [
        "intersect([[1,10]], [[2,3],[5,6]])",
        "[[2,3],[5,6]]"
      ]
    ],
    "reference": "\ndef intersect(a, b):\n    out = []\n    i = j = 0\n    while i < len(a) and j < len(b):\n        lo = max(a[i][0], b[j][0])\n        hi = min(a[i][1], b[j][1])\n        if lo <= hi:\n            out.append([lo, hi])\n        if a[i][1] < b[j][1]:\n            i += 1\n        else:\n            j += 1\n    return out\n",
    "type": "function"
  },
  {
    "id": "justify_text",
    "filename": "justify_text.py",
    "func_name": "justify",
    "desc": "Build a Python module with a function justify(words, width) that fully justifies text. Greedily pack as many words as fit on each line (words separated by at least one space). Pad each line to exactly `width` characters by distributing spaces as evenly as possible between words, giving the extra spaces to the LEFTMOST gaps first. The last line, and any line holding a single word, is left-justified with single spaces and padded on the right. Return a list of lines. justify([], 5) returns [].",
    "tests": [
      [
        "justify(['This','is','an','example','of','text','justification.'], 16)",
        "['This    is    an','example  of text','justification.  ']"
      ],
      [
        "justify([], 5)",
        "[]"
      ],
      [
        "justify(['a'], 4)",
        "['a   ']"
      ],
      [
        "justify(['what','must','be'], 6)",
        "['what  ','must  ','be    ']"
      ],
      [
        "justify(['ab','cd','ef'], 5)",
        "['ab cd','ef   ']"
      ]
    ],
    "reference": "\ndef justify(words, width):\n    if not words:\n        return []\n    lines = []\n    cur = []\n    cur_len = 0\n    for w in words:\n        if cur and cur_len + len(cur) + len(w) > width:\n            lines.append(cur)\n            cur, cur_len = [], 0\n        cur.append(w)\n        cur_len += len(w)\n    lines.append(cur)\n    out = []\n    for idx, line in enumerate(lines):\n        if idx == len(lines) - 1 or len(line) == 1:\n            s = \" \".join(line)\n            out.append(s + \" \" * (width - len(s)))\n        else:\n            total_spaces = width - sum(len(w) for w in line)\n            gaps = len(line) - 1\n            base, extra = divmod(total_spaces, gaps)\n            s = \"\"\n            for i, w in enumerate(line[:-1]):\n                s += w + \" \" * (base + (1 if i < extra else 0))\n            s += line[-1]\n            out.append(s)\n    return out\n",
    "type": "function"
  },
  {
    "id": "caesar_cipher",
    "filename": "caesar_cipher.py",
    "func_name": "caesar",
    "desc": "Build a Python module with a function caesar(text, shift) that shifts every ASCII letter forward by `shift` positions, wrapping within its own case. Non-letters are left unchanged. shift may be negative or larger than 26. caesar('abc', 1) returns 'bcd'. caesar('', 5) returns ''.",
    "tests": [
      [
        "caesar('abc', 1)",
        "'bcd'"
      ],
      [
        "caesar('', 5)",
        "''"
      ],
      [
        "caesar('Zebra!', 1)",
        "'Afcsb!'"
      ],
      [
        "caesar('abc', -1)",
        "'zab'"
      ],
      [
        "caesar('abc', 27)",
        "'bcd'"
      ]
    ],
    "reference": "\ndef caesar(text, shift):\n    out = []\n    for ch in text:\n        if \"a\" <= ch <= \"z\":\n            out.append(chr((ord(ch) - 97 + shift) % 26 + 97))\n        elif \"A\" <= ch <= \"Z\":\n            out.append(chr((ord(ch) - 65 + shift) % 26 + 65))\n        else:\n            out.append(ch)\n    return \"\".join(out)\n",
    "type": "function"
  },
  {
    "id": "palindrome_alnum",
    "filename": "palindrome_alnum.py",
    "func_name": "is_palindrome",
    "desc": "Build a Python module with a function is_palindrome(s) that returns True if s reads the same forwards and backwards once every non-alphanumeric character is removed and case is ignored. The empty string is a palindrome. Digits count as alphanumeric.",
    "tests": [
      [
        "is_palindrome('A man, a plan, a canal: Panama')",
        "True"
      ],
      [
        "is_palindrome('')",
        "True"
      ],
      [
        "is_palindrome('race a car')",
        "False"
      ],
      [
        "is_palindrome('0P')",
        "False"
      ],
      [
        "is_palindrome('12321')",
        "True"
      ]
    ],
    "reference": "\ndef is_palindrome(s):\n    cleaned = [ch.lower() for ch in s if ch.isalnum()]\n    return cleaned == cleaned[::-1]\n",
    "type": "function"
  },
  {
    "id": "pascal_row",
    "filename": "pascal_row.py",
    "func_name": "pascal_row",
    "desc": "Build a Python module with a function pascal_row(n) that returns row n of Pascal's triangle as a list of integers, where row 0 is [1]. pascal_row(4) returns [1,4,6,4,1]. If n is negative, return [].",
    "tests": [
      [
        "pascal_row(0)",
        "[1]"
      ],
      [
        "pascal_row(4)",
        "[1,4,6,4,1]"
      ],
      [
        "pascal_row(-1)",
        "[]"
      ],
      [
        "pascal_row(1)",
        "[1,1]"
      ],
      [
        "pascal_row(6)",
        "[1,6,15,20,15,6,1]"
      ]
    ],
    "reference": "\ndef pascal_row(n):\n    if n < 0:\n        return []\n    row = [1]\n    for k in range(n):\n        row.append(row[-1] * (n - k) // (k + 1))\n    return row\n",
    "type": "function"
  },
  {
    "id": "digital_root",
    "filename": "digital_root.py",
    "func_name": "digital_root",
    "desc": "Build a Python module with a function digital_root(n) that repeatedly sums the decimal digits of the non-negative integer n until a single digit remains, and returns it. digital_root(0) returns 0. digital_root(9875) returns 2.",
    "tests": [
      [
        "digital_root(0)",
        "0"
      ],
      [
        "digital_root(9875)",
        "2"
      ],
      [
        "digital_root(9)",
        "9"
      ],
      [
        "digital_root(10)",
        "1"
      ],
      [
        "digital_root(199)",
        "1"
      ]
    ],
    "reference": "\ndef digital_root(n):\n    while n > 9:\n        n = sum(int(c) for c in str(n))\n    return n\n",
    "type": "function"
  },
  {
    "id": "min_jumps",
    "filename": "min_jumps.py",
    "func_name": "min_jumps",
    "desc": "Build a Python module with a function min_jumps(nums) that returns the least number of jumps needed to reach the last index of the list, starting at index 0, where nums[i] is the maximum jump length from position i. If the last index cannot be reached, return -1. A list of length 0 or 1 needs 0 jumps.",
    "tests": [
      [
        "min_jumps([2,3,1,1,4])",
        "2"
      ],
      [
        "min_jumps([])",
        "0"
      ],
      [
        "min_jumps([0])",
        "0"
      ],
      [
        "min_jumps([3,2,1,0,4])",
        "-1"
      ],
      [
        "min_jumps([1,1,1,1])",
        "3"
      ]
    ],
    "reference": "\ndef min_jumps(nums):\n    n = len(nums)\n    if n <= 1:\n        return 0\n    jumps = 0\n    cur_end = 0\n    farthest = 0\n    for i in range(n - 1):\n        if i > farthest:\n            return -1\n        farthest = max(farthest, i + nums[i])\n        if i == cur_end:\n            jumps += 1\n            cur_end = farthest\n            if cur_end >= n - 1:\n                return jumps\n    return -1 if farthest < n - 1 else jumps\n",
    "type": "function"
  },
  {
    "id": "topo_sort",
    "filename": "topo_sort.py",
    "func_name": "topo_sort",
    "desc": "Build a Python module with a function topo_sort(nodes, edges) that returns a topological ordering of `nodes` (a list) given `edges` (a list of [a, b] pairs meaning a must come before b). When several nodes are ready at once, take the one that appears earliest in `nodes`. If the graph has a cycle, return []. topo_sort([], []) returns [].",
    "tests": [
      [
        "topo_sort(['a','b','c'], [['a','b'],['b','c']])",
        "['a','b','c']"
      ],
      [
        "topo_sort([], [])",
        "[]"
      ],
      [
        "topo_sort(['a','b'], [['a','b'],['b','a']])",
        "[]"
      ],
      [
        "topo_sort(['c','a','b'], [['a','b']])",
        "['c','a','b']"
      ],
      [
        "topo_sort(['a','b','c'], [])",
        "['a','b','c']"
      ]
    ],
    "reference": "\ndef topo_sort(nodes, edges):\n    indeg = {n: 0 for n in nodes}\n    adj = {n: [] for n in nodes}\n    for a, b in edges:\n        adj[a].append(b)\n        indeg[b] += 1\n    out = []\n    remaining = list(nodes)\n    while remaining:\n        pick = None\n        for n in remaining:\n            if indeg[n] == 0:\n                pick = n\n                break\n        if pick is None:\n            return []\n        remaining.remove(pick)\n        out.append(pick)\n        for nb in adj[pick]:\n            indeg[nb] -= 1\n    return out\n",
    "type": "function"
  },
  {
    "id": "dedupe_ordered",
    "filename": "dedupe_ordered.py",
    "func_name": "dedupe",
    "desc": "Build a Python module with a function dedupe(items) that returns a new list with duplicates removed, keeping the FIRST occurrence of each value and the original order. The input must not be modified. dedupe([]) returns []. Values that compare equal are treated as duplicates.",
    "tests": [
      [
        "dedupe([1,2,1,3,2])",
        "[1,2,3]"
      ],
      [
        "dedupe([])",
        "[]"
      ],
      [
        "dedupe(['a','a','a'])",
        "['a']"
      ],
      [
        "dedupe([3,2,1])",
        "[3,2,1]"
      ],
      [
        "dedupe([0,False,1])",
        "[0,1]"
      ]
    ],
    "reference": "\ndef dedupe(items):\n    seen = set()\n    out = []\n    for it in items:\n        if it not in seen:\n            seen.add(it)\n            out.append(it)\n    return out\n",
    "type": "function"
  },
  {
    "id": "moving_average",
    "filename": "moving_average.py",
    "func_name": "moving_average",
    "desc": "Build a Python module with a function moving_average(nums, k) that returns the list of averages of every consecutive window of length k, each rounded to 2 decimal places with the built-in round. If k is less than 1 or greater than the length of nums, return []. moving_average([], 1) returns [].",
    "tests": [
      [
        "moving_average([1,2,3,4], 2)",
        "[1.5, 2.5, 3.5]"
      ],
      [
        "moving_average([], 1)",
        "[]"
      ],
      [
        "moving_average([1,2], 3)",
        "[]"
      ],
      [
        "moving_average([1,2,3], 3)",
        "[2.0]"
      ],
      [
        "moving_average([1,1,4], 2)",
        "[1.0, 2.5]"
      ]
    ],
    "reference": "\ndef moving_average(nums, k):\n    if k < 1 or k > len(nums):\n        return []\n    out = []\n    for i in range(len(nums) - k + 1):\n        out.append(round(sum(nums[i:i + k]) / k, 2))\n    return out\n",
    "type": "function"
  },
  {
    "id": "gcd_lcm",
    "filename": "gcd_lcm.py",
    "func_name": "gcd_lcm",
    "desc": "Build a Python module with a function gcd_lcm(a, b) that returns the tuple (gcd, lcm) of two non-negative integers. The gcd of 0 and 0 is 0, and their lcm is also 0. When either value is 0 the lcm is 0. gcd_lcm(12, 18) returns (6, 36).",
    "tests": [
      [
        "gcd_lcm(12, 18)",
        "(6, 36)"
      ],
      [
        "gcd_lcm(0, 0)",
        "(0, 0)"
      ],
      [
        "gcd_lcm(0, 5)",
        "(5, 0)"
      ],
      [
        "gcd_lcm(7, 13)",
        "(1, 91)"
      ],
      [
        "gcd_lcm(4, 4)",
        "(4, 4)"
      ]
    ],
    "reference": "\ndef gcd_lcm(a, b):\n    x, y = a, b\n    while y:\n        x, y = y, x % y\n    g = x\n    lcm = 0 if (a == 0 or b == 0) else a * b // g\n    return (g, lcm)\n",
    "type": "function"
  },
  {
    "id": "two_sum_sorted",
    "filename": "two_sum_sorted.py",
    "func_name": "two_sum",
    "desc": "Build a Python module with a function two_sum(nums, target) that finds two DIFFERENT positions in the ascending-sorted list nums whose values add up to target, and returns them as a list of two zero-based indices in increasing order. If several pairs work, return the one with the smallest first index; if that ties, the smallest second index. Return [] if no pair works.",
    "tests": [
      [
        "two_sum([2,7,11,15], 9)",
        "[0,1]"
      ],
      [
        "two_sum([2,3,4], 6)",
        "[0,2]"
      ],
      [
        "two_sum([], 1)",
        "[]"
      ],
      [
        "two_sum([1,2], 100)",
        "[]"
      ],
      [
        "two_sum([0,0,3], 0)",
        "[0,1]"
      ]
    ],
    "reference": "\ndef two_sum(nums, target):\n    for i in range(len(nums)):\n        for j in range(i + 1, len(nums)):\n            if nums[i] + nums[j] == target:\n                return [i, j]\n    return []\n",
    "type": "function"
  },
  {
    "id": "expand_tabs",
    "filename": "expand_tabs.py",
    "func_name": "expand_tabs",
    "desc": "Build a Python module with a function expand_tabs(line, tabsize) that replaces every tab character with spaces up to the next tab stop. Tab stops sit at every multiple of tabsize counted from the start of the line, so a tab always inserts at least one space. Other characters are copied unchanged and each advances the column by one. expand_tabs('', 4) returns ''. If tabsize is less than 1, return the line unchanged.",
    "tests": [
      [
        "expand_tabs('a\\tb', 4)",
        "'a   b'"
      ],
      [
        "expand_tabs('', 4)",
        "''"
      ],
      [
        "expand_tabs('\\t', 4)",
        "'    '"
      ],
      [
        "expand_tabs('abcd\\te', 4)",
        "'abcd    e'"
      ],
      [
        "expand_tabs('a\\tb', 0)",
        "'a\\tb'"
      ]
    ],
    "reference": "\ndef expand_tabs(line, tabsize):\n    if tabsize < 1:\n        return line\n    out = []\n    col = 0\n    for ch in line:\n        if ch == \"\\t\":\n            pad = tabsize - (col % tabsize)\n            out.append(\" \" * pad)\n            col += pad\n        else:\n            out.append(ch)\n            col += 1\n    return \"\".join(out)\n",
    "type": "function"
  },
  {
    "id": "version_compare",
    "filename": "version_compare.py",
    "func_name": "compare_versions",
    "desc": "Build a Python module with a function compare_versions(a, b) that compares two dot-separated version strings numerically and returns -1 if a is older, 1 if a is newer, and 0 if they are equal. Each part is an integer, leading zeros are allowed and insignificant, and a missing trailing part counts as 0, so '1.0' equals '1'.",
    "tests": [
      [
        "compare_versions('1.0', '1')",
        "0"
      ],
      [
        "compare_versions('1.2', '1.10')",
        "-1"
      ],
      [
        "compare_versions('2.0', '1.9.9')",
        "1"
      ],
      [
        "compare_versions('1.01', '1.1')",
        "0"
      ],
      [
        "compare_versions('1.0.0', '1.0.1')",
        "-1"
      ]
    ],
    "reference": "\ndef compare_versions(a, b):\n    pa = [int(x) for x in a.split(\".\")]\n    pb = [int(x) for x in b.split(\".\")]\n    for i in range(max(len(pa), len(pb))):\n        va = pa[i] if i < len(pa) else 0\n        vb = pb[i] if i < len(pb) else 0\n        if va < vb:\n            return -1\n        if va > vb:\n            return 1\n    return 0\n",
    "type": "function"
  },
  {
    "id": "csv_split",
    "filename": "csv_split.py",
    "func_name": "split_csv_line",
    "desc": "Build a Python module with a function split_csv_line(line) that splits one line of CSV into a list of field strings. A field wrapped in double quotes may contain commas and doubled quotes: inside a quoted field, '\"\"' means one literal quote character. Quotes are removed from the result. Unquoted fields are taken as-is with no trimming. split_csv_line('') returns [''].",
    "tests": [
      [
        "split_csv_line('a,b,c')",
        "['a','b','c']"
      ],
      [
        "split_csv_line('')",
        "['']"
      ],
      [
        "split_csv_line('a,\"b,c\",d')",
        "['a','b,c','d']"
      ],
      [
        "split_csv_line('\"say \"\"hi\"\"\",x')",
        "['say \"hi\"','x']"
      ],
      [
        "split_csv_line('a,,b')",
        "['a','','b']"
      ]
    ],
    "reference": "\ndef split_csv_line(line):\n    fields = []\n    cur = []\n    i = 0\n    in_quotes = False\n    while i < len(line):\n        ch = line[i]\n        if in_quotes:\n            if ch == '\"':\n                if i + 1 < len(line) and line[i + 1] == '\"':\n                    cur.append('\"')\n                    i += 2\n                    continue\n                in_quotes = False\n            else:\n                cur.append(ch)\n        else:\n            if ch == '\"':\n                in_quotes = True\n            elif ch == \",\":\n                fields.append(\"\".join(cur))\n                cur = []\n            else:\n                cur.append(ch)\n        i += 1\n    fields.append(\"\".join(cur))\n    return fields\n",
    "type": "function"
  },
  {
    "id": "binary_gap",
    "filename": "binary_gap.py",
    "func_name": "binary_gap",
    "desc": "Build a Python module with a function binary_gap(n) that returns the length of the longest run of consecutive zeros in the binary representation of the positive integer n that is bounded by a 1 on both sides. If there is no such run, return 0. binary_gap(9) is 2 because 9 is 1001. binary_gap(0) returns 0.",
    "tests": [
      [
        "binary_gap(9)",
        "2"
      ],
      [
        "binary_gap(0)",
        "0"
      ],
      [
        "binary_gap(529)",
        "4"
      ],
      [
        "binary_gap(20)",
        "1"
      ],
      [
        "binary_gap(15)",
        "0"
      ]
    ],
    "reference": "\ndef binary_gap(n):\n    if n <= 0:\n        return 0\n    bits = bin(n)[2:]\n    best = 0\n    cur = None\n    for ch in bits:\n        if ch == \"1\":\n            if cur is not None:\n                best = max(best, cur)\n            cur = 0\n        elif cur is not None:\n            cur += 1\n    return best\n",
    "type": "function"
  }
]
