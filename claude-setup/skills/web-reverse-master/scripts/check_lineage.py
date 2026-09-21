#!/usr/bin/env python3
"""Offline HAR inventory and analyst-recorded lineage checks (stdlib, Python 3.10+).

This validates files, graph structure and declared evidence conditions. It cannot
authenticate evidence, infer hidden dependencies, or decide business semantics.
Neither init nor check performs network requests or executes referenced code.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
from urllib.parse import parse_qsl, urlsplit


CLAIM = "structural checks and analyst assertions only; authenticity and semantic truth unverified"
SHA256 = re.compile(r"^[0-9a-f]{64}$")


class Invalid(ValueError):
    def __init__(self, code, where, next_step):
        self.issue = {"code": code, "at": where, "next": next_step}
        super().__init__(f"{code}: {where}: {next_step}")


def fail(code, where, next_step):
    raise Invalid(code, where, next_step)


def require(condition, code, where, next_step):
    if not condition:
        fail(code, where, next_step)


def obj(value, where):
    require(isinstance(value, dict), "TYPE", where, "Use a JSON object.")
    return value


def arr(value, where):
    require(isinstance(value, list), "TYPE", where, "Use a JSON array.")
    return value


def string(value, where, nonempty=False):
    require(isinstance(value, str), "TYPE", where, "Use a string.")
    require(not nonempty or bool(value.strip()), "EMPTY", where, "Supply a nonempty string.")
    return value


def strings(value, where):
    arr(value, where)
    for index, item in enumerate(value):
        string(item, f"{where}/{index}", True)
    require(len(set(value)) == len(value), "DUPLICATE", where, "Remove duplicate references.")
    return value


def integer(value, where):
    require(type(value) is int and value >= 0, "TYPE", where, "Use a nonnegative integer.")
    return value


def choice(value, options, where):
    string(value, where)
    require(value in options, "ENUM", where, "Use one of: " + ", ".join(sorted(options)))


def keys(value, required, where):
    obj(value, where)
    for key in required:
        require(key in value, "MISSING", where + "/" + key, "Add the required field.")


def unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "DUPLICATE_JSON_KEY", "JSON", "Remove duplicate JSON keys.")
        result[key] = value
    return result


def read_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"), object_pairs_hook=unique_pairs,
                          parse_constant=lambda _: fail("JSON_NUMBER", "JSON", "Use finite JSON numbers."))
    except Invalid:
        raise
    except (UnicodeError, ValueError):
        fail("JSON_PARSE", path.name, "Supply valid UTF-8 JSON.")


def digest(path):
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def is_link(path):
    info = path.lstat()
    return stat.S_ISLNK(info.st_mode) or bool(getattr(info, "st_file_attributes", 0) & 0x400)


def root_path(value):
    root = Path(os.path.abspath(value))
    require(root.is_dir(), "ROOT", "project-root", "Use an existing project directory.")
    for part in (root, *root.parents):
        require(not is_link(part), "PATH_LINK", "project-root", "Use a physical directory without symlinks/junctions.")
    return root


def safe_path(root, value, where, *, relative=False, existing=False):
    string(value, where, True)
    require("\x00" not in value, "PATH_INVALID", where, "Use a path without NUL characters.")
    raw = Path(value)
    require(not relative or not raw.is_absolute(), "PATH_ABSOLUTE", where, "Use a project-relative artifact path.")
    require(not raw.drive or raw.is_absolute(), "PATH_DRIVE", where, "Do not use drive-relative paths.")
    # On Windows a colon can name an alternate data stream; no artifact uses one.
    require(not any(":" in p for p in raw.parts if p != raw.anchor),
            "PATH_STREAM", where, "Use an ordinary file path without alternate streams.")
    path = raw if raw.is_absolute() else root / raw
    require(".." not in path.parts, "PATH_ESCAPE", where, "Use a normalized path inside project-root.")
    path = Path(os.path.abspath(path))
    try:
        rel = path.relative_to(root)
    except ValueError:
        fail("PATH_ESCAPE", where, "Keep the file inside project-root.")
    current = root
    for part in rel.parts:
        current = current / part
        if os.path.lexists(current):
            require(not is_link(current), "PATH_LINK", where, "Do not reference symlinks/junctions.")
    require(not existing or path.is_file(), "FILE_MISSING", where, "Provide the referenced local file.")
    return path


def write_new(path, text):
    require(not os.path.lexists(path), "OUTPUT_EXISTS", path.name, "Choose a new output path; existing files are never overwritten.")
    # Validate encoding before creating the file: a lone JSON surrogate must not
    # leave an empty output that blocks a corrected retry.
    try:
        encoded = text.encode("utf-8")
    except UnicodeError:
        fail("JSON_UNICODE", "output", "Use Unicode scalar values without unpaired surrogates.")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(encoded)


def pointer_piece(value):
    return value.replace("~", "~0").replace("/", "~1")


def at_pointer(value, pointer, where):
    require(pointer.startswith("/"), "ANCHOR", where, "Use a JSON pointer beginning with /.")
    try:
        for token in pointer[1:].split("/"):
            require(not re.search(r"~(?:[^01]|$)", token), "ANCHOR", where, "Use only ~0 and ~1 JSON pointer escapes.")
            token = token.replace("~1", "/").replace("~0", "~")
            if isinstance(value, list):
                require(bool(re.fullmatch(r"0|[1-9][0-9]*", token)), "ANCHOR", where, "Use canonical nonnegative JSON array indices.")
                value = value[int(token)]
            else:
                value = value[token]
    except Invalid:
        raise
    except (KeyError, IndexError, TypeError, ValueError):
        fail("ANCHOR_MISSING", where, "Anchor the source to an existing captured JSON location.")
    return value


def har_entries(path):
    har = obj(read_json(path), "HAR")
    log = obj(har.get("log"), "HAR/log")
    entries = arr(log.get("entries"), "HAR/log/entries")
    return har, entries


def inventory(entry, index):
    """Return locations only, never request values. True means unsupported opaque body."""
    entry = obj(entry, f"HAR/entries/{index}")
    request = obj(entry.get("request"), f"HAR/entries/{index}/request")
    string(request.get("method"), "HAR/request/method", True)
    url = string(request.get("url"), "HAR/request/url", True)
    try:
        parsed = urlsplit(url)
        url_query = parse_qsl(parsed.query, keep_blank_values=True)
    except ValueError:
        fail("HAR_URL", f"HAR/entries/{index}", "Repair the malformed captured URL.")
    locations = {key: False for key in ("/method", "/url/scheme", "/url/host", "/url/path")}
    for i in range(len(url_query)):
        locations[f"/url/query/{i}"] = False
    if parsed.username is not None or parsed.password is not None:
        locations["/url/userinfo"] = False
    for group in ("headers", "queryString", "cookies"):
        for i, value in enumerate(arr(request.get(group, []), "HAR/request/" + group)):
            keys(value, ("name", "value"), "HAR/request/" + group)
            string(value["name"], "HAR/request/" + group + "/name")
            string(value["value"], "HAR/request/" + group + "/value")
            locations[f"/{group}/{i}/value"] = False
            if group == "headers" and value["name"].lower() == "cookie":
                for j, part in enumerate(value["value"].split(";")):
                    if part.strip():
                        locations[f"/headers/{i}/cookies/{j}/value"] = False
    body_size = request.get("bodySize", 0)
    require(type(body_size) is int, "TYPE", "HAR/request/bodySize", "Use an integer HAR bodySize.")
    body_headers = request.get("headers", [])
    nonempty_body = body_size > 0 or any(
        header["name"].lower() == "content-length" and header["value"].strip().lstrip("0")
        for header in body_headers)
    transfer_encoded = any(header["name"].lower() == "transfer-encoding" and header["value"].strip()
                           for header in body_headers)
    if "postData" not in request:
        if nonempty_body or (transfer_encoded and request.get("bodySize") != 0):
            locations["/postData/missing/opaque"] = True
        return locations
    post = obj(request["postData"], "HAR/request/postData")
    mime = string(post.get("mimeType", ""), "HAR/postData/mimeType").split(";", 1)[0].lower().strip()
    if "mimeType" in post:
        locations["/postData/mimeType"] = False
    params = arr(post.get("params", []), "HAR/postData/params")
    for i, param in enumerate(params):
        obj(param, "HAR/postData/params")
        string(param.get("name"), "HAR/postData/params/name")
        for member in ("value", "fileName", "contentType"):
            if member in param:
                string(param[member], "HAR/postData/params/" + member)
                locations[f"/postData/params/{i}/{member}"] = member == "fileName"
        if "value" not in param and "fileName" not in param:
            locations[f"/postData/params/{i}/opaque"] = True
    if "text" not in post:
        if not params:
            locations["/postData/opaque"] = True
        return locations
    body = string(post["text"], "HAR/postData/text")
    # HAR may describe form fields in params instead of text. An explicitly
    # empty text with no params cannot explain a declared nonempty body.
    # Transfer-Encoding alone is not proof of nonempty content (zero chunks).
    if not body and not params and nonempty_body:
        locations["/postData/missing/opaque"] = True
    if mime == "application/json" or mime.endswith("+json"):
        try:
            decoded = json.loads(body, object_pairs_hook=unique_pairs,
                                 parse_constant=lambda _: fail("JSON_NUMBER", "HAR/body", "Use finite JSON numbers."))
        except ValueError:
            # Includes Invalid, JSONDecodeError and the interpreter's integer
            # conversion limit. Unsupported JSON stays an explicit body gap.
            locations["/postData/text/opaque"] = True
            return locations

        def walk(value, location):
            if isinstance(value, dict) and value:
                for key, child in value.items():
                    try:
                        key.encode("utf-8")
                    except UnicodeError:
                        fail("JSON_UNICODE", "HAR/body/key", "Use Unicode scalar values without unpaired surrogates.")
                    walk(child, location + "/" + pointer_piece(key))
            elif isinstance(value, list) and value:
                for i, child in enumerate(value):
                    walk(child, location + "/" + str(i))
            else:
                locations[location] = False

        walk(decoded, "/postData/text/json")
    elif mime == "application/x-www-form-urlencoded":
        for i, _ in enumerate(parse_qsl(body, keep_blank_values=True)):
            locations[f"/postData/text/form/{i}"] = False
        if not body:
            locations["/postData/text/form"] = False
    else:
        locations["/postData/text/opaque"] = True
    return locations


def new_node(node_id, request_id, location):
    return {
        "id": node_id, "node_type": "field", "request_id": request_id, "location": location,
        "source": {"kind": "UNKNOWN", "producer": "", "artifact": "", "anchor": "", "realm": ""},
        "dependencies": [], "transformations": [], "encoding": "", "storage": "", "consumer": "",
        "lifecycle": {"status": "unknown", "description": "", "evidence_ids": []},
        "binding": {"status": "unknown", "description": "", "evidence_ids": []},
        "implementation": None, "evidence_ids": [],
        "gaps": [{"detail": "Observed request location; source and boundaries UNKNOWN.",
                  "next_experiment": "Trace this field to its producer, dependencies and consuming request; preserve local evidence."}],
    }


def initialize(root, har_name, output_name, entries_arg=None):
    har_path = safe_path(root, har_name, "har", existing=True)
    output = safe_path(root, output_name, "output")
    require(not os.path.lexists(output), "OUTPUT_EXISTS", "output", "Choose a new lineage file.")
    _, entries = har_entries(har_path)
    if entries_arg is None:
        selected = list(range(len(entries)))
    else:
        try:
            selected = [int(part) for part in entries_arg.split(",")]
        except ValueError:
            fail("ENTRIES", "entries", "Use comma-separated HAR entry indices, for example 0,2.")
    require(bool(selected) and len(set(selected)) == len(selected), "ENTRIES", "entries", "Select at least one unique HAR entry index.")
    require(all(0 <= i < len(entries) for i in selected), "ENTRIES", "entries", "Select only existing HAR entry indices.")
    data = {"version": 1, "capture": {"artifact": "capture", "entries": selected},
            "artifacts": [{"id": "capture", "path": har_path.relative_to(root).as_posix(),
                           "sha256": digest(har_path), "kind": "capture", "provenance": "unknown"}],
            "runs": [], "sessions": [], "requests": [], "nodes": [], "evidence": [],
            "algorithms": [], "business_targets": []}
    for index in selected:
        request_id = f"r{index}"
        data["requests"].append({"id": request_id, "entry_index": index, "predecessors": [],
                                 "state_before": "", "state_after": "", "epoch": "", "trigger": "",
                                 "realm": "", "session_id": "", "evidence_ids": []})
        for location in inventory(entries[index], index):
            data["nodes"].append(new_node(f"f{len(data['nodes'])}", request_id, location))
    write_new(output, json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    return {"valid": True, "initialized": output.relative_to(root).as_posix(),
            "requests": len(data["requests"]), "fields": len(data["nodes"]),
            "machine_claim": CLAIM, "next": "Fill UNKNOWN records and preserve evidence before requesting completion checks."}


def id_map(value, where):
    result = {}
    for i, item in enumerate(arr(value, where)):
        obj(item, f"{where}/{i}")
        key = string(item.get("id"), f"{where}/{i}/id", True)
        require(key not in result, "DUPLICATE_ID", where, "Use unique IDs within each collection.")
        result[key] = item
    return result


def references(values, mapping, where):
    for value in strings(values, where):
        require(value in mapping, "DANGLING", where, "Reference an existing ID.")


def graph_ancestors(mapping, member, where):
    done, visiting = {}, set()

    def visit(key):
        if key in done:
            return done[key]
        require(key not in visiting, "CYCLE", where + "/" + key, "Use a DAG; represent refresh epochs as new node/request instances.")
        visiting.add(key)
        found = set()
        for dependency in mapping[key][member]:
            found.add(dependency)
            found.update(visit(dependency))
        visiting.remove(key)
        done[key] = found
        return found

    for key in mapping:
        visit(key)
    return done


class Checker:
    def __init__(self, root, data):
        self.root, self.data = root, data
        self.paths, self.gaps = {}, []
        self.maps = {}
        self.opaque = set()

    def gap(self, code, where, next_step):
        issue = {"code": code, "at": where, "next": next_step}
        if issue not in self.gaps:
            self.gaps.append(issue)

    def node_assets(self, node_ids):
        assets = set()
        for node_id in node_ids:
            node = self.maps["nodes"][node_id]
            if node["source"]["artifact"]:
                assets.add(node["source"]["artifact"])
            if node["implementation"]:
                assets.add(node["implementation"]["artifact"])
        return assets

    def evidence_refs(self, value, where):
        references(value, self.maps["evidence"], where)

    def validate(self):
        data = self.data
        keys(data, ("version", "capture", "artifacts", "runs", "sessions", "requests", "nodes",
                    "evidence", "algorithms", "business_targets"), "lineage")
        require(type(data["version"]) is int and data["version"] == 1,
                "VERSION", "version", "Use supported lineage version 1.")
        for name in ("artifacts", "runs", "sessions", "requests", "nodes", "evidence", "algorithms", "business_targets"):
            self.maps[name] = id_map(data[name], name)
        artifacts = self.maps["artifacts"]
        seen_paths = set()
        for key, artifact in artifacts.items():
            keys(artifact, ("id", "path", "sha256", "kind", "provenance"), "artifacts/" + key)
            choice(artifact["kind"], {"capture", "code", "evidence"}, "artifacts/" + key + "/kind")
            choice(artifact["provenance"], {"unknown", "target", "fixture"}, "artifacts/" + key + "/provenance")
            claimed = string(artifact["sha256"], "artifacts/" + key + "/sha256")
            require(bool(SHA256.fullmatch(claimed)), "HASH_FORMAT", key, "Use a lowercase SHA-256 hex digest.")
            path = safe_path(self.root, artifact["path"], "artifacts/" + key + "/path", relative=True, existing=True)
            require(path not in seen_paths, "DUPLICATE_PATH", key, "Use one artifact ID for each physical file.")
            seen_paths.add(path)
            require(digest(path) == claimed, "HASH_CHANGED", "artifacts/" + key, "Preserve the old artifact and collect new evidence for the changed bytes.")
            self.paths[key] = path
        capture = data["capture"]
        keys(capture, ("artifact", "entries"), "capture")
        string(capture["artifact"], "capture/artifact", True)
        require(capture["artifact"] in artifacts, "DANGLING", "capture/artifact", "Reference the local HAR artifact.")
        require(artifacts[capture["artifact"]]["kind"] == "capture", "CAPTURE_KIND", "capture/artifact", "Use a capture artifact.")
        self.har, self.entries = har_entries(self.paths[capture["artifact"]])
        selected = arr(capture["entries"], "capture/entries")
        for i in selected:
            integer(i, "capture/entries")
            require(i < len(self.entries), "ENTRIES", "capture/entries", "Select existing HAR entries.")
        require(bool(selected) and len(set(selected)) == len(selected), "ENTRIES", "capture/entries", "Select unique, nonempty entries.")
        for key, run in self.maps["runs"].items():
            keys(run, ("kind",), "runs/" + key)
            choice(run["kind"], {"unknown", "target", "fixture"}, "runs/" + key + "/kind")
        for key, session in self.maps["sessions"].items():
            keys(session, ("run_id", "kind", "initial_state"), "sessions/" + key)
            string(session["run_id"], "sessions/" + key + "/run_id", True)
            require(session["run_id"] in self.maps["runs"], "DANGLING", key, "Reference the session's run.")
            choice(session["kind"], {"new", "existing"}, key + "/kind")
            string(session["initial_state"], key + "/initial_state")
        requests = self.maps["requests"]
        request_indices = []
        self.expected = set()
        for key, request in requests.items():
            keys(request, ("entry_index", "predecessors", "state_before", "state_after", "epoch",
                           "trigger", "realm", "session_id", "evidence_ids"), "requests/" + key)
            index = integer(request["entry_index"], key + "/entry_index")
            require(index in selected, "REQUEST_SCOPE", key, "Reference a selected HAR entry.")
            request_indices.append(index)
            references(request["predecessors"], requests, key + "/predecessors")
            for member in ("state_before", "state_after", "epoch", "trigger", "realm", "session_id"):
                string(request[member], key + "/" + member)
            if request["session_id"]:
                require(request["session_id"] in self.maps["sessions"], "DANGLING", key + "/session_id", "Reference an existing session.")
            self.evidence_refs(request["evidence_ids"], key + "/evidence_ids")
            for location, opaque in inventory(self.entries[index], index).items():
                self.expected.add((key, location))
                if opaque:
                    self.opaque.add((key, location))
        require(sorted(request_indices) == sorted(selected), "REQUEST_COVERAGE", "requests", "Represent every selected HAR entry exactly once.")
        self.request_ancestors = graph_ancestors(requests, "predecessors", "requests")
        nodes = self.maps["nodes"]
        observed = set()
        for key, node in nodes.items():
            keys(node, ("node_type", "request_id", "location", "source", "dependencies", "transformations",
                        "encoding", "storage", "consumer", "lifecycle", "binding", "implementation", "evidence_ids", "gaps"), "nodes/" + key)
            choice(node["node_type"], {"field", "internal"}, key + "/node_type")
            string(node["request_id"], key + "/request_id")
            string(node["location"], key + "/location")
            if node["node_type"] == "field":
                pair = (node["request_id"], node["location"])
                require(pair in self.expected, "FIELD_LOCATION", key, "Use an exact inventoried request location.")
                require(pair not in observed, "DUPLICATE_LOCATION", key, "Represent each request location once.")
                observed.add(pair)
            else:
                require(not node["request_id"] and not node["location"], "INTERNAL_LOCATION", key, "Internal nodes have empty request_id and location; consumers reference their IDs.")
            source = node["source"]
            keys(source, ("kind", "producer", "artifact", "anchor", "realm"), key + "/source")
            choice(source["kind"], {"UNKNOWN", "constant", "local", "server", "derived", "device"}, key + "/source/kind")
            for member in ("producer", "artifact", "anchor", "realm"):
                string(source[member], key + "/source/" + member)
            if source["artifact"]:
                require(source["artifact"] in artifacts, "DANGLING", key + "/source/artifact", "Reference a frozen source artifact.")
            if source["kind"] == "server" and source["producer"]:
                require(source["producer"] in requests, "DANGLING", key + "/source/producer", "Represent the producing request in the selected capture.")
                if source["anchor"]:
                    require(source["anchor"].startswith("/response/"), "SERVER_ANCHOR", key, "Use a /response/ JSON pointer in the producer HAR entry.")
                    producer = requests[source["producer"]]
                    at_pointer(self.entries[producer["entry_index"]], source["anchor"], key + "/source/anchor")
            elif source["artifact"] and source["anchor"] and artifacts[source["artifact"]]["kind"] == "capture":
                at_pointer(read_json(self.paths[source["artifact"]]), source["anchor"], key + "/source/anchor")
            references(node["dependencies"], nodes, key + "/dependencies")
            for member in ("encoding", "storage", "consumer"):
                string(node[member], key + "/" + member)
            for i, transformation in enumerate(arr(node["transformations"], key + "/transformations")):
                keys(transformation, ("name", "evidence_ids"), key + "/transformations")
                string(transformation["name"], key + f"/transformations/{i}/name", True)
                self.evidence_refs(transformation["evidence_ids"], key + "/transformations/evidence_ids")
            for member in ("lifecycle", "binding"):
                boundary = node[member]
                keys(boundary, ("status", "description", "evidence_ids"), key + "/" + member)
                choice(boundary["status"], {"unknown", "verified", "na"}, key + "/" + member + "/status")
                string(boundary["description"], key + "/" + member + "/description")
                self.evidence_refs(boundary["evidence_ids"], key + "/" + member + "/evidence_ids")
            implementation = node["implementation"]
            if implementation is not None:
                keys(implementation, ("artifact", "symbol"), key + "/implementation")
                string(implementation["artifact"], key + "/implementation/artifact", True)
                string(implementation["symbol"], key + "/implementation/symbol", True)
                require(implementation["artifact"] in artifacts, "DANGLING", key, "Reference the implementation artifact.")
                require(artifacts[implementation["artifact"]]["kind"] == "code", "IMPLEMENTATION_KIND", key, "Reference a code artifact.")
            self.evidence_refs(node["evidence_ids"], key + "/evidence_ids")
            for gap in arr(node["gaps"], key + "/gaps"):
                keys(gap, ("detail", "next_experiment"), key + "/gaps")
                string(gap["detail"], key + "/gaps/detail", True)
                string(gap["next_experiment"], key + "/gaps/next_experiment", True)
        missing = sorted(self.expected - observed)
        require(not missing, "FIELD_COVERAGE", "nodes" + (":" + missing[0][0] + missing[0][1] if missing else ""),
                "Restore omitted fields from the actual HAR inventory.")
        self.node_ancestors = graph_ancestors(nodes, "dependencies", "nodes")
        self.validate_evidence()
        self.validate_claims()

    def validate_evidence(self):
        artifacts, requests = self.maps["artifacts"], self.maps["requests"]
        for key, evidence in self.maps["evidence"].items():
            keys(evidence, ("kind", "artifact", "run_id", "session_id", "asset_ids", "asset_hashes", "request_ids", "details"), "evidence/" + key)
            choice(evidence["kind"], {"source", "lifecycle", "oracle", "business", "state"}, key + "/kind")
            for member, mapping in (("artifact", artifacts), ("run_id", self.maps["runs"]), ("session_id", self.maps["sessions"])):
                string(evidence[member], key + "/" + member, True)
                require(evidence[member] in mapping, "DANGLING", key + "/" + member, "Reference an existing ID.")
            require(self.maps["sessions"][evidence["session_id"]]["run_id"] == evidence["run_id"],
                    "EVIDENCE_RUN", key, "Keep evidence and session in the same run.")
            references(evidence["asset_ids"], artifacts, key + "/asset_ids")
            references(evidence["request_ids"], requests, key + "/request_ids")
            snapshots = obj(evidence["asset_hashes"], key + "/asset_hashes")
            expected = set(evidence["asset_ids"]) | {evidence["artifact"]}
            require(set(snapshots) == expected, "EVIDENCE_SNAPSHOT", key, "Freeze hashes for evidence.artifact and every asset_id.")
            for asset, value in snapshots.items():
                string(value, key + "/asset_hashes/" + asset)
                require(value == artifacts[asset]["sha256"], "STALE_EVIDENCE", key + "/asset_hashes/" + asset,
                        "Collect new evidence for the changed asset; do not refresh old evidence hashes.")
            obj(evidence["details"], key + "/details")

    def validate_claims(self):
        artifacts, nodes = self.maps["artifacts"], self.maps["nodes"]
        for key, algorithm in self.maps["algorithms"].items():
            keys(algorithm, ("fields", "conditions", "comparisons"), "algorithms/" + key)
            references(algorithm["fields"], nodes, key + "/fields")
            keys(algorithm["conditions"], ("random", "clock"), key + "/conditions")
            for member in ("random", "clock"):
                string(algorithm["conditions"][member], key + "/conditions/" + member)
            for comparison in arr(algorithm["comparisons"], key + "/comparisons"):
                keys(comparison, ("input_artifact", "oracle_artifact", "local_artifact", "non_sample", "evidence_ids"), key + "/comparisons")
                for member in ("input_artifact", "oracle_artifact", "local_artifact"):
                    string(comparison[member], key + "/comparisons/" + member, True)
                    require(comparison[member] in artifacts, "DANGLING", key + "/comparisons/" + member, "Reference frozen byte files.")
                require(type(comparison["non_sample"]) is bool, "TYPE", key + "/comparisons/non_sample", "Use a boolean assertion.")
                self.evidence_refs(comparison["evidence_ids"], key + "/comparisons/evidence_ids")
        for key, target in self.maps["business_targets"].items():
            keys(target, ("request_ids", "criteria", "evidence_ids", "session_ids"), "business_targets/" + key)
            references(target["request_ids"], self.maps["requests"], key + "/request_ids")
            references(target["session_ids"], self.maps["sessions"], key + "/session_ids")
            string(target["criteria"], key + "/criteria")
            self.evidence_refs(target["evidence_ids"], key + "/evidence_ids")

    def target_evidence(self, evidence_id, kind=None, request_id=None, assets=()):
        evidence = self.maps["evidence"][evidence_id]
        artifacts = self.maps["artifacts"]
        linked = set(evidence["asset_ids"])
        return (
            (kind is None or evidence["kind"] == kind)
            and artifacts[self.data["capture"]["artifact"]]["provenance"] == "target"
            and self.maps["runs"][evidence["run_id"]]["kind"] == "target"
            and bool(linked) and set(assets).issubset(linked)
            and all(artifacts[a]["provenance"] == "target" for a in linked | {evidence["artifact"]})
            and (request_id is None or (request_id in evidence["request_ids"] and
                 self.maps["requests"][request_id]["session_id"] == evidence["session_id"]))
        )

    @staticmethod
    def known(value):
        return bool(value.strip()) and value.strip().lower() not in {"unknown", "todo", "tbd", "未验证", "未知"}

    def node_closed(self, key):
        node = self.maps["nodes"][key]
        source = node["source"]
        request_id = node["request_id"] or None
        checks = []

        def check(ok, code, next_step):
            checks.append(ok)
            if not ok:
                self.gap(code, "nodes/" + key, next_step)

        check(source["kind"] != "UNKNOWN", "SOURCE_UNKNOWN", "Trace and evidence the actual field producer.")
        check((node["request_id"], node["location"]) not in self.opaque, "OPAQUE_BODY",
              "Analyze the unsupported body with an appropriate parser; this tool cannot close opaque internals.")
        check(not node["gaps"], "DECLARED_GAP", "Resolve each declared gap with its distinguishing experiment.")
        for index, declared in enumerate(node["gaps"]):
            self.gaps.append({"code": "DECLARED_EXPERIMENT", "at": f"nodes/{key}/gaps/{index}",
                              "detail": declared["detail"], "next": declared["next_experiment"]})
        for member in ("encoding", "storage", "consumer"):
            check(self.known(node[member]), "BOUNDARY_UNKNOWN", "Document " + member + " explicitly, including a justified none where applicable.")
        check(self.known(source["realm"]) and bool(source["artifact"]) and self.known(source["anchor"]),
              "SOURCE_ANCHOR", "Record a source artifact, code/producer anchor and execution realm.")
        assets = {source["artifact"]} if source["artifact"] else set()
        implementation = node["implementation"]
        if source["kind"] in {"local", "derived"}:
            check(implementation is not None, "IMPLEMENTATION", "Link the implementing code file and symbol.")
            check(bool(source["artifact"]) and self.maps["artifacts"][source["artifact"]]["kind"] == "code",
                  "CODE_SOURCE", "Anchor local generation to a frozen code artifact.")
        if implementation:
            assets.add(implementation["artifact"])
        check(any(self.target_evidence(e, "source", request_id, assets) for e in node["evidence_ids"]),
              "SOURCE_EVIDENCE", "Collect target source evidence linked to this request/session and its source/implementation assets.")
        if source["kind"] == "derived":
            check(bool(node["dependencies"]), "DEPENDENCIES", "List all upstream internal dependency nodes.")
        if source["kind"] == "server":
            check(bool(source["producer"]) and source["artifact"] == self.data["capture"]["artifact"] and
                  source["anchor"].startswith("/response/"), "SERVER_PRODUCER",
                  "Anchor the issued value to the captured producing response.")
            consumers = [request_id] if request_id else [n["request_id"] for n in self.maps["nodes"].values()
                         if n["request_id"] and key in self.node_ancestors[n["id"]]]
            check(bool(consumers) and all(source["producer"] in self.request_ancestors[r] for r in consumers),
                  "SERVER_ORDER", "Connect issue/store/consume through predecessor requests; refresh uses new epoch instances.")
        for member in ("lifecycle", "binding"):
            boundary = node[member]
            state = boundary["status"]
            check(state != "unknown" and self.known(boundary["description"]), "BOUNDARY_UNKNOWN",
                  "Evidence " + member + ", or explicitly justify non-applicability.")
            check(state != "na" or source["kind"] not in {"server", "device"}, "DYNAMIC_NA",
                  "Verify lifecycle and binding for server/device state; na cannot close dynamic state.")
            if state == "verified":
                check(any(self.target_evidence(e, "lifecycle", request_id, assets) for e in boundary["evidence_ids"]),
                      "LIFECYCLE_EVIDENCE", "Collect target lifecycle/binding evidence for this node and its assets.")
        for transformation in node["transformations"]:
            check(any(self.target_evidence(e, None, request_id, assets) for e in transformation["evidence_ids"]),
                  "TRANSFORM_EVIDENCE", "Evidence each transformation and encoding step.")
        return all(checks)

    def algorithm_conditions(self, closed):
        algorithms = self.maps["algorithms"]
        good = bool(algorithms)
        if not algorithms:
            self.gap("NO_ALGORITHMS", "algorithms", "Declare the specific algorithm fields before requesting algorithm conditions.")
        for key, algorithm in algorithms.items():
            fields = algorithm["fields"]
            needed = set(fields)
            for node_id in fields:
                needed.update(self.node_ancestors[node_id])
            ok = bool(fields) and all(closed[n] for n in needed)
            if not ok:
                self.gap("ALGORITHM_LINEAGE", "algorithms/" + key, "Close every claimed field and its transitive dependencies.")
            if not all(self.known(algorithm["conditions"][member]) for member in ("random", "clock")):
                ok = False
                self.gap("ORACLE_CONDITIONS", key, "State how random and clock inputs were controlled or observed.")
            implementations = {self.maps["nodes"][n]["implementation"]["artifact"] for n in needed
                               if self.maps["nodes"][n]["implementation"]}
            lineage_assets = self.node_assets(needed)
            if not implementations:
                ok = False
                self.gap("ALGORITHM_IMPLEMENTATION", key, "Link at least one implementing code artifact and symbol.")
            distinct = set()
            for i, comparison in enumerate(algorithm["comparisons"]):
                where = f"algorithms/{key}/comparisons/{i}"
                refs = {comparison[m] for m in ("input_artifact", "oracle_artifact", "local_artifact")}
                valid = comparison["non_sample"] and all(self.maps["artifacts"][a]["provenance"] == "target" for a in refs)
                valid = valid and comparison["oracle_artifact"] != comparison["local_artifact"]
                valid = valid and not self.paths[comparison["oracle_artifact"]].samefile(self.paths[comparison["local_artifact"]])
                evidence_ok = any(self.target_evidence(e, "oracle", assets=refs | lineage_assets)
                                  and self.maps["evidence"][e]["details"].get("algorithm_id") == key
                                  for e in comparison["evidence_ids"])
                valid = valid and evidence_ok
                oracle = self.paths[comparison["oracle_artifact"]].read_bytes()
                local = self.paths[comparison["local_artifact"]].read_bytes()
                if oracle != local:
                    valid = False
                    self.gap("BYTE_MISMATCH", where, "Resolve the actual oracle/local byte difference and recollect comparison evidence.")
                if not valid:
                    self.gap("ORACLE_EVIDENCE", where, "Provide non-sample target evidence binding input/oracle/local/implementation hashes in one run/session.")
                else:
                    distinct.add(self.maps["artifacts"][comparison["input_artifact"]]["sha256"])
                ok = ok and valid
            if len(distinct) < 3:
                ok = False
                self.gap("ORACLE_COUNT", key, "Collect at least three distinct non-sample input byte files with matched oracle/local outputs.")
            good = good and ok
        return good

    def state_conditions(self):
        good = bool(self.maps["requests"])
        requests, sessions = self.maps["requests"], self.maps["sessions"]
        capture_id = self.data["capture"]["artifact"]
        for key, request in requests.items():
            ok = all(self.known(request[m]) for m in ("state_before", "state_after", "epoch", "trigger", "realm", "session_id"))
            sid = request["session_id"]
            if sid:
                session = sessions[sid]
                ok = ok and self.maps["runs"][session["run_id"]]["kind"] == "target"
                predecessors = request["predecessors"]
                if predecessors:
                    ok = ok and all(requests[p]["session_id"] == sid and requests[p]["state_after"] == request["state_before"] for p in predecessors)
                else:
                    ok = ok and session["initial_state"] == request["state_before"]
            ok = ok and any(self.target_evidence(e, "state", key, {capture_id}) for e in request["evidence_ids"])
            if not ok:
                self.gap("REQUEST_STATE", "requests/" + key, "Evidence trigger, realm, epoch and same-session before/after state chain from its initial state.")
            good = good and ok
        return good

    def business_conditions(self):
        good = True
        requests, sessions = self.maps["requests"], self.maps["sessions"]
        capture_id = self.data["capture"]["artifact"]
        targets = self.maps["business_targets"]
        if not targets:
            self.gap("NO_BUSINESS_TARGET", "business_targets", "Declare explicit business acceptance criteria; HTTP status alone is not a judge.")
            good = False
        for key, target in targets.items():
            ok = bool(target["request_ids"]) and self.known(target["criteria"]) and bool(target["session_ids"])
            needed = {node_id for node_id, node in self.maps["nodes"].items()
                      if node["request_id"] in target["request_ids"]}
            for node_id in tuple(needed):
                needed.update(self.node_ancestors[node_id])
            lineage_assets = self.node_assets(needed) | {capture_id}
            covered = set()
            for evidence_id in target["evidence_ids"]:
                evidence = self.maps["evidence"][evidence_id]
                detail = evidence["details"]
                semantic = (self.target_evidence(evidence_id, "business", assets=lineage_assets)
                            and detail.get("target_id") == key and detail.get("judge") == "business-semantic"
                            and detail.get("accepted") is True and isinstance(detail.get("observation"), str)
                            and self.known(detail["observation"]))
                sid = evidence["session_id"]
                if semantic and sid in target["session_ids"] and sessions[sid]["kind"] == "new":
                    covered.update(r for r in target["request_ids"] if r in evidence["request_ids"] and requests[r]["session_id"] == sid)
            ok = ok and set(target["request_ids"]).issubset(covered)
            if not ok:
                self.gap("BUSINESS_EVIDENCE", "business_targets/" + key,
                         "Record accepted business-semantic observations for each target request in a linked new session; HTTP 200 is insufficient.")
            good = good and ok
        return good

    def check(self, requirement):
        self.validate()
        closed = {key: self.node_closed(key) for key in self.maps["nodes"]}
        # A node closes only if its entire upstream dependency graph closes.
        closed = {key: good and all(closed[d] for d in self.node_ancestors[key]) for key, good in closed.items()}
        origin = bool(closed) and all(closed.values())
        byte = self.algorithm_conditions(closed)
        state = self.state_conditions()
        business = self.business_conditions()
        generated = {key for key, node in self.maps["nodes"].items() if node["source"]["kind"] in {"local", "derived"}}
        declared = set()
        for algorithm in self.maps["algorithms"].values():
            for key in algorithm["fields"]:
                declared.add(key)
                declared.update(self.node_ancestors[key])
        uncovered = generated - declared
        for key in sorted(uncovered):
            self.gap("UNTESTED_ALGORITHM", "nodes/" + key, "Declare and byte-compare this generated field and its dependencies before protocol conditions can pass.")
        no_algorithm_needed = origin and not generated and not self.maps["algorithms"]
        if no_algorithm_needed and requirement != "algorithm":
            self.gaps = [gap for gap in self.gaps if gap["code"] != "NO_ALGORITHMS"]
        valid = requirement == "record" or (byte if requirement == "algorithm" else
                origin and state and business and not uncovered and (byte or no_algorithm_needed))
        return {"valid": bool(valid), "record_valid": True, "requirement": requirement,
                "axes": {"origin": "conditions_met" if origin else "incomplete",
                         "byte": "conditions_met" if byte else ("not_applicable" if no_algorithm_needed else "incomplete"),
                         "business": "conditions_met" if business else "incomplete",
                         "state": "conditions_met" if state else "incomplete"},
                "errors": [], "gaps": self.gaps, "machine_claim": CLAIM,
                "inventory": {"selected_requests": len(self.maps["requests"]), "request_fields": len(self.expected),
                              "opaque_fields": len(self.opaque), "internal_nodes": sum(n["node_type"] == "internal" for n in self.maps["nodes"].values())}}


def md(value):
    # Encode the original characters once; replacing '#' after constructing
    # numeric entities would corrupt those very entities (e.g. '&#95;').
    special = "&<>|`\\[]()!*_#"
    return "".join(" " if character in "\r\n" else
                   f"&#{ord(character)};" if character in special else character
                   for character in str(value))


def render_report(data, result):
    lines = ["# Lineage record report", "", "Record validity does not mean task completion.",
             "", CLAIM + ".", "", "| Axis | Declared conditions |", "| --- | --- |"]
    for axis, state in result["axes"].items():
        lines.append(f"| {md(axis)} | {md(state)} |")
    lines += ["", "Coverage: selected HAR HTTP request metadata, URL queries, headers, cookies and supported bodies.",
              "Unsupported bodies remain opaque; WebSocket/SSE/application message inventories are outside this tool.",
              "Raw captured values are not included.", "", "## Frozen artifacts", "",
              "| ID | Project-relative path | Kind / provenance | SHA-256 |", "| --- | --- | --- | --- |"]
    for artifact in data["artifacts"]:
        lines.append(f"| {md(artifact['id'])} | {md(artifact['path'])} | {md(artifact['kind'] + ' / ' + artifact['provenance'])} | {md(artifact['sha256'])} |")
    lines += ["", "## Request states", "",
              "| Request / HAR entry | Predecessors | Before | After | Epoch | Session | Evidence IDs |", "| --- | --- | --- | --- | --- | --- | --- |"]
    for request in data["requests"]:
        values = (request["id"] + " / " + str(request["entry_index"]), ", ".join(request["predecessors"]),
                  request["state_before"], request["state_after"], request["epoch"], request["session_id"],
                  ", ".join(request["evidence_ids"]))
        lines.append("| " + " | ".join(md(value) for value in values) + " |")
    lines += ["", "| Request | Trigger | Realm |", "| --- | --- | --- |"]
    for request in data["requests"]:
        lines.append(f"| {md(request['id'])} | {md(request['trigger'])} | {md(request['realm'])} |")
    lines += ["", "## Field and internal node inventory", "",
              "| Node | Request location | Source kind | Dependencies |", "| --- | --- | --- | --- |"]
    for node in data["nodes"]:
        lines.append(f"| {md(node['id'])} | {md(node['request_id'] + node['location'])} | {md(node['source']['kind'])} | {md(', '.join(node['dependencies']))} |")
    for node in data["nodes"]:
        source = node["source"]
        implementation = node["implementation"]
        lines += ["", "### " + md(node["id"]), "", "| Item | Recorded lineage |", "| --- | --- |"]
        details = [
            ("Source", "kind=" + source["kind"] + "; artifact=" + source["artifact"] + "; anchor=" + source["anchor"] +
             "; producer=" + source["producer"] + "; realm=" + source["realm"]),
            ("Implementation", implementation["artifact"] + " :: " + implementation["symbol"] if implementation else "Unrecorded / not applicable"),
            ("Encoding", node["encoding"]), ("Storage", node["storage"]), ("Consumer", node["consumer"]),
            ("Transformations", "; ".join(t["name"] + " [evidence: " + ", ".join(t["evidence_ids"]) + "]" for t in node["transformations"])),
        ]
        for member in ("lifecycle", "binding"):
            boundary = node[member]
            details.append((member, boundary["status"] + ": " + boundary["description"] + "; evidence=" + ", ".join(boundary["evidence_ids"])))
        details.append(("Source evidence", ", ".join(node["evidence_ids"])))
        for label, value in details:
            lines.append(f"| {md(label)} | {md(value)} |")
    lines += ["", "| Gap | Location | Detail | Next distinguishing action |", "| --- | --- | --- | --- |"]
    for gap in result["gaps"]:
        lines.append(f"| {md(gap['code'])} | {md(gap['at'])} | {md(gap.get('detail', ''))} | {md(gap['next'])} |")
    return "\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init", help="Create UNKNOWN records from an explicitly supplied local HAR.")
    init.add_argument("--har", required=True)
    init.add_argument("--output", required=True)
    init.add_argument("--project-root", default=".")
    init.add_argument("--entries")
    check = sub.add_parser("check", help="Verify frozen artifacts, inventory, graph and declared evidence.")
    check.add_argument("--lineage", required=True)
    check.add_argument("--project-root", default=".")
    check.add_argument("--require", choices=("record", "algorithm", "protocol"), default="record")
    check.add_argument("--report")
    args = parser.parse_args(argv)
    try:
        root = root_path(args.project_root)
        if args.command == "init":
            result = initialize(root, args.har, args.output, args.entries)
        else:
            lineage_path = safe_path(root, args.lineage, "lineage", existing=True)
            data = read_json(lineage_path)
            checker = Checker(root, data)
            result = checker.check(args.require)
            if args.report:
                report_path = safe_path(root, args.report, "report")
                write_new(report_path, render_report(data, result))
        print(json.dumps(result, ensure_ascii=False))
        return 0 if result["valid"] else 1
    except Invalid as error:
        print(json.dumps({"valid": False, "record_valid": False, "errors": [error.issue], "gaps": [], "machine_claim": CLAIM}, ensure_ascii=False))
        return 1
    except (OSError, RecursionError) as error:
        code = "DEPTH_LIMIT" if isinstance(error, RecursionError) else "FILE_IO"
        print(json.dumps({"valid": False, "record_valid": False, "errors": [{"code": code, "at": "local files", "next": "Check file access, path constraints and JSON/graph depth."}], "gaps": [], "machine_claim": CLAIM}))
        return 1


if __name__ == "__main__":
    sys.exit(main())
