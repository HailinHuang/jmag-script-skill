import unittest
from pathlib import Path

from jmag_functions.runtime import (
    JMAGRuntimeManager,
    ProcessRecord,
    RuntimeTarget,
    process_records_from_rows,
    close_all_jmag_designers,
    merge_runtime_targets,
    parse_jproj_path,
)


class FakeApp:
    def __init__(self, path=r"C:\Models\motor.jproj", running=True, save_error=None):
        self.path = path
        self.running = running
        self.save_error = save_error
        self.calls = []
        self.cancel_count = 0
        self.save_count = 0
        self.quit_count = 0

    def GetProjectPath(self):
        self.calls.append("GetProjectPath")
        return self.path

    def HasRunningProcess(self):
        self.calls.append("HasRunningProcess")
        return self.running

    def GetProcessId(self):
        return 99

    def GetWindowHandle(self):
        return 99

    def CancelProcess(self):
        self.cancel_count += 1
        self.running = False

    def Save(self):
        self.save_count += 1
        if self.save_error:
            raise self.save_error

    def Quit(self):
        self.quit_count += 1


class FakeProvider:
    def __init__(self, records):
        self._records = records

    def records(self):
        return list(self._records)


class FakeJob:
    def __init__(self, status="running", progress=25.0):
        self.status = status
        self.progress = progress
        self.cancelled = False

    def Status(self):
        return self.status

    def PercentComplete(self):
        return self.progress

    def Cancel(self):
        self.cancelled = True


class FakeScheduler:
    def __init__(self, jobs):
        self.jobs = jobs

    def GetJobByFolder(self, folder):
        return self.jobs.get(folder)


class FakeWindowController:
    def __init__(self):
        self.calls = []

    def bring_to_front(self, handle):
        self.calls.append(("foreground", handle))

    def minimize(self, handle):
        self.calls.append(("minimize", handle))


class FakeProcessController:
    def __init__(self):
        self.calls = []

    def terminate(self, pid):
        self.calls.append(pid)


