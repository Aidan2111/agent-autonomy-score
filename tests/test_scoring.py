import unittest

from autonomy_score.diff_parser import parse_unified_diff
from autonomy_score.scoring import score_change


class ScoringTests(unittest.TestCase):
    def test_presentation_only_change_is_low_risk(self):
        diff = """diff --git a/App/Views/ProfileView.swift b/App/Views/ProfileView.swift
--- a/App/Views/ProfileView.swift
+++ b/App/Views/ProfileView.swift
@@ -1,3 +1,6 @@
 struct ProfileView: View {
+    Text("Profile changes sync across devices.")
+        .font(.caption)
+        .foregroundStyle(.secondary)
 }
"""

        result = score_change(parse_unified_diff(diff))

        self.assertLessEqual(result.score, 3)
        self.assertEqual(result.recommended_mode, "Unsupervised")
        self.assertTrue(any(signal.name == "presentation-only-cap" for signal in result.signals))

    def test_state_change_without_tests_needs_guidance(self):
        diff = """diff --git a/App/State/SessionStore.swift b/App/State/SessionStore.swift
--- a/App/State/SessionStore.swift
+++ b/App/State/SessionStore.swift
@@ -1,4 +1,11 @@
 final class SessionStore {
+    private var token: String?
+
+    func refresh(using authClient: AuthClient) async throws {
+        token = try await authClient.refreshToken()
+    }
 }
"""

        result = score_change(parse_unified_diff(diff))

        self.assertGreaterEqual(result.score, 4)
        self.assertLessEqual(result.score, 7)
        self.assertEqual(result.recommended_mode, "Guided Autonomy")

    def test_core_data_migration_with_nested_loop_is_high_risk(self):
        diff = """diff --git a/App/Persistence/Migrations/AddConversationIndexMigration.swift b/App/Persistence/Migrations/AddConversationIndexMigration.swift
--- /dev/null
+++ b/App/Persistence/Migrations/AddConversationIndexMigration.swift
@@ -0,0 +1,18 @@
+import CoreData
+
+final class AddConversationIndexMigration {
+    func migrate(context: NSManagedObjectContext) throws {
+        let conversations = try context.fetch(NSFetchRequest<Conversation>())
+        for conversation in conversations {
+            for message in conversation.messages {
+                message.createdAt = conversation.updatedAt
+            }
+        }
+        try context.execute(NSBatchDeleteRequest(fetchRequest: oldDraftRequest()))
+        try context.save()
+    }
+}
"""

        result = score_change(parse_unified_diff(diff))

        self.assertGreaterEqual(result.score, 8)
        self.assertEqual(result.recommended_mode, "Pair Programming")
        self.assertTrue(any(signal.name == "big-o:nested-loop" for signal in result.signals))

    def test_tests_in_diff_avoid_no_tests_signal(self):
        diff = """diff --git a/App/Services/SearchCache.swift b/App/Services/SearchCache.swift
--- a/App/Services/SearchCache.swift
+++ b/App/Services/SearchCache.swift
@@ -1,3 +1,7 @@
+final class SearchCache {
+    private var results: [String: CacheEntry] = [:]
+}
diff --git a/App/Tests/SearchCacheTests.swift b/App/Tests/SearchCacheTests.swift
--- /dev/null
+++ b/App/Tests/SearchCacheTests.swift
@@ -0,0 +1,4 @@
+final class SearchCacheTests {
+    func testReturnsCachedResult() {}
+}
"""

        result = score_change(parse_unified_diff(diff))

        self.assertFalse(any(signal.name == "validation:no-tests-in-diff" for signal in result.signals))


if __name__ == "__main__":
    unittest.main()

