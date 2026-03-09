import importlib.util
import json
import shlex
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "search.py"


def load_module():
    spec = importlib.util.spec_from_file_location("codex_deep_search", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class SearchScriptTests(unittest.TestCase):
    def test_default_paths_are_under_skill_data_directory(self):
        module = load_module()

        result_dir = module.default_result_dir(MODULE_PATH)
        task_name = "demo-task"
        output_path = module.default_output_path(result_dir, task_name)
        raw_log_path = module.raw_log_path(result_dir, task_name)
        meta_path = module.meta_path(result_dir, task_name)

        expected_dir = ROOT / "data" / "codex-search-results"
        self.assertEqual(result_dir, expected_dir)
        self.assertEqual(output_path, expected_dir / "demo-task.md")
        self.assertEqual(raw_log_path, expected_dir / "demo-task.raw.log")
        self.assertEqual(meta_path, expected_dir / "demo-task.meta.json")

    def test_missing_codex_writes_failed_metadata(self):
        module = load_module()

        with tempfile.TemporaryDirectory() as temp_dir:
            result_dir = Path(temp_dir)
            output_path = result_dir / "query.md"
            exit_code = module.run_search(
                prompt="test prompt",
                task_name="missing-codex",
                model="gpt-5.3-codex",
                timeout_seconds=5,
                result_dir=result_dir,
                output_path=output_path,
                codex_bin="codex-does-not-exist",
                post_run_hook=None,
            )

            self.assertNotEqual(exit_code, 0)
            meta = json.loads((result_dir / "missing-codex.meta.json").read_text())
            self.assertEqual(meta["status"], "failed")
            self.assertEqual(meta["task_name"], "missing-codex")
            self.assertEqual(meta["output"], str(output_path))
            self.assertIn("not found", meta["error"].lower())

    def test_post_run_hook_receives_metadata_context(self):
        module = load_module()

        with tempfile.TemporaryDirectory() as temp_dir:
            result_dir = Path(temp_dir)
            output_path = result_dir / "query.md"
            hook_log = result_dir / "hook.json"
            codex_stub = result_dir / "codex-stub.sh"
            hook_script = result_dir / "hook.py"
            codex_stub.write_text(
                "#!/usr/bin/env bash\n"
                "echo 'stub codex output'\n",
                encoding="utf-8",
            )
            codex_stub.chmod(0o755)
            hook_script.write_text(
                "import json\n"
                "import os\n"
                "from pathlib import Path\n"
                "\n"
                "Path(os.environ['HOOK_LOG']).write_text(json.dumps({\n"
                "    'task_name': os.environ['TASK_NAME'],\n"
                "    'status': os.environ['STATUS'],\n"
                "    'output': os.environ['OUTPUT'],\n"
                "    'meta_file': os.environ['META_FILE'],\n"
                "} ))\n",
                encoding="utf-8",
            )

            hook_command = f"HOOK_LOG={shlex.quote(str(hook_log))} {shlex.quote(sys.executable)} {shlex.quote(str(hook_script))}"

            exit_code = module.run_search(
                prompt="test prompt",
                task_name="hook-task",
                model="gpt-5.3-codex",
                timeout_seconds=5,
                result_dir=result_dir,
                output_path=output_path,
                codex_bin=str(codex_stub),
                post_run_hook=hook_command,
            )

            self.assertEqual(exit_code, 0)
            hook_payload = json.loads(hook_log.read_text())
            self.assertEqual(hook_payload["task_name"], "hook-task")
            self.assertEqual(hook_payload["status"], "done")
            self.assertEqual(hook_payload["output"], str(output_path))
            self.assertTrue(hook_payload["meta_file"].endswith("hook-task.meta.json"))

    def test_dispatch_mode_returns_without_waiting_for_completion(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            result_dir = Path(temp_dir)
            codex_stub = result_dir / "codex-slow.sh"
            codex_stub.write_text(
                "#!/usr/bin/env bash\n"
                "sleep 2\n"
                "echo 'slow codex output'\n",
                encoding="utf-8",
            )
            codex_stub.chmod(0o755)

            command = [
                sys.executable,
                str(MODULE_PATH),
                "--prompt",
                "dispatch prompt",
                "--task-name",
                "dispatch-task",
                "--result-dir",
                str(result_dir),
                "--codex-bin",
                str(codex_stub),
                "--dispatch",
            ]

            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=False,
                timeout=1,
            )

            self.assertEqual(completed.returncode, 0)
            latest_meta = json.loads((result_dir / "latest-meta.json").read_text())
            self.assertEqual(latest_meta["task_name"], "dispatch-task")
            self.assertEqual(latest_meta["status"], "running")
            self.assertIn("dispatch-task.meta.json", completed.stdout)


if __name__ == "__main__":
    unittest.main()