class RuntimeTests(unittest.TestCase):
    def test_parse_jproj_path_extracts_quoted_path(self):
        path = parse_jproj_path(r'"C:\Models\motor test.jproj" -g')
        self.assertEqual(path, Path(r"C:\Models\motor test.jproj").resolve())

    def test_merge_runtime_targets_keeps_attached_target_and_process_metadata(self):
        attached = [
            RuntimeTarget(
                "designer:123", "designer", pid=123, project_path=Path("m.jproj"),
                status="running", attached=True,
            )
        ]
        processes = [
            ProcessRecord(
                "designer.exe", 123, r'"C:\Models\m.jproj"', 1,
                r"C:\designer.exe",
            )
        ]
        merged = merge_runtime_targets(attached, [], processes)
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0].pid, 123)
        self.assertEqual(
            merged[0].project_path,
            Path(r"C:\Models\m.jproj").resolve(),
        )

    def test_refresh_reports_attached_designer_running_state_and_path(self):
        app = FakeApp(running=True)
        snapshot = JMAGRuntimeManager(
            app=app, process_provider=FakeProvider([])
        ).refresh()
        target = snapshot.by_kind("designer")[0]
        self.assertEqual(
            target.project_path,
            Path(r"C:\Models\motor.jproj").resolve(),
        )
        self.assertEqual(target.status, "running")
        self.assertTrue(target.attached)

    def test_refresh_is_read_only(self):
        app = FakeApp(running=True)
        JMAGRuntimeManager(
            app=app, process_provider=FakeProvider([])
        ).refresh()
        self.assertEqual(app.calls, ["GetProjectPath", "HasRunningProcess"])

    def test_refresh_lists_unattached_jproj_process_and_scheduler_progress(self):
        folder = r"C:\Runs\job.jfiles"
        manager = JMAGRuntimeManager(
            scheduler=FakeScheduler({folder: FakeJob(progress=62.5)}),
            scheduler_folders=[folder],
            process_provider=FakeProvider([
                ProcessRecord(
                    "designer.exe", 321,
                    r'"C:\Models\other motor.jproj" -g',
                    1,
                    r"C:\designer.exe",
                )
            ]),
        )
        snapshot = manager.refresh()
        process = snapshot.get("process:321")
        scheduler = snapshot.get(f"scheduler:{folder}")
        self.assertIsNotNone(process)
        self.assertEqual(process.project_path, Path(r"C:\Models\other motor.jproj").resolve())
        self.assertEqual(scheduler.progress, 62.5)

    def test_process_rows_preserve_main_window_handle_and_title(self):
        records = process_records_from_rows([
            {
                "Name": "designer.exe",
                "ProcessId": 321,
                "CommandLine": r'"C:\Models\motor.jproj"',
                "ParentProcessId": 1,
                "ExecutablePath": r"C:\designer.exe",
                "MainWindowHandle": 777,
                "MainWindowTitle": "JMAG Designer",
            }
        ])
        self.assertEqual(records[0].window_handle, 777)
        self.assertEqual(records[0].window_title, "JMAG Designer")

    def test_save_and_close_saves_then_cancels_running_designer(self):
        app = FakeApp(running=True)
        result = JMAGRuntimeManager(
            app=app, process_provider=FakeProvider([])
        ).save_and_close_all_designers()[0]
        self.assertTrue(result.ok)
        self.assertEqual(app.save_count, 1)
        self.assertEqual(app.cancel_count, 1)
        self.assertEqual(app.quit_count, 1)

    def test_close_all_designers_without_save_does_not_call_save(self):
        app = FakeApp(running=False)
        result = JMAGRuntimeManager(
            app=app, process_provider=FakeProvider([])
        ).close_all_designers()[0]
        self.assertTrue(result.ok)
        self.assertEqual(app.save_count, 0)
        self.assertEqual(app.quit_count, 1)

    def test_top_level_close_all_function_uses_the_manager(self):
        app = FakeApp(running=False)
        result = close_all_jmag_designers(app=app, process_provider=FakeProvider([]))[0]
        self.assertTrue(result.ok)
        self.assertEqual(app.quit_count, 1)

    def test_stop_selected_cancels_scheduler_job_and_designer_process(self):
        app = FakeApp(running=True)
        folder = r"C:\Runs\job.jfiles"
        job = FakeJob()
        scheduler = FakeScheduler({folder: job})
        manager = JMAGRuntimeManager(
            app=app,
            scheduler=scheduler,
            scheduler_folders=[folder],
            process_provider=FakeProvider([]),
        )
        results = manager.stop_selected_jobs(
            [f"scheduler:{folder}", "designer:99"]
        )
        self.assertTrue(all(result.ok for result in results))
        self.assertTrue(job.cancelled)
        self.assertEqual(app.cancel_count, 1)

    def test_save_and_close_does_not_quit_when_save_fails(self):
        app = FakeApp(running=False, save_error=OSError("locked"))
        result = JMAGRuntimeManager(
            app=app, process_provider=FakeProvider([])
        ).save_and_close_all_designers()[0]
        self.assertFalse(result.ok)
        self.assertEqual(app.quit_count, 0)

    def test_window_operations_delegate_to_injected_controller(self):
        controller = FakeWindowController()
        manager = JMAGRuntimeManager(
            app=FakeApp(),
            window_controller=controller,
            process_provider=FakeProvider([]),
        )
        manager.bring_to_front("designer:99")
        manager.minimize_to_background("designer:99")
        self.assertEqual(
            controller.calls,
            [("foreground", 99), ("minimize", 99)],
        )

    def test_process_termination_requires_explicit_force(self):
        controller = FakeProcessController()
        manager = JMAGRuntimeManager(
            process_provider=FakeProvider(
                [ProcessRecord("designer.exe", 321, "", 1, "designer.exe")]
            ),
            process_controller=controller,
        )
        result = manager.terminate_selected_processes(["process:321"])[0]
        self.assertFalse(result.ok)
        self.assertEqual(controller.calls, [])


if __name__ == "__main__":
    unittest.main()
