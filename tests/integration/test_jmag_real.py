import os
import unittest


@unittest.skipUnless(os.environ.get("JMAG_REAL_SMOKE") == "1", "set JMAG_REAL_SMOKE=1 under JMAG Python")
class RealJmagSmokeTests(unittest.TestCase):
    def test_hidden_application_lifecycle(self):
        from jmag.designer import designer
        app = designer.CreateApplication(["-g"])
        self.assertIsNotNone(app)
        try:
            self.assertTrue(callable(app.GetCurrentModel))
            self.assertTrue(callable(app.GetCurrentStudy))
        finally:
            app.Quit()


if __name__ == "__main__": unittest.main()
