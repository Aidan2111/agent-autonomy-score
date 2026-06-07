import unittest

from autonomy_score.diff_parser import parse_unified_diff


class DiffParserTests(unittest.TestCase):
    def test_groups_added_and_removed_lines_by_file(self):
        diff = """diff --git a/a.py b/a.py
--- a/a.py
+++ b/a.py
@@ -1,2 +1,2 @@
-old
+new
diff --git a/b.py b/b.py
--- a/b.py
+++ b/b.py
@@ -1,0 +1,1 @@
+added
"""

        files = parse_unified_diff(diff)

        self.assertEqual([file.path for file in files], ["a.py", "b.py"])
        self.assertEqual(files[0].removed_lines, ("old",))
        self.assertEqual(files[0].added_lines, ("new",))
        self.assertEqual(files[1].added_lines, ("added",))

    def test_treats_plain_text_as_stdin(self):
        files = parse_unified_diff("print('hello')\n")

        self.assertEqual(len(files), 1)
        self.assertEqual(files[0].path, "stdin")
        self.assertEqual(files[0].added_line_count, 1)


if __name__ == "__main__":
    unittest.main()

