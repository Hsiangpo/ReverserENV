#!/usr/bin/env python3
"""Offline semantic counterexamples for the lineage CLI.

Every artifact is temporary synthetic test data. Even controls carrying
``provenance=target`` test the parser's treatment of analyst assertions only;
they are not observations of a real browser, oracle, device, or server.
"""

from __future__ import annotations

import copy
import hashlib
import html
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
CHECKER = Path(__file__).with_name("check_lineage.py")
SECRET = "DO_NOT_PRINT_live_credential_7cd154"


class LineageCLITests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="lineage-offline-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.capture = self.root / "capture.har"
        self.lineage = self.root / "lineage.json"
        self.har = {
            "log": {
                "version": "1.2",
                "entries": [{
                    "request": {
                        "method": "POST",
                        "url": "https://mock.invalid/api?a=" + SECRET + "&a=two",
                        "queryString": [
                            {"name": "a", "value": SECRET},
                            {"name": "a", "value": "two"},
                        ],
                        "headers": [
                            {"name": "Authorization", "value": "Bearer " + SECRET},
                            {"name": "X-Tag", "value": "one"},
                            {"name": "X-Tag", "value": "two"},
                            {"name": "Cookie", "value": "session=" + SECRET},
                        ],
                        "cookies": [
                            {"name": "session", "value": SECRET},
                            {"name": "session", "value": "second"},
                        ],
                        "postData": {
                            "mimeType": "application/json",
                            "text": json.dumps({
                                "secret": SECRET,
                                "nested": {"nil": None, "list": [], "object": {}},
                                "items": [0, None, {}],
                                "a/b~c": "value",
                            }),
                        },
                    },
                    "response": {"status": 200, "content": {
                        "mimeType": "application/json", "text": '{"accepted":false}'
                    }},
                }],
            },
        }
        self.write_json(self.capture, self.har)

    def write_json(self, path, data):
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def run_cli(self, *arguments):
        result = subprocess.run(
            [sys.executable, "-B", str(CHECKER), *map(str, arguments),
             "--project-root", str(self.root)],
            cwd=self.root, capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=30,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONIOENCODING": "utf-8",
                 "PYTHONINTMAXSTRDIGITS": "4300"},
        )
        self.assertNotIn("Traceback (most recent call last)", result.stdout + result.stderr)
        return result

    def init_record(self, har=None, entries=None):
        if har is not None:
            self.write_json(self.capture, har)
        arguments = ["init", "--har", "capture.har", "--output", "lineage.json"]
        if entries is not None:
            arguments.extend(["--entries", entries])
        result = self.run_cli(*arguments)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return json.loads(self.lineage.read_text(encoding="utf-8"))

    def check(self, record, requirement="record", **options):
        self.write_json(self.lineage, record)
        arguments = ["check", "--lineage", "lineage.json", "--require", requirement]
        for key, value in options.items():
            arguments.extend(["--" + key.replace("_", "-"), str(value)])
        result = self.run_cli(*arguments)
        try:
            summary = json.loads(result.stdout)
        except ValueError as error:
            self.fail(f"check must produce one JSON diagnostic: {error}: {result.stdout}{result.stderr}")
        return result, summary

    def assert_rejected(self, record, requirement="record"):
        result, summary = self.check(record, requirement)
        self.assertNotEqual(result.returncode, 0, summary)
        self.assertFalse(summary["valid"], summary)
        self.assertTrue(summary.get("errors") or summary.get("gaps"), summary)
        return summary

    def artifact(self, record, name, data=b"synthetic evidence\n", kind="evidence", provenance="target"):
        path = self.root / name
        path.write_bytes(data)
        identifier = "artifact-" + name.replace(".", "-")
        record["artifacts"].append({
            "id": identifier, "path": name,
            "sha256": hashlib.sha256(data).hexdigest(),
            "kind": kind, "provenance": provenance,
        })
        return identifier

    def bind_current_assets(self, record):
        """Model a new analyst assertion; never silently used in drift tests."""
        hashes = {item["id"]: item["sha256"] for item in record["artifacts"]}
        for evidence in record["evidence"]:
            evidence["asset_hashes"] = {
                identifier: hashes[identifier]
                for identifier in [evidence["artifact"], *evidence["asset_ids"]]
            }

    def asserted_target_control(self):
        """A mock record, never an actual target verification or live evidence."""
        record = self.init_record()
        record["artifacts"][0]["provenance"] = "target"
        code = self.artifact(
            record, "mock.py", b"# SYNTHETIC PARSER CONTROL ONLY\ndef identity(x): return x\n", "code"
        )
        record["runs"] = [{"id": "mock-run", "kind": "target"}]
        record["sessions"] = [{
            "id": "mock-session", "run_id": "mock-run", "kind": "new",
            "initial_state": "SYNTHETIC parser input; no real session was observed",
        }]

        def evidence(identifier, kind, details=None):
            artifact = self.artifact(record, identifier + ".json", json.dumps({
                "synthetic_parser_control": True, "details": details or {}
            }).encode("utf-8"))
            item = {
                "id": identifier, "kind": kind, "artifact": artifact,
                "run_id": "mock-run", "session_id": "mock-session",
                "asset_ids": [code, record["capture"]["artifact"]],
                "request_ids": ["r0"], "details": details or {},
            }
            record["evidence"].append(item)
            return identifier

        source = evidence("mock-source", "source")
        life = evidence("mock-lifecycle", "lifecycle")
        state = evidence("mock-state", "state")
        oracle = evidence("mock-oracle", "oracle", {
            "algorithm_id": "mock-algorithm", "claimed_result": "pass"
        })
        business = evidence("mock-business", "business", {
            "target_id": "mock-business-target", "judge": "business-semantic",
            "accepted": True, "observation": "SYNTHETIC accepted marker; parser assertion only",
        })
        record["requests"][0].update(
            state_before=record["sessions"][0]["initial_state"], state_after="synthetic after", epoch="synthetic epoch",
            trigger="synthetic CLI test", realm="synthetic realm", session_id="mock-session",
            evidence_ids=[state],
        )
        for node in record["nodes"]:
            node.update(
                source={"kind": "constant", "producer": "", "artifact": code,
                        "anchor": "mock.py:1", "realm": "synthetic realm"},
                transformations=[], encoding="UTF-8", storage="synthetic request", consumer="r0",
                lifecycle={"status": "verified", "description": "synthetic lifetime assertion", "evidence_ids": [life]},
                binding={"status": "verified", "description": "synthetic binding assertion", "evidence_ids": [life]},
                evidence_ids=[source], gaps=[],
            )
        generated = record["nodes"][-1]
        generated["source"]["kind"] = "local"
        generated["implementation"] = {"artifact": code, "symbol": "identity"}
        comparisons = []
        for number in range(3):
            input_id = self.artifact(record, f"input-{number}.bin", f"synthetic-input-{number}".encode())
            output = f"synthetic-output-{number}".encode()
            oracle_id = self.artifact(record, f"oracle-{number}.bin", output)
            local_id = self.artifact(record, f"local-{number}.bin", output)
            comparisons.append({
                "input_artifact": input_id, "oracle_artifact": oracle_id,
                "local_artifact": local_id, "non_sample": True, "evidence_ids": [oracle],
            })
            oracle_evidence = next(item for item in record["evidence"] if item["id"] == oracle)
            oracle_evidence["asset_ids"].extend([input_id, oracle_id, local_id])
        record["algorithms"] = [{
            "id": "mock-algorithm", "fields": [generated["id"]],
            "conditions": {"random": "no randomness in synthetic parser control", "clock": "no time input"},
            "comparisons": comparisons,
        }]
        record["business_targets"] = [{
            "id": "mock-business-target", "request_ids": ["r0"],
            "criteria": "SYNTHETIC accepted marker, not a real service criterion",
            "evidence_ids": [business], "session_ids": ["mock-session"],
        }]
        self.bind_current_assets(record)
        result, summary = self.check(record, "protocol")
        self.assertEqual(result.returncode, 0, f"synthetic parser control must pass before mutation: {summary}")
        return record

    def restate_synthetic_capture(self, baseline, har, suffix):
        """Fill a changed CLI inventory with complete mock assertions, even for opaque fields."""
        self.write_json(self.capture, har)
        output = f"inventory-{suffix}.json"
        result = self.run_cli("init", "--har", "capture.har", "--output", output)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        inventory = json.loads((self.root / output).read_text(encoding="utf-8"))
        record = copy.deepcopy(baseline)
        template = record["nodes"][0]
        record["nodes"] = []
        for observed in inventory["nodes"]:
            node = copy.deepcopy(template)
            for member in ("id", "node_type", "request_id", "location"):
                node[member] = observed[member]
            node["source"]["kind"] = "constant"
            node["implementation"] = None
            record["nodes"].append(node)
        record["algorithms"] = []
        capture = next(item for item in record["artifacts"] if item["id"] == record["capture"]["artifact"])
        capture["sha256"] = hashlib.sha256(self.capture.read_bytes()).hexdigest()
        self.bind_current_assets(record)
        return record

    def test_har_inventory_preserves_multiplicity_null_and_empty_containers(self):
        record = self.init_record()
        locations = [node["location"] for node in record["nodes"] if node["node_type"] == "field"]
        expected = {
            "/method", "/url/scheme", "/url/host", "/url/path",
            "/url/query/0", "/url/query/1",
            "/queryString/0/value", "/queryString/1/value",
            "/headers/0/value", "/headers/1/value", "/headers/2/value", "/headers/3/value",
            "/headers/3/cookies/0/value", "/postData/mimeType",
            "/cookies/0/value", "/cookies/1/value",
            "/postData/text/json/secret", "/postData/text/json/nested/nil",
            "/postData/text/json/nested/list", "/postData/text/json/nested/object",
            "/postData/text/json/items/0", "/postData/text/json/items/1",
            "/postData/text/json/items/2", "/postData/text/json/a~1b~0c",
        }
        self.assertEqual(set(locations), expected)
        self.assertEqual(len(locations), len(expected), "duplicate inventory nodes must not hide omissions")

    def test_unknown_starter_is_record_valid_but_cannot_complete(self):
        record = self.init_record()
        result, summary = self.check(record)
        self.assertEqual(result.returncode, 0, summary)
        self.assertTrue(summary["record_valid"])
        self.assertTrue(summary["gaps"])
        for requirement in ("algorithm", "protocol"):
            with self.subTest(requirement=requirement):
                self.assert_rejected(record, requirement)

    def test_selected_capture_entries_have_exact_request_inventory(self):
        self.har["log"]["entries"] = [copy.deepcopy(self.har["log"]["entries"][0]) for _ in range(3)]
        record = self.init_record(self.har, entries="0,2")
        self.assertEqual(record["capture"]["entries"], [0, 2])
        self.assertEqual({request["entry_index"] for request in record["requests"]}, {0, 2})
        self.assertEqual({node["request_id"] for node in record["nodes"]}, {"r0", "r2"})
        result, summary = self.check(record)
        self.assertEqual(result.returncode, 0, summary)

    def test_synthetic_target_assertions_are_only_a_parser_control(self):
        record = self.asserted_target_control()
        for requirement in ("algorithm", "protocol"):
            with self.subTest(requirement=requirement):
                result, summary = self.check(record, requirement)
                self.assertEqual(result.returncode, 0, summary)
                self.assertIn("authenticity", summary["machine_claim"])
                self.assertIn("unverified", summary["machine_claim"])
                self.assertIsNot(summary.get("target_verified"), True)

    def test_fixture_bytes_do_not_become_target_verification(self):
        record = self.asserted_target_control()
        for artifact in record["artifacts"]:
            artifact["provenance"] = "fixture"
        record["runs"][0]["kind"] = "fixture"
        result, summary = self.check(record)
        self.assertEqual(result.returncode, 0, summary)
        self.assert_rejected(record, "algorithm")
        self.assert_rejected(record, "protocol")

    def test_fixture_oracle_is_rejected_even_when_other_evidence_is_target(self):
        record = self.asserted_target_control()
        oracle_id = record["algorithms"][0]["comparisons"][0]["oracle_artifact"]
        artifact = next(a for a in record["artifacts"] if a["id"] == oracle_id)
        artifact["provenance"] = "fixture"
        self.assert_rejected(record, "algorithm")

    def test_algorithm_requires_three_independent_non_sample_inputs(self):
        baseline = self.asserted_target_control()
        variants = {}
        for count in (1, 2):
            record = copy.deepcopy(baseline)
            record["algorithms"][0]["comparisons"] = record["algorithms"][0]["comparisons"][:count]
            variants[f"only-{count}-inputs"] = record
        record = copy.deepcopy(baseline)
        comparisons = record["algorithms"][0]["comparisons"]
        for item in comparisons:
            item["input_artifact"] = comparisons[0]["input_artifact"]
        variants["repeated-same-input"] = record
        record = copy.deepcopy(baseline)
        for item in record["algorithms"][0]["comparisons"]:
            item["non_sample"] = False
        variants["sample-inputs-only"] = record
        for name, record in variants.items():
            with self.subTest(variant=name):
                self.assert_rejected(record, "algorithm")

    def test_same_input_bytes_under_three_artifact_ids_are_not_independent(self):
        record = self.asserted_target_control()
        input_ids = {item["input_artifact"] for item in record["algorithms"][0]["comparisons"]}
        for artifact in record["artifacts"]:
            if artifact["id"] in input_ids:
                data = b"same synthetic input under different ids"
                (self.root / artifact["path"]).write_bytes(data)
                artifact["sha256"] = hashlib.sha256(data).hexdigest()
        self.bind_current_assets(record)
        self.assert_rejected(record, "algorithm")

    def test_claimed_pass_does_not_hide_actual_byte_mismatch(self):
        record = self.asserted_target_control()
        comparison = record["algorithms"][0]["comparisons"][2]
        artifact = next(a for a in record["artifacts"] if a["id"] == comparison["local_artifact"])
        data = b"different output despite claimed pass"
        (self.root / artifact["path"]).write_bytes(data)
        artifact["sha256"] = hashlib.sha256(data).hexdigest()
        self.bind_current_assets(record)
        summary = self.assert_rejected(record, "algorithm")
        self.assertRegex(json.dumps(summary.get("errors", []) + summary.get("gaps", [])).lower(), r"mismatch|differ|not.*equal|not.*match")

    def test_changed_asset_invalidates_prior_evidence_even_after_manifest_refresh(self):
        record = self.asserted_target_control()
        artifact = next(item for item in record["artifacts"] if item["kind"] == "code")
        data = b"# different synthetic code revision\ndef identity(x): return b'new'\n"
        (self.root / artifact["path"]).write_bytes(data)
        artifact["sha256"] = hashlib.sha256(data).hexdigest()
        # Deliberately keep evidence.asset_hashes from the previous observation.
        summary = self.assert_rejected(record, "algorithm")
        self.assertRegex(json.dumps(summary).lower(), r"hash|asset|stale")

    def test_oracle_binds_source_sdk_separately_from_local_implementation(self):
        record = self.asserted_target_control()
        result, summary = self.check(record, "protocol")
        self.assertEqual(result.returncode, 0, summary)
        sdk = self.artifact(record, "mock-sdk.js", b"// SYNTHETIC SOURCE ASSET\n", "code")
        field = next(node for node in record["nodes"] if node["id"] == record["algorithms"][0]["fields"][0])
        field["source"].update(artifact=sdk, anchor="mock-sdk.js:1")
        for evidence in record["evidence"]:
            if evidence["kind"] in {"source", "lifecycle", "business"}:
                evidence["asset_ids"].append(sdk)
        self.bind_current_assets(record)
        rejected = self.assert_rejected(record, "algorithm")
        self.assertTrue(any(item["code"] == "ORACLE_EVIDENCE" for item in rejected["gaps"]), rejected)
        for evidence in record["evidence"]:
            if evidence["kind"] == "oracle":
                evidence["asset_ids"].append(sdk)
        self.bind_current_assets(record)
        result, summary = self.check(record, "algorithm")
        self.assertEqual(result.returncode, 0, summary)

    def test_report_retains_specific_gap_and_reviewable_lineage(self):
        record = self.asserted_target_control()
        record["nodes"][0]["gaps"] = [{
            "detail": "Issuer for this key remains unknown",
            "next_experiment": "Trace the key writer before initialization",
        }]
        result, summary = self.check(record, report="review.md")
        self.assertEqual(result.returncode, 0, summary)
        report = (self.root / "review.md").read_text(encoding="utf-8")
        self.assertIn("Issuer for this key remains unknown", report)
        self.assertIn("Trace the key writer before initialization", report)
        self.assertIn("mock.py:1", report)
        self.assertIn("synthetic lifetime assertion", report)
        self.assertIn("synthetic binding assertion", report)
        self.assertIn(record["requests"][0]["state_before"], report)
        self.assertNotIn(SECRET, report)

    def test_report_escapes_markdown_once_and_preserves_text(self):
        record = self.init_record()
        detail = "Check key_id #1 <unsafe> & [label](x) `call` *once*"
        record["nodes"][0]["gaps"] = [{"detail": detail, "next_experiment": "Trace the producer"}]
        result, summary = self.check(record, report="escaped.md")
        self.assertEqual(result.returncode, 0, summary)
        report = (self.root / "escaped.md").read_text(encoding="utf-8")
        self.assertNotIn("<unsafe>", report)
        self.assertNotIn("[label](x)", report)
        self.assertIn(detail, html.unescape(report))

    def test_http_200_without_semantic_judge_cannot_pass_protocol(self):
        record = self.asserted_target_control()
        evidence = next(item for item in record["evidence"] if item["kind"] == "business")
        evidence["details"] = {
            "target_id": "mock-business-target", "judge": "http-status",
            "accepted": True, "status": 200, "observation": "HTTP 200 only",
        }
        self.assert_rejected(record, "protocol")

    def test_semantic_rejection_or_absent_observation_cannot_pass_protocol(self):
        baseline = self.asserted_target_control()
        for key, value in (("accepted", False), ("observation", "")):
            with self.subTest(field=key):
                record = copy.deepcopy(baseline)
                evidence = next(item for item in record["evidence"] if item["kind"] == "business")
                evidence["details"][key] = value
                self.assert_rejected(record, "protocol")

    def test_existing_or_undocumented_session_cannot_pass_protocol(self):
        baseline = self.asserted_target_control()
        for mutation in ("existing", "missing-initial-state", "missing-session"):
            with self.subTest(mutation=mutation):
                record = copy.deepcopy(baseline)
                if mutation == "existing":
                    record["sessions"][0]["kind"] = "existing"
                elif mutation == "missing-initial-state":
                    record["sessions"][0]["initial_state"] = ""
                else:
                    record["business_targets"][0]["session_ids"] = []
                self.assert_rejected(record, "protocol")

    def test_missing_claimed_boundaries_or_protocol_state_prevents_required_closure(self):
        baseline = self.asserted_target_control()
        for missing in ("lifecycle", "binding", "state_before", "epoch", "realm"):
            with self.subTest(missing=missing):
                record = copy.deepcopy(baseline)
                if missing in ("lifecycle", "binding"):
                    record["nodes"][-1][missing]["status"] = "unknown"
                else:
                    record["requests"][0][missing] = ""
                self.assert_rejected(record, "algorithm" if missing in ("lifecycle", "binding") else "protocol")

    def test_algorithm_scope_does_not_claim_unrelated_origin_is_complete(self):
        record = self.asserted_target_control()
        record["nodes"][0]["lifecycle"]["status"] = "unknown"
        result, summary = self.check(record, "algorithm")
        self.assertEqual(result.returncode, 0, summary)
        self.assertEqual(summary["axes"]["origin"], "incomplete")
        self.assertEqual(summary["axes"]["business"], "conditions_met")
        self.assert_rejected(record, "protocol")

    def test_protocol_without_local_algorithm_has_byte_axis_not_applicable(self):
        record = self.asserted_target_control()
        record["nodes"][-1]["source"]["kind"] = "constant"
        record["nodes"][-1]["implementation"] = None
        record["algorithms"] = []
        result, summary = self.check(record, "protocol")
        self.assertEqual(result.returncode, 0, summary)
        self.assertEqual(summary["axes"]["byte"], "not_applicable")
        self.assert_rejected(record, "algorithm")

    def test_uncovered_local_generation_blocks_protocol_only(self):
        record = self.asserted_target_control()
        record["nodes"][0]["source"]["kind"] = "local"
        record["nodes"][0]["implementation"] = copy.deepcopy(record["nodes"][-1]["implementation"])
        result, summary = self.check(record, "algorithm")
        self.assertEqual(result.returncode, 0, summary)
        self.assert_rejected(record, "protocol")

    def test_unknown_internal_key_prevents_closure_of_known_transport_fields(self):
        record = self.asserted_target_control()
        generated = record["nodes"][-1]
        internal = copy.deepcopy(generated)
        internal.update(
            id="unknown-internal-key", node_type="internal", request_id="", location="",
            source={"kind": "UNKNOWN", "producer": "", "artifact": "", "anchor": "", "realm": ""},
            dependencies=[], implementation=None, evidence_ids=[],
            gaps=[{"detail": "Synthetic key origin is deliberately unknown", "next_experiment": "Trace mock key producer"}],
        )
        generated["dependencies"] = [internal["id"]]
        record["nodes"].append(internal)
        result, summary = self.check(record)
        self.assertEqual(result.returncode, 0, summary)
        self.assert_rejected(record, "algorithm")

    def test_omitted_observed_field_cannot_be_hidden_by_other_statuses(self):
        record = self.asserted_target_control()
        record["nodes"].pop(0)  # All remaining fields retain their complete assertions.
        summary = self.assert_rejected(record)
        self.assertFalse(summary["record_valid"])
        self.assertRegex(json.dumps(summary["errors"]).lower(), r"inventory|coverage|missing.*field|omitt")

    def test_duplicate_and_dangling_node_references_rejected(self):
        baseline = self.init_record()
        mutations = {
            "duplicate-id": lambda r: r["nodes"].append(copy.deepcopy(r["nodes"][0])),
            "dangling-dependency": lambda r: r["nodes"][0]["dependencies"].append("absent-node"),
            "dangling-request": lambda r: r["nodes"][0].update(request_id="absent-request"),
            "dangling-evidence": lambda r: r["nodes"][0]["evidence_ids"].append("absent-evidence"),
            "dangling-artifact": lambda r: r["nodes"][0]["source"].update(artifact="absent-artifact"),
        }
        for name, mutation in mutations.items():
            with self.subTest(mutation=name):
                record = copy.deepcopy(baseline)
                mutation(record)
                self.assert_rejected(record)

    def test_duplicate_entity_ids_and_dangling_cross_references_rejected(self):
        baseline = self.asserted_target_control()
        for key in ("artifacts", "runs", "sessions", "requests", "evidence", "algorithms", "business_targets"):
            with self.subTest(duplicate_entity=key):
                record = copy.deepcopy(baseline)
                record[key].append(copy.deepcopy(record[key][0]))
                self.assert_rejected(record)
        mutations = {
            "evidence-run": lambda r: r["evidence"][0].update(run_id="absent-run"),
            "evidence-session": lambda r: r["evidence"][0].update(session_id="absent-session"),
            "evidence-asset": lambda r: r["evidence"][0]["asset_ids"].append("absent-asset"),
            "algorithm-field": lambda r: r["algorithms"][0]["fields"].append("absent-node"),
            "business-request": lambda r: r["business_targets"][0]["request_ids"].append("absent-request"),
        }
        for name, mutation in mutations.items():
            with self.subTest(reference=name):
                record = copy.deepcopy(baseline)
                mutation(record)
                self.assert_rejected(record)

    def test_dependency_and_request_cycles_rejected(self):
        baseline = self.init_record()
        record = copy.deepcopy(baseline)
        first, second = record["nodes"][:2]
        first["dependencies"] = [second["id"]]
        second["dependencies"] = [first["id"]]
        self.assert_rejected(record)
        record = copy.deepcopy(baseline)
        record["requests"][0]["predecessors"] = [record["requests"][0]["id"]]
        self.assert_rejected(record)

    def test_missing_changed_and_escaping_artifacts_rejected(self):
        baseline = self.init_record()
        baseline["artifacts"][0]["path"] = "missing.har"
        self.assert_rejected(baseline)
        baseline["artifacts"][0]["path"] = "capture.har"
        self.capture.write_bytes(self.capture.read_bytes() + b"\n")
        self.assert_rejected(baseline)
        with tempfile.TemporaryDirectory(prefix="lineage-outside-") as outside:
            escaped = Path(outside) / "evidence.txt"
            escaped.write_text("outside", encoding="utf-8")
            baseline["artifacts"][0].update(
                path=os.path.relpath(escaped, self.root),
                sha256=hashlib.sha256(escaped.read_bytes()).hexdigest(),
            )
            self.assert_rejected(baseline)

    def test_symlink_or_windows_junction_evidence_rejected(self):
        record = self.init_record()
        target = self.root / "plain.txt"
        target.write_bytes(b"evidence")
        linked = self.root / "linked.txt"
        try:
            linked.symlink_to(target)
        except (OSError, NotImplementedError) as error:
            if sys.platform != "win32":
                self.skipTest(f"host cannot create symlink: {type(error).__name__}")
            target_dir = self.root / "junction-target"
            target_dir.mkdir()
            (target_dir / "evidence.txt").write_bytes(b"evidence")
            junction = self.root / "junction-link"
            powershell = Path(os.environ["SystemRoot"]) / "System32/WindowsPowerShell/v1.0/powershell.exe"
            result = subprocess.run(
                [str(powershell), "-NoProfile", "-NonInteractive", "-Command",
                 "$ErrorActionPreference='Stop'; New-Item -ItemType Junction -Path $env:LINEAGE_TEST_LINK -Target $env:LINEAGE_TEST_TARGET | Out-Null"],
                env={**os.environ, "LINEAGE_TEST_LINK": str(junction), "LINEAGE_TEST_TARGET": str(target_dir)},
                capture_output=True, text=True, timeout=20, creationflags=subprocess.CREATE_NO_WINDOW,
            )
            self.assertEqual(result.returncode, 0, "Windows junction fixture creation failed")
            linked = junction / "evidence.txt"
            print("[path fixture] Windows junction exercised; file symlink permission unavailable")
        record["artifacts"].append({
            "id": "linked-evidence", "path": str(linked.relative_to(self.root)),
            "sha256": hashlib.sha256(b"evidence").hexdigest(),
            "provenance": "target", "kind": "evidence",
        })
        self.assert_rejected(record)

    def test_opaque_body_remains_an_explicit_gap(self):
        record = self.asserted_target_control()
        self.har["log"]["entries"][0]["request"]["postData"] = {
            "mimeType": "application/octet-stream", "text": "opaque-encrypted-payload",
        }
        self.write_json(self.capture, self.har)
        capture = next(item for item in record["artifacts"] if item["id"] == record["capture"]["artifact"])
        capture["sha256"] = hashlib.sha256(self.capture.read_bytes()).hexdigest()
        generated = record["nodes"][-1]
        record["nodes"] = [node for node in record["nodes"] if not node["location"].startswith("/postData/text/json")]
        generated["location"] = "/postData/text/opaque"
        record["nodes"].append(generated)
        self.bind_current_assets(record)
        result, summary = self.check(record)
        self.assertEqual(result.returncode, 0, summary)
        self.assertTrue(summary["record_valid"])
        summary = self.assert_rejected(record, "algorithm")
        self.assertIn("opaque", json.dumps(summary).lower())

    def test_uncaptured_nonempty_body_is_an_opaque_inventory_field(self):
        request = self.har["log"]["entries"][0]["request"]
        del request["postData"]
        request["bodySize"] = 128
        record = self.init_record(self.har)
        locations = {node["location"] for node in record["nodes"]}
        self.assertIn("/postData/missing/opaque", locations)

    def test_empty_postdata_cannot_hide_advertised_nonempty_body(self):
        baseline = self.asserted_target_control()
        cases = (
            ("size-text", 128, None, {"mimeType": "application/x-www-form-urlencoded", "text": "", "params": []}),
            ("length-text", 0, "128", {"mimeType": "application/x-www-form-urlencoded", "text": "", "params": []}),
            ("size-empty-object", 128, None, {}),
            ("size-empty-params", 128, None, {"params": []}),
        )
        for name, size, length, post in cases:
            with self.subTest(case=name):
                har = copy.deepcopy(self.har)
                request = har["log"]["entries"][0]["request"]
                request.update(bodySize=size, postData=post)
                if length is not None:
                    request["headers"].append({"name": "Content-Length", "value": length})
                record = self.restate_synthetic_capture(baseline, har, name)
                self.assertTrue(any(node["location"].endswith("/opaque") for node in record["nodes"]))
                summary = self.assert_rejected(record, "protocol")
                self.assertTrue(summary["record_valid"])
                self.assertIn("OPAQUE_BODY", {gap["code"] for gap in summary["gaps"]})
                self.assertEqual(summary["axes"]["state"], "conditions_met")
                self.assertEqual(summary["axes"]["business"], "conditions_met")

    def test_empty_and_params_represented_bodies_are_not_falsely_opaque(self):
        baseline = self.asserted_target_control()
        empty_form = {"mimeType": "application/x-www-form-urlencoded", "text": "", "params": []}
        cases = (
            ("zero-absent", 0, None, None),
            ("zero-form", 0, None, empty_form),
            ("zero-chunked-form", 0, {"name": "Transfer-Encoding", "value": "chunked"}, empty_form),
            ("zero-chunked-absent", 0, {"name": "Transfer-Encoding", "value": "chunked"}, None),
            ("params-body", 128, {"name": "Content-Length", "value": "128"}, {
                "mimeType": "application/x-www-form-urlencoded", "text": "", "params": [{"name": "a", "value": "x"}],
            }),
        )
        for name, size, header, post in cases:
            with self.subTest(case=name):
                har = copy.deepcopy(self.har)
                request = har["log"]["entries"][0]["request"]
                request["bodySize"] = size
                if post is None:
                    request.pop("postData")
                else:
                    request["postData"] = post
                if header is not None:
                    request["headers"].append(header)
                record = self.restate_synthetic_capture(baseline, har, name)
                result, summary = self.check(record, "protocol")
                self.assertEqual(result.returncode, 0, summary)
                self.assertEqual(summary["inventory"]["opaque_fields"], 0)
                if name == "params-body":
                    self.assertIn("/postData/params/0/value", {node["location"] for node in record["nodes"]})

    def test_chunked_body_with_unknown_size_and_no_capture_stays_opaque(self):
        baseline = self.asserted_target_control()
        for name, size in (("chunked-size-omitted", None), ("chunked-size-unknown", -1)):
            with self.subTest(case=name):
                har = copy.deepcopy(self.har)
                request = har["log"]["entries"][0]["request"]
                request.pop("postData")
                if size is not None:
                    request["bodySize"] = size
                request["headers"].append({"name": "Transfer-Encoding", "value": "chunked"})
                record = self.restate_synthetic_capture(baseline, har, name)
                self.assertIn("/postData/missing/opaque", {node["location"] for node in record["nodes"]})
                summary = self.assert_rejected(record, "protocol")
                self.assertIn("OPAQUE_BODY", {gap["code"] for gap in summary["gaps"]})

    def test_json_body_oversized_integer_is_opaque_without_traceback(self):
        if not hasattr(sys, "get_int_max_str_digits"):
            self.skipTest("Python runtime does not expose the configurable integer conversion limit")
        request = self.har["log"]["entries"][0]["request"]
        request["postData"] = {"mimeType": "application/json", "text": '{"n":' + "9" * 5000 + "}"}
        record = self.init_record(self.har)
        self.assertIn("/postData/text/opaque", {node["location"] for node in record["nodes"]})
        result, summary = self.check(record)
        self.assertEqual(result.returncode, 0, summary)
        self.assertEqual(summary["inventory"]["opaque_fields"], 1)

    def test_json_body_lone_surrogate_key_is_rejected_without_creating_output(self):
        for escaped in (r"\ud800", r"\udc00"):
            with self.subTest(key=escaped):
                self.har["log"]["entries"][0]["request"]["postData"] = {
                    "mimeType": "application/json", "text": '{"' + escaped + '":1}',
                }
                self.write_json(self.capture, self.har)
                result = self.run_cli("init", "--har", "capture.har", "--output", "lineage.json")
                self.assertNotEqual(result.returncode, 0)
                summary = json.loads(result.stdout)
                self.assertIn("JSON_UNICODE", {error["code"] for error in summary["errors"]})
                self.assertFalse(self.lineage.exists(), "Rejected Unicode must not leave an empty output artifact")

    def test_json_body_valid_emoji_surrogate_pair_remains_a_normal_field(self):
        self.har["log"]["entries"][0]["request"]["postData"] = {
            "mimeType": "application/json", "text": r'{"\ud83d\ude00":1}',
        }
        record = self.init_record(self.har)
        self.assertIn("/postData/text/json/\U0001f600", {node["location"] for node in record["nodes"]})
        result, summary = self.check(record)
        self.assertEqual(result.returncode, 0, summary)
        self.assertEqual(summary["inventory"]["opaque_fields"], 0)

    def test_report_lone_surrogate_text_does_not_create_empty_output(self):
        record = self.init_record()
        record["nodes"][0]["gaps"][0]["detail"] = "Synthetic analyst text with unpaired surrogate: \ud800"
        self.lineage.write_text(json.dumps(record, ensure_ascii=True), encoding="utf-8")
        result = self.run_cli("check", "--lineage", "lineage.json", "--report", "surrogate-report.md")
        self.assertNotEqual(result.returncode, 0)
        summary = json.loads(result.stdout)
        self.assertIn("JSON_UNICODE", {error["code"] for error in summary["errors"]})
        self.assertFalse((self.root / "surrogate-report.md").exists())

    def test_capture_anchor_rejects_negative_json_pointer_array_index(self):
        record = self.asserted_target_control()
        source = record["nodes"][0]["source"]
        source["artifact"] = record["capture"]["artifact"]
        source["anchor"] = "/log/entries/0/request/headers/0/value"
        result, summary = self.check(record, "protocol")
        self.assertEqual(result.returncode, 0, summary)
        source["anchor"] = "/log/entries/0/request/headers/-1/value"
        summary = self.assert_rejected(record)
        self.assertRegex(json.dumps(summary["errors"]).lower(), r"anchor|pointer|index")

    def test_init_and_report_do_not_overwrite_or_leak_capture_values(self):
        record = self.init_record()
        original = self.lineage.read_bytes()
        self.assertNotIn(SECRET, original.decode("utf-8"))
        result = self.run_cli("init", "--har", "capture.har", "--output", "lineage.json")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.lineage.read_bytes(), original)
        result, summary = self.check(record, report="report.md")
        self.assertEqual(result.returncode, 0, summary)
        report = self.root / "report.md"
        text = report.read_text(encoding="utf-8")
        self.assertNotIn(SECRET, result.stdout + result.stderr + text)
        report.write_text("preserve existing report", encoding="utf-8")
        result, _ = self.check(record, report="report.md")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(report.read_text(encoding="utf-8"), "preserve existing report")

    def test_init_and_report_cannot_write_outside_project(self):
        with tempfile.TemporaryDirectory(prefix="lineage-output-outside-") as outside:
            escaped = Path(outside) / "lineage.json"
            result = self.run_cli("init", "--har", "capture.har", "--output", escaped)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(escaped.exists())
            record = self.init_record()
            report = Path(outside) / "report.md"
            result, _ = self.check(record, report=report)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(report.exists())

    def test_malformed_json_and_schema_types_fail_with_diagnostics(self):
        baseline = self.init_record()
        malformed = ["{", '{"version":1,"version":1}']
        for text in malformed:
            with self.subTest(json=text):
                self.lineage.write_text(text, encoding="utf-8")
                result = self.run_cli("check", "--lineage", "lineage.json")
                self.assertNotEqual(result.returncode, 0)
                self.assertTrue(result.stdout or result.stderr)
        for key, value in (("version", 2), ("version", True), ("nodes", None), ("artifacts", {}), ("requests", [None])):
            with self.subTest(field=key):
                record = copy.deepcopy(baseline)
                record[key] = value
                self.assert_rejected(record)
        for key, value in (("source", None), ("dependencies", {}), ("lifecycle", []), ("gaps", "done")):
            with self.subTest(node_field=key):
                record = copy.deepcopy(baseline)
                record["nodes"][0][key] = value
                self.assert_rejected(record)

    def test_nested_evidence_and_comparison_types_are_controlled_errors(self):
        baseline = self.asserted_target_control()
        for invalid in (None, [], 7):
            with self.subTest(evidence_details=invalid):
                record = copy.deepcopy(baseline)
                record["evidence"][0]["details"] = invalid
                self.assert_rejected(record)
            with self.subTest(comparison=invalid):
                record = copy.deepcopy(baseline)
                record["algorithms"][0]["comparisons"][0] = invalid
                self.assert_rejected(record)

    def test_malformed_har_fails_without_traceback(self):
        for malformed in ({"log": {"entries": [None]}}, {"log": {"entries": "wrong"}}):
            with self.subTest(har=malformed):
                self.write_json(self.capture, malformed)
                result = self.run_cli("init", "--har", "capture.har", "--output", "lineage.json")
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(self.lineage.exists())


if __name__ == "__main__":
    unittest.main()
